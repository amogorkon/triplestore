
from uuid import uuid5, NAMESPACE_URL

class E(str):
    """Entity"""
    def __new__(cls, value):
        return super().__new__(cls, value)
    def __hash__(self):
        return uuid5(NAMESPACE_URL, self).int

class P(str):
    """Property"""
    def __new__(cls, value):
        return super().__new__(cls, value)    
    def __hash__(self):
        return uuid5(NAMESPACE_URL, self).int  

class TripleStore:
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
            s = key.start
            if not isinstance(s, E):
                raise RuntimeWarning("subject must be an E()")
            p = key.stop
            if not isinstance(p, P):
                raise RuntimeWarning("predicate must be a P()")
            o = value
            add2index(self._spo, s, p, o)
            add2index(self._pos, p, o, s)
            add2index(self._osp, o, s, p)
                      
    def __getitem__(self, key):
        if not isinstance(key, slice):
            s = key
            p,o = None, None
        else: 
            s, p, o = key.start, key.stop, key.step
            
        d2 = {(True, True, True): lambda: ((s, p, o) for x in (1,) 
                                           if o in self._spo[s][p]),
              (True, True, False): lambda: ((s, p, OBJ) for OBJ in self._spo[s][p]),
              (True, False, True): lambda: ((s, PRED, o) for PRED in self._osp[o][s]),
              (True, False, False): lambda: ((s, PRED, OBJ) 
                                             for PRED, objset in self._spo[s].items()
                                             for OBJ in objset),
              (False, True, True): lambda: ((SUB, p, o) for SUB in self._pos[p][o]),
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
        # .get with default won't work here because any of the dicts may throw KeyError
        try:
            return d2[(s is not None,  p is not None, o is not None)]()
        except KeyError:
            return ()
        
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