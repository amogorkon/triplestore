
from uuid import uuid4, UUID
from collections import namedtuple, defaultdict

from inspect import isclass
from itertools import product, chain
from dataclasses import dataclass
from warnings import warn
from collections.abc import Set

from typing import List

# unused?
from enum import Enum

# remove after dev
from pprint import pprint

class StoreException(UserWarning):
    """All Exceptions specific to this package for easy filtering."""
    
class FailedToComply(StoreException):
    pass

class NotFound(StoreException):
    pass

Triple = namedtuple("Triple", "s p o")
    
class Predicate:
    """See django validators."""
    url = None
    
    def validate(self, value):
        return True
    
    @property
    def name(self):
        return self.__class__.__name__
    
    def __str__(self):
        return self.name
    
    def __repr__(self):
        return self.name

class E:
    """Entity.
    Most entities will be anonymous, which is perfectly fine, while some can have names.
    Entities are the same whenever they have the same id, which is unique.
    These are NOT singletons (which could be conceivable), but due to the UUID used as
    hash, they behave very similar, for instance as keys in dicts.
    """
    def __init__(self, name:str=None, id_:str=None, url:str=None):        
        self.url = url
        
        if name is None:
            self.name = None
        elif not str.isidentifier(name):
            raise StoreException("%s not an identifier."%name)
        else:
            self.name = name

        self.id = UUID(id_) if id_ is not None else uuid4()
    
    def __hash__(self):
        return self.id.int
    
    def __str__(self):
        return self.name if self.name is not None else "_" + str(self.id)[:5]
    
    def __repr__(self):
        """Return representation so that e == eval(repr(e))"""
        return (f"""E(\
{f"name='{self.name}', " if self.name is not None else ''}\
id_='{self.id}'\
{f", url='{self.url}'" if self.url is not None else ''})"""
               )
    
    def __eq__(self, other):
        return hash(self) == hash(other)


