
from uuid import uuid4, UUID

class StoreException(UserWarning):
    """All Exceptions specific to this package for easy filtering."""

class E:
    """Entity.
    Most entities will be anonymous, which is perfectly fine, while some can have names.
    Entities are the same whenever they have the same id, which is unique.
    These are NOT singletons (which could be conceivable), but due to the UUID used as
    hash, they behave very similar, for instance as keys in dicts.
    
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
            self.name = name
        
        self.id = UUID(id_) if id_ is not None else uuid4()
    
    def __hash__(self):
        return self.id.int
    
    def __str__(self):
        return self.name if self.name is not None else str(self.id)[:5]
    
    def __repr__(self):
        return f"E(name='{self.name}', id_='{self.id}')"
    
    def __eq__(self, other):
        return self.id == other.id

class P(str):
    """
    Predicate class.
    
    This must be a valid identifier so that it can be called via store.get(predicate="foo")
    
    >>> h = P("has")
    >>> h == eval(repr(h))
    True
    """
    def __new__(cls, value):
        if not str.isidentifier(value):
            raise StoreException("%s not an identifier."%value)
        else:
            return super().__new__(cls, value)


class TripleStore:
    """A set of three dicts that work together as one.
    
    Keep in mind that the primary dict - spo - is a Python3 dict,
    which works as an OrderedDict that remembers insertion order.
    It might be a good idea to have the other two dicts as weakrefs,
    but that still needs to be figured out.
    
    Subjects need to be unique Entities because
    head = {"eye": {"side": {"left}}, "eye": {"side": "right"}}
    naturally would only count 1 eye instead of two different ones.
    So, this must work:
    
    >>> body = TripleStore()
    >>> body.add(name="eye", side="left")
    >>> body.add(name="eye", side="right")
    
    #>>> len(body.get(name="eye"))
    #2
    
    >>> fingers = "thumb index middle ring pinky".split()
    >>> sides = ["left", "right"]
    >>> body.add_all(name=fingers, side=sides, is_a=["finger"])
    
    #>>> len(body.get(is_a="finger))
    #10
    
    There are ways for manipulating entries:
    
    >>> x = body.get(name="eye", side="left")
    
    # >>> body[x] == {x: {"name":{"eye"}, "side":{"left"}}}
    >>> body[x:"color"] = "blue"
    
    #>>> body[x:"color"]
    #"blue"
    """
    
    _spo = {}  # {subject: {predicate: set([object])}}
    _pos = {}  # {predicate: {object: set([subject])}}
    _osp = {}  # {subject: {subject, set([predicate])}}
    
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
            raise RuntimeWarning("must be store[s:p] = o")
        elif key.step is not None:
            raise RuntimeWarning("slice must be two-part, not three")
        else:
            s = key.start if isinstance(key.start, E) else E(key.start)
            p = key.stop
            o = value
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
        if not isinstance(key, slice):
            s = key
            p,o = None, None
        else: 
            s, p, o = key.start, key.stop, key.step
            
        case = {(True, True, True): lambda: ((s, p, o) 
                                             for x in (1,) 
                                             if o in self._spo[s][p]),
              (True, True, False): lambda: ((s, p, OBJ) 
                                            for OBJ in self._spo[s][p]),
              (True, False, True): lambda: ((s, PRED, o) 
                                            for PRED in self._osp[o][s]),
              (True, False, False): lambda: ((s, PRED, OBJ) 
                                             for PRED, objset in self._spo[s].items()
                                             for OBJ in objset),
              (False, True, True): lambda: ((SUB, p, o) 
                                            for SUB in self._pos[p][o]),
              (False, True, False): lambda: ((SUB, p, OBJ) 
                                             for OBJ, subset in self._pos[p].items() 
                                             for SUB in subset),
              (False, False, True): lambda: ((SUB, PRED, o) 
                                             for SUB, predset in self._osp[o].items()
                                             for PRED in predset),
              (False, False, False): lambda: ((SUB, PRED, OBJ) 
                                             for SUB, predset in self._spo.items()
                                             for PRED, objset in predset.items()
                                             for OBJ in objset)
             }
        # .get with default won't work here because any of the 
        # dicts may throw KeyError
        try:
            return case[(s is not None,  p is not None, o is not None)]()
        except KeyError:
            return ()
    
    def add(self, **properties):
        s = E()
        for p, o in properties.items():
            self[s:p] = o
    
    def add_all(self, **lists_of_properties):
        pass
    
    def get(self, **clauses):
        pass
    
    def get_last(self):
        return list(self._spo.keys())[-1]
    
    def query(self,clauses):        
        bindings = None
        for clause in clauses:
            bpos = {}
            qc = []
            for pos, x in enumerate(clause):
                if x.startswith('?'):
                    qc.append(None)
                    bpos[x] = pos
                else:
                    qc.append(x)
            rows = list(self.triples((qc[0], qc[1], qc[2])))
            if bindings == None:
                # This is the first pass, everything matches
                bindings = []
                for row in rows:   
                    binding = {}
                    for var, pos in bpos.items():
                        binding[var] = row[pos]
                    bindings.append(binding)
            else:
                # In subsequent passes, eliminate bindings that don't work
                newb = []
                for binding in bindings:
                    for row in rows:
                        validmatch = True
                        tempbinding = binding.copy()
                        for var, pos in bpos.items():
                            if var in tempbinding:
                                if tempbinding[var] != row[pos]:
                                    validmatch = False
                            else:
                                tempbinding[var] = row[pos]
                        if validmatch: newb.append(tempbinding)
                bindings = newb    
        return bindings
    

class Query:
    """Class representing a query to the store."""