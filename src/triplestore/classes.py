from dataclasses import dataclass
from functools import singledispatchmethod
from itertools import product
from typing import Any
from uuid import NAMESPACE_DNS, uuid4, uuid5

from beartype import beartype

_sp: dict[int, set[int]] = {}
_po: dict[int, set[int]] = {}
_os: dict[int, set[int]] = {}
_kv_store: dict[int, Any] = {}


class StoreException(UserWarning):
    """All Exceptions specific to this package for easy filtering."""


class FailedToComply(StoreException):
    pass


class NotFound(StoreException):
    pass


class Triple:
    """A triple of (subject, predicate, object)."""

    __slots__ = ("_s", "_p", "_o")

    def __init__(self, s: int, p: int, o: int):
        self._s = s
        self._p = p
        self._o = o

    @property
    def s(self):
        return E(self._s)

    @property
    def p(self):
        return E(self._p)

    @property
    def o(self):
        return E(self._o)


class E:
    __slots__ = ("id",)

    def __init__(self, id_: int | None = None):
        if id_ is None:
            id_ = uuid4().int
        assert isinstance(id_, int)
        self.id = id_

    @classmethod
    def from_value(cls, value):
        id_ = uuid5(NAMESPACE_DNS, value).int
        if id_ not in _kv_store:
            _kv_store[id_] = value
        return cls(id_)

    @property
    def value(self):
        return _kv_store[self.id]

    def __repr__(self):
        return f"E({self.id})"

    def __str__(self):
        return _kv_store.get(self.id) or f"E({self.id})"

    def __eq__(self, other):
        return self.id == other.id


class Value:
    """Some content to be put in the kv_store as a typed value."""

    def __init__(self, value: Any, type_: type):
        self.value = value
        self.type = type_

    def __repr__(self):
        return f"Value({self.value})"

    def __str__(self):
        return str(self.value)

    def __eq__(self, other):
        return self.value == other.value

    def validate(self):
        return isinstance(self.value, self.type)


class TripleStore:
    """A set of three dicts that work together as one."""

    def __init__(self, /, *, kv_store: dict[int, Any], relations: dict[int, set[int]]):
        global _kv_store, _sp, _po, _os
        _kv_store = kv_store

        self._spo: dict[int, dict[int, set[int]]] = {}
        "{subject: {predicate: set([object])}}"
        self._pos: dict[int, dict[int, set[int]]] = {}
        "{predicate: {object: set([subject])}}"
        self._osp: dict[int, dict[int, set[int]]] = {}
        "{object: {subject: set([predicate])}}"

    @beartype
    def __getitem__(self, key: slice):
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

        assert isinstance(s, (E, None))

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

    @beartype
    def __len__(self) -> int:
        return len(self._spo)

    @beartype
    def __iter__(self):
        """Return the same iterator as Store[::] for convenience."""
        return (
            (SUB, PRED, OBJ)
            for SUB, predset in self._spo.items()
            for PRED, objset in predset.items()
            for OBJ in objset
        )

    @beartype
    def __contains__(self, value: tuple[int, int, int]) -> bool:
        s, p, o = value
        try:
            return o in self._spo[s][p]
        except KeyError:
            return False

    @singledispatchmethod
    def add(self, arg):
        raise NotImplementedError("Unsupported type")

    @add.register(Triple)
    def add_triple(self, triple: Triple):
        assert isinstance(triple, Triple)
        s, p, o = triple.s.id, triple.p.id, triple.o.id
        _add2index(self._spo, s, p, o)
        _add2index(self._pos, p, o, s)
        _add2index(self._osp, o, s, p)
        return Triple(s, p, o)

    @beartype
    @add.register(E)
    def add(self, s: E, p: E, o: E) -> Triple:
        assert isinstance(s, E)
        assert isinstance(p, E)
        assert isinstance(o, E)
        s, p, o = s.id, p.id, o.id

        _add2index(self._spo, s, p, o)
        _add2index(self._pos, p, o, s)
        _add2index(self._osp, o, s, p)
        return Triple(s, p, o)

    @beartype
    def __setitem__(self, key: slice, value: int):
        assert isinstance(key, slice), (
            "Must be assigned using a slice (ex: Store[:foo:] = 23)."
        )

        p = key.stop
        o = value

        if not isinstance(key.start, (int, Triple)):
            return [self.add(s=s, p=p, o=o) for s in key.start]
        return self.add(s=key.start, p=p, o=o)

    @beartype
    def create_subjects_with(self, predobjects: dict[int, list[int]]) -> list[int]:
        """Add all combinations of predicate:object to the store and create new entities for each combo.

        From a dict of key:[list of values] we produce a list of all combinations
        of [(key1,value1), (key1,value2)] from which we can build a new dict
        to pass into self.add as parameters.

        """
        combinations = product(*[[(k, v) for v in predobjects[k]] for k in predobjects])
        subjects = []
        # Trick is to create new entities with a sentinel of None so there is an indefinite amount
        for C, s in zip(combinations, iter(int, None)):
            for p, o in C:
                self.add(s=s, p=p, o=o)
            subjects.append(s)
        return subjects

    @beartype
    def set_all(
        self, *, subjects: list[int], predobjects: dict[int, list[int]]
    ) -> list[Triple]:
        results = []
        for s in subjects:
            for p, O in predobjects.items():  # noqa: E741
                for o in O:
                    r = self.add(s=s, p=p, o=o)
                    results.append(r)
        return results

    @beartype
    def get(self, clause_dict: dict[int, int]) -> Triple | None:
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

    @beartype
    def get_all(self, clause_dict: dict[int, int]) -> set[Triple]:
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

    @beartype
    def get_last_added(self) -> int:
        """Get the item that was last added to the store."""
        return list(self._spo.keys())[-1]

    @beartype
    def __delitem__(self, item: Triple):
        raise NotImplementedError

    @beartype
    def __str__(self) -> str:
        return "".join(f"{str(s)} {str(p)} {str(o)}\n" for s, p, o in self)


@dataclass
class Query:
    """Class representing a query to the store."""

    store: TripleStore
    spo: Triple

    @beartype
    def __call__(self) -> set[Triple]:
        return self.store[self.triple[0] : self.triple[1] : self.triple[2]]


class QuerySet:
    def __init__(self, values):
        self.values = values

    @beartype
    def __getattr__(self, name: str):
        """Get the value of an attribute."""
        if name in self._sets:
            return self._sets[name]
        else:
            raise AttributeError(f"{name} is not a method or attribute of set or ")


def _add2index(index, a: int, b: int, c: int):
    if a not in index:
        index[a] = {b: {c}}
    else:
        if b not in index[a]:
            index[a][b] = {c}
        else:
            index[a][b].add(c)
