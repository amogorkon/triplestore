from weakref import WeakValueDictionary, WeakSet
from uuid import uuid4, UUID
from collections import namedtuple, Iterable
from itertools import product


class StoreException(UserWarning):
    """All Exceptions specific to this package for easy filtering."""

T = namedtuple("Triple", "s p o")

class E:
    """Entity.
    Most entities will be anonymous, which is perfectly fine, while some can have names.
    Entities are the same whenever they have the same id, which is unique.
    
    >>> x = E("hello")
    >>> y = eval(repr(x))
    >>> x == y
    True
    >>> x is y
    False
    """
    def __init__(self, name=None, uri=None, ID=None):        
        
        if name is None:
            self.name = None
        elif not str.isidentifier(name):
            raise StoreException("%s not an identifier."%name)
        else:
            #_named_entities[name] = 
            self.name = name
        
        self.uri = uri
        self.ID = UUID(ID) if ID is not None else uuid4()
    
    def __hash__(self):
        return self.ID.int
    
    def __str__(self):
        return self.name if self.name is not None else "#" + str(self.ID)[:6]
    
    def __repr__(self):
        """Return representation so that e == eval(repr(e))"""
        return ("E(" 
                f"""{f"name='{self.name}'," if self.name is not None else ''}"""
                f"ID='{self.ID}')"
               )

    def __mul__(self, value):
        if not isinstance(value, int):
            raise ValueError
        else:
            for _ in range(value):
                yield E(name=self.name, uri=self.uri)
    
    def __eq__(self, other):
        return self.ID == other.ID


class Predicate:
    def __init__(self, name, *, uri=None, validators=None):
        if not str.isidentifier(name):
            raise StoreException("%s not an identifier."%name)
        predicates[name] = self
        self.name = name
        self.uri = uri
        self.validators = [] if validators is None else validators

    def __hash__(self):
        return hash(self.name) 

    def __str__(self):
        return self.name

    def __repr__(self):
        return (f"Predicate('{self.name}', {f'uri={self.uri},' if self.uri is not None else ''}"
                f"{f'validators={self.validators}' if self.validators != [] else ''})")

    def __eq__(self, other):
         return self.name == other.name

    def __call__(self, arg):
        return all(v(arg) for v in self.validators)