class TripleStore:
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
    """
    
    def __init__(self):
        self._spo = {}  # {subject: {predicate: set([object])}}
        self._pos = {}  # {predicate: {object: set([subject])}}
        self._osp = {}  # {object: {subject, set([predicate])}}
        
    def __getitem__(self, key):
        """
        Return iterator over triplets directly as result.
        
        This is a mechanism inspired by the brilliant way numpy handles
        arrays and its vectorization methods. 
        Another way of querying is the .get() method inspired by django which
        returns a Query object, representing a view on the dictionary to be evaluated lazily.
        
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
            assert isinstance(key, E) or isinstance(key, Triple)
            # we return a dict of p:o that we can use in set_all, producing a nice symmetry
            # this is in contrast to the slice method, which returns sets of objects
            return self._spo[key]
        else:
            s, p, o = key.start, key.stop, key.step
            
        # Observe that cases with only one False return no Triples but the values themselves
        # this way, the results can be used directly in an assignment.
        case = {(True, True, True): lambda: {Triple(s, p, o) 
                                             for x in (1,) 
                                             if o in self._spo[s][p]},
              (True, True, False): lambda: {OBJ for OBJ in self._spo[s][p]},
              (True, False, True): lambda: {PRED 
                                            for PRED in self._osp[o][s] if PRED in self._osp[o][s]},
              (True, False, False): lambda: {Triple(s, PRED, OBJ) 
                                             for PRED, objset in self._spo[s].items()
                                             for OBJ in objset},
              (False, True, True): lambda: {SUB for SUB in self._pos[p][o]},
              (False, True, False): lambda: {Triple(SUB, p, OBJ) 
                                             for OBJ, subset in self._pos[p].items() 
                                             for SUB in subset},
              (False, False, True): lambda: {Triple(SUB, PRED, o) 
                                             for SUB, predset in self._osp[o].items()
                                             for PRED in predset},
              (False, False, False): lambda: {Triple(SUB, PRED, OBJ) 
                                             for SUB, predset in self._spo.items()
                                             for PRED, objset in predset.items()
                                             for OBJ in objset}
             }
        try:
            return case[(s is not None,  p is not None, o is not None)]()
        except KeyError:
            warn((s, p, o), NotFound)
        
    
    def __len__(self):
        return len(self._spo)
    
    def __iter__(self):
        """Return the same iterator as Store[::] for convenience."""
        return ((SUB, PRED, OBJ) for SUB, predset in self._spo.items()
                                for PRED, objset in predset.items()
                                for OBJ in objset)
    
    def __contains__(self, value):
        s, p, o = value
        try:
            return o in self._spo[s][p]
        except KeyError:
            return False
    
    def add(self, *, s, p, o):
        def add2index(index, a, b, c):
            if a not in index:
                index[a] = {b: set([c])}
            else:
                if b not in index[a]:
                    index[a][b] = set([c])
                else:
                    index[a][b].add(c)
                    
        if s is None or (s, p, o) in self:
            warn(f"{s, p, o}", FailedToComply)
        
        # Subject can be an existing Triple, which allows for softlink-recursion.
        if isinstance(s, Triple):
            if s not in self:
                raise FailedToComply("Specified subject (Triple) was not found in the store.")
        else:
            if not isinstance(s, E):
                raise FailedToComply("Subject is neither a Triple nor an instance of E.", s, type(s))
        
        assert hasattr(p, "name"), "Predicate has no name!"
        assert hasattr(p, "validate"), "Predicate has no method for validation!"
        assert hasattr(p, "url"), "Predicate has no url!"
        
        if not p.validate(o):
            raise StoreException(f"{o} does not match the criteria for predicate {p}")
        
        add2index(self._spo, s, p, o)
        add2index(self._pos, p, o, s)
        add2index(self._osp, o, s, p)
        return Triple(s, p, o)
        
    def __setitem__(self, key, value):
        assert isinstance(key, slice), "Must be assigned using a slice (ex: Store[:foo:] = 23)."
        assert isinstance(key.stop, Predicate), "Predicate MUST be specified in slice."
        
        p = key.stop
        o = value
        
        if not (isinstance(key.start, E) or isinstance(key.start, Triple)):
            results = []
            S = key.start
            for s in S:
                results.append(self.add(s=s, p=p, o=o))
            return results
        else:
            s = key.start
            return self.add(s=s, p=p, o=o)

    
    def create_subjects_with(self, predobjects):
        """Add all combinations of predicate:object to the store and create new entities for each combo.
        
        From a dict of key:[list of values] we produce a list of all combinations
        of [(key1,value1), (key1,value2)] from which we can build a new dict
        to pass into self.add as parameters.
        
        """
        combinations = product(*[[(k, v) for v in predobjects[k]] for k in predobjects.keys()])
        subjects = []
        # Trick is to create new entities with a sentinel of None so there is an indefinite amount
        for C, s in zip(combinations, iter(E, None)):
            for p, o in C:
                r = self.add(s=s, p=p, o=o)
            subjects.append(s)
        return subjects

    def set_all(self, *, subjects:List[E], predobjects:dict):
        results = []
        for s in subjects:
            for p, O in predobjects.items():
                for o in O:
                    r = self.add(s=s, p=p, o=o)
                    results.append(r)
        return results
    
    def get(self, clause_dict):
        """Get the item from the store that matches ALL clauses."""
        clauses = list(clause_dict.items())
        # we need to init the results somehow
        k, v = clauses.pop()
        result = {s for s in self[:k:v]}
        for k, v in clauses:
            result.intersection_update({s for s in self[:k:v]})
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
        result = self[:k:v].copy()
        for k, v in clauses:
            result.intersection_update(self[:k:v])
        return result  # Should be QuerySet

    
    def get_last_added(self):
        """Get the item that was last added to the store."""
        return list(self._spo.keys())[-1]
    
    def undo(self):
        raise NotImplementedError
    
    def __delitem__(self, item):
        raise NotImplementedError
        
    def __str__(self):
        return "".join(f"{str(s)} {str(p)} {str(o)}\n" for s, p, o in self)
        
    

@dataclass
class Query:
    """Class representing a query to the store."""
    store: TripleStore
    spo: Triple
        
    def __call__(self):
        return self.store[self.triple.s: self.triple.p: self.triple.o]


class QuerySet:
    def __init__(self, values):
        self.values = values

    def __getattr__(self, name):
        """Get the value of an attribute."""
        if name in self._sets:
            return self._sets[name]
        else:
            raise AttributeError(f"{name} is not a method or attribute of set or ")