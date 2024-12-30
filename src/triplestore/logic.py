from collections.abc import Any
from dataclasses import dataclass
from itertools import product
from warnings import warn

# to be replaced with a real key-value store. This is a placeholder.
# import the module, then replace the class as the store.
store = {int: Any}
relations = {int: Any}


def set_globals(store_, relations_):
    global store, relations
    store = store_
    relations = relations_


class StoreException(UserWarning):
    """All Exceptions specific to this package for easy filtering."""


class FailedToComply(StoreException):
    pass


class NotFound(StoreException):
    pass


class Triple(tuple):
    """A triple of (subject, predicate, object)."""

    @property
    def s(self):
        return E(self[0])

    @property
    def p(self):
        return E(self[1])

    @property
    def o(self):
        return E(self[2])


class E:
    __slots__ = ("id",)

    def __init__(self, _id):
        self.id = _id

    @property
    def name(self):
        return store[self.id]

    @property
    def relations(self):
        return relations[self.id]


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
        self._spo: dict[int, dict[int, set[int]]] = {}
        "{subject: {predicate: set([object])}}"
        self._pos: dict[int, dict[int, set[int]]] = {}
        "{predicate: {object: set([subject])}}"
        self._osp: dict[int, dict[int, set[int]]] = {}
        "{object: {subject: set([predicate])}}"

    def __getitem__(self, key):
        """
        Return iterator over triplets directly as result.

        This is a mechanism inspired by the brilliant way numpy handles
        arrays and its vectorization methods.
        Another way of querying is the .get() method inspired by django which
        returns a Query object, representing a view on the dictionary to be evaluated lazily.
        """
        if not isinstance(key, slice):
            return self._spo[key]
        s, p, o = key.start, key.stop, key.step
        match (s is not None, p is not None, o is not None):
            case (True, True, True):
                return {Triple(s, p, o) for _ in (1,) if o in self._spo[s][p]}
            case (True, True, False):
                return (set(self._spo[s][p]),)
            case (True, False, True):
                return {PRED for PRED in self._osp[o][s] if PRED in self._osp[o][s]}
            case (True, False, False):
                return {
                    Triple(s, PRED, OBJ)
                    for PRED, objset in self._spo[s].items()
                    for OBJ in objset
                }
            case (False, True, True):
                return (set(self._pos[p][o]),)
            case (False, True, False):
                return (
                    {
                        Triple(SUB, p, OBJ)
                        for OBJ, subset in self._pos[p].items()
                        for SUB in subset
                    },
                )
            case (False, False, True):
                return {
                    Triple(SUB, PRED, o)
                    for SUB, predset in self._osp[o].items()
                    for PRED in predset
                }
            case (False, False, False):
                return {
                    Triple(SUB, PRED, OBJ)
                    for SUB, predset in self._spo.items()
                    for PRED, objset in predset.items()
                    for OBJ in objset
                }

    def __len__(self):
        return len(self._spo)

    def __iter__(self):
        """Return the same iterator as Store[::] for convenience."""
        return (
            (SUB, PRED, OBJ)
            for SUB, predset in self._spo.items()
            for PRED, objset in predset.items()
            for OBJ in objset
        )

    def __contains__(self, value):
        s, p, o = value
        try:
            return o in self._spo[s][p]
        except KeyError:
            return False

    def add(self, *, s: int, p: int, o: int):
        def add2index(index, a, b, c):
            if a not in index:
                index[a] = {b: {c}}
            else:
                if b not in index[a]:
                    index[a][b] = {c}
                else:
                    index[a][b].add(c)

        if s is None or (s, p, o) in self:
            warn(f"{'<unknown expression ERROR>':o}", FailedToComply)
        if isinstance(s, Triple):
            if s not in self:
                raise FailedToComply(
                    "Specified subject (Triple) was not found in the store."
                )
        else:
            if not isinstance(s, int):
                raise FailedToComply(
                    "Subject is neither a Triple nor an instance of int.", s, type(s)
                )

        if not p.validate(o):
            raise StoreException(f"{o} does not match the criteria for predicate {p}")
        add2index(self._spo, s, p, o)
        add2index(self._pos, p, o, s)
        add2index(self._osp, o, s, p)
        return Triple(s, p, o)

    def __setitem__(self, key, value):
        assert isinstance(key, slice), (
            "Must be assigned using a slice (ex: Store[:foo:] = 23)."
        )

        p = key.stop
        o = value

        if not isinstance(key.start, (int, Triple)):
            return [self.add(s=s, p=p, o=o) for s in key.start]
        return self.add(s=key.start, p=p, o=o)

    def create_subjects_with(self, predobjects):
        """Add all combinations of predicate:object to the store and create new entities for each combo.

        From a dict of key:[list of values] we produce a list of all combinations
        of [(key1,value1), (key1,value2)] from which we can build a new dict
        to pass into self.add as parameters.

        """
        combinations = product(*[
            [(k, v) for v in predobjects[k]] for k in predobjects.keys()
        ])
        subjects = []
        # Trick is to create new entities with a sentinel of None so there is an indefinite amount
        for C, s in zip(combinations, iter(int, None)):
            for p, o in C:
                self.add(s=s, p=p, o=o)
            subjects.append(s)
        return subjects

    def set_all(self, *, subjects: list[int], predobjects: dict):
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
        k, v = clauses.pop()
        result = set(self[:k:v])
        for k, v in clauses:
            result.intersection_update(set(self[:k:v]))
        if len(result) > 1:
            raise AttributeError("More than a single item matches the criteria.")
        elif not result:
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
        return self.store[self.triple[0] : self.triple[1] : self.triple[2]]


class QuerySet:
    def __init__(self, values):
        self.values = values

    def __getattr__(self, name):
        """Get the value of an attribute."""
        if name in self._sets:
            return self._sets[name]
        else:
            raise AttributeError(f"{name} is not a method or attribute of set or ")