class Store:
    """A set of three dicts that work together as one."""
    
    def __init__(self):
        self._spo = {}  # {subject: {predicate: set([object])}}
        self._pos = {}  # {predicate: {object: set([subject])}}
        self._osp = {}  # {object: {subject, set([predicate])}}
    
    def __setitem__(self, key, value):
        def add2index(index, a, b, c):
            if a not in index:
                index[a] = {b: set([c])}
            else:
                if b not in index[a]:
                    index[a][b] = set([c])
                else:
                    index[a][b].add(c)
        
        if not isinstance(key, slice):
            raise StoreException("Syntax is: store[s:p:context] = o")
        else:
            s = key.start if isinstance(key.start, E) else E(key.start)
            p = key.stop
            context = key.step
            o = value
            # to allow the idiom store[s:p] = o*2
            if isinstance(o, Iterable):
                for x in o:
                    self.__setitem__(key, x)
            elif not p(o):
                raise StoreException(f"Object {o} does not validate for {p}.")
            else:
                add2index(self._spo, s, p, o)
                add2index(self._pos, p, o, s)
                add2index(self._osp, o, s, p)
        
    def __getitem__(self, key):
        """
        Return iterator over triplets directly as result.
        
        This is a mechanism inspired by the brilliant way numpy handles
        arrays and its vectorization methods.
        This is different from the SQL inspired brilliant way of how 
        django handles queries, which is reflected by the .get() method,
        which returns a Query object that lazily evaluates and caches.
        
        The case dictionary here is an invention of mine after 
        researching alternatives for page-long if-clauses that 
        are detrimental to readability.
        It works like this: 
        1) extract s, p and o from the given store[s:p:o] call
        2) go to the bottom of the function and check which parts are given
        3) pass the resulting tuple into the case dict as key and execute the stored func
        4) since the anonymous funcs are closures with access to the local variables,
           they easily can build generators with those and return them.
        
        """
        # we query for an entity directly
        if not isinstance(key, slice):
            assert isinstance(key, E)
            properties = self._spo[key]
            try:
                return namedtuple(f"{str(key)}", 
                              [p.name for p in properties.keys()])(
                                **{k.name:v for k, v in properties.items()})
            except ValueError:
                return namedtuple(f"{str(key)}", 
                        [f"{p.__class__.__name__}__{p.name}"
                         for p in properties.keys()])(
                    **{f"{k.__class__.__name__}__{k.name}":v 
                         for k, v in properties.items()})
        else:
            s, p, o = key.start, key.stop, key.step
            
        case = {(True, True, True): lambda: {(s, p, o) 
                                             for x in (1,) 
                                             if o in self._spo[s][p]},
              (True, True, False): lambda: {(s, p, OBJ)
                                            for OBJ in self._spo[s][p]},
              (True, False, True): lambda: {(s, PRED, o) 
                                            for PRED in self._osp[o][s]},
              (True, False, False): lambda: {(s, PRED, OBJ) 
                                             for PRED, objset in self._spo[s].items()
                                             for OBJ in objset},
              (False, True, True): lambda: {(SUB, p, o) 
                                            for SUB in self._pos[p][o]},
              (False, True, False): lambda: {(SUB, p, OBJ) 
                                             for OBJ, subset in self._pos[p].items() 
                                             for SUB in subset},
              (False, False, True): lambda: {(SUB, PRED, o) 
                                             for SUB, predset in self._osp[o].items()
                                             for PRED in predset},
              (False, False, False): lambda: {(SUB, PRED, OBJ) 
                                             for SUB, predset in self._spo.items()
                                             for PRED, objset in predset.items()
                                             for OBJ in objset}
             }
        # .get with default won't work here because any of the 
        # dicts may throw KeyError
        try:
            return case[(s is not None,  p is not None, o is not None)]()
        except KeyError:
            return ()
    
    def __len__(self):
        return len(self._spo)
    
    def __iter__(self):
        """Return the same iterator as store[::] for convenience."""
        return (T(SUB, PRED, OBJ) for SUB, predset in self._spo.items()
                                for PRED, objset in predset.items()
                                for OBJ in objset)
    
    def add(self, d, s=None):
        """Convenience method to add a new item to the store."""
        s = s if s is not None else E()
        for p, o in d.items():
            if not p(o):
                return False
        for p, o in d.items():
            self[s:p] = o
        return s
    
    def add_all(self, d, list_of_s=None):
        """Add all combinations of predicate:object to the store.
        
        From a dict of key:[list of values] we produce a list of all combinations
        of [(key1,value1), (key1,value2)] from which we can build a new dict
        to pass into self.add as parameters.
        
        The subjects (param S) is a list of entities that all these combinations 
        will be added to.
        
        >>> body = TripleStore()
        >>> P = BasePredicate("P", "name has side")
        >>> torso = E("torso")
        >>> body.add({P.name:"torso"}, s=torso) == torso
        True
        >>> legs = body.add_all({P.name:["leg"], P.side:["left", "right"]})
        >>> body.add_all({P.has:legs}, list_of_s=[torso]) == [torso]
        True
        >>> body[torso].has == set(legs)
        True
        >>> body.add_all({P.has:["muscle"]}, list_of_s=legs) == legs
        True
        >>> x = body.get({P.name:"leg", P.side:"left"})
        >>> "muscle" in body[x].has
        True
        """

        # simple case: no subjects were given, so we create one for each combination
        if list_of_s is None:
            results = []
            combos = product(*[[(k, v) for v in d[k]] for k in d.keys()])
            for c in combos:
                params = {k:v for k, v in c}
                # I'd rather yield, but that'd mean it won't return!
                results.append(self.add(params))
            return results
        else:
            # we have a list of entities, which we use as target for each combination
            for s in list_of_s:
                for p, O in d.items():
                    for o in O:
                        self[s:p] = o
            return list_of_s

    def get(self, clause_dict):
        """Get the item from the store that matches all clauses."""
        clauses = list(clause_dict.items())
        # we need to init the results somehow
        k, v = clauses.pop()
        result = {s for s, p, o in self[:k:v]}
        for k, v in clauses:
            result.intersection_update({s for s, p, o in self[:k:v]})
        if len(result) > 1:
            raise AttributeError("More than a single item matches the criteria.")
        elif len(result) == 0:
            return None
        else:
            return result.pop()
    
    def get_all(self, clause_dict):
        """Get all items from the store that match ALL clauses.
        
        The returned set of items can be reused in any way, including combining
        or excluding items from different queries or manually adding items.
        It is necessary to use a dict here in order to make use of Enum.
        """
        clauses = list(clause_dict.items())
        # we need to init the results somehow
        k, v = clauses.pop()
        result = {s for s, p, o in self[:k:v]}
        for k, v in clauses:
            result.intersection_update({s for s, p, o in self[:k:v]})
        return result

    
    def get_last_added(self):
        """Get the item that was last added to the store."""
        return list(self._spo.keys())[-1]



# SELECT returns data matching some conditions, results are represented in a simple table, where each matching result is a row and each colum is the value for a specific variable
# ASK check if there is at least one result for a given query pattern, the result is true or false. 
# DESCRIBE returns an RDF graph that describes a resource. the implementation of this return form is up for each query engine
# CONSTRUCT returns an RDF graph that is created from a template specified as part of the query itself. a new RDF graph is created by taking the results of a query pattern and filling in the values of variables that occur in the construct template. is used to transform RDF data (for example into a different graph structure and with a different vocabulary than the source data)
# DBpedia - wiki.dbpedia.org 