
from uuid import uuid4, UUID
from collections import namedtuple, defaultdict
from weakref import WeakValueDictionary
from itertools import product

class StoreException(UserWarning):
    """All Exceptions specific to this package for easy filtering."""

_named_entities = WeakValueDictionary()

class P:
    """Predicate.
    
    Predicates are supposed to be URIs, which means there can be different URLs that mean the same thing.
    So, we do the same as for entities: we map URIs to UUIDs.
    """
    def __init__(self, uri, id_=None):        
        if not str.isidentifier(uri):
            raise StoreException("%s not an identifier."%uri)
        else:
            _predicates[uri] = self
            self.uri = uri
        
        self.id = UUID(id_) if id_ is not None else uuid4()
    
    def __hash__(self):
        return self.id.int
    
    def __str__(self):
        return self.name if self.name is not None else "_" + str(self.id)[:5]
    
    def __repr__(self):
        """Return representation so that e == eval(repr(e))"""
        return ("E(" 
                f"""{f"name='{self.name}'," if self.name is not None else ''}"""
                f"id_='{self.id}')"
               )
    
    def __eq__(self, other):
        return self.id == other.id
    

class E:
    """Entity.
    Most entities will be anonymous, which is perfectly fine, while some can have names.
    Entities are the same whenever they have the same id, which is unique.
    
    >>> x = E("hello")
    >>> y = eval(repr(x))
    >>> x == y
    True
    """
    def __init__(self, name=None, id_=None):        
        
        self.name = None
        
        if name is None:
            self.name = None
        elif not str.isidentifier(name):
            raise StoreException("%s not an identifier."%name)
        else:
            _named_entities[name] = self
            self.name = name
        
        self.id = UUID(id_) if id_ is not None else uuid4()
    
    def __hash__(self):
        return self.id.int
    
    def __str__(self):
        return self.name if self.name is not None else "_" + str(self.id)[:5]
    
    def __repr__(self):
        """Return representation so that e == eval(repr(e))"""
        return ("E(" 
                f"""{f"name='{self.name}'," if self.name is not None else ''}"""
                f"id_='{self.id}')"
               )
    
    def __eq__(self, other):
        return self.id == other.id


class Store:
    """A set of three dicts that work together as one.
    
    Keep in mind that the primary dict - spo - is a Python3 dict,
    which works as an OrderedDict that remembers insertion order.
    It might be a good idea to have the other two dicts as weakrefs,
    but that still needs to be figured out.
    
    Subjects need to be unique Entities because
    head = {"eye": {"side": {"left}}, "eye": {"side": "right"}}
    naturally would only count 1 eye instead of two different ones.
    Please note that store.add returns the entity (or list of entities for
    store.add_all) that was the target of the operation to simplify workflow and tests. 
    Since these return values matter in doctests, we assign them to dummy variables.
    
    >>> body = TripleStore()

    """
    
    def __init__(self):
        self._spo = {}  # {subject: {predicate: set([object])}}
        self._pos = {}  # {predicate: {object: set([subject])}}
        self._osp = {}  # {object: {subject, set([predicate])}}
        # sic!
        self._checks = defaultdict(lambda: lambda o: True)
    
    def set_check(self, p, func):
        self._checks[p] = func
    
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
            raise StoreException("must be store[s:p] = o")
        elif key.step is not None:
            raise StoreException("slice must be two-part, not three")
        else:
            s = key.start if isinstance(key.start, E) else E(key.start)
            p = key.stop
            o = value
            if not self._checks[p](o):
                raise StoreException("%s does not match the set criteria for this predicate"%o)
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
            # This is a bit tricky because P.thing is not a valid identifier.
            # This becomes a problem if different sets of predicates are defined
            # as namespaces with conflicting names.
            # In this case, we resolve the conflict the django-way by mangling
            # predicates to P__thing.
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
        """Return the same iterator as body[::] for convenience."""
        return ((SUB, PRED, OBJ) for SUB, predset in self._spo.items()
                                for PRED, objset in predset.items()
                                for OBJ in objset)
    
    def add(self, d, s=None):
        """Convenience method to add a new item to the store."""
        s = s if s is not None else E()
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
        """Get the item from the store that matches ALL clauses."""
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

class Query:
    """Class representing a query to the store."""