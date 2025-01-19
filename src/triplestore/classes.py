from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Any, Generator
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


class E(int):
    __slots__ = ()

    def __new__(cls, id_: int | None = None) -> E:
        if id_ is None:
            id_ = uuid4().int
        assert isinstance(id_, int)
        return super().__new__(cls, id_)

    @classmethod
    def from_str(cls, value: str) -> E:
        id_ = uuid5(NAMESPACE_DNS, value).int
        if id_ not in _kv_store:
            _kv_store[id_] = value
        return cls(id_)

    @property
    def value(self) -> Any:
        return _kv_store[self]

    def __repr__(self):
        return f"E({super().__repr__()})"

    def __str__(self):
        return f"E({hex(self)[2:9]}..)" if len(hex(self)) > 9 else f"E({hex(self)[2:]})"


class Triple:
    """A triplet of subjects, predicates, and objects."""

    __slots__ = ("s_", "p_", "o_")

    def __init__(self, s: int, p: int, o: int):
        self.s_ = s
        self.p_ = p
        self.o_ = o

    @property
    def s(self):
        return E(self.s_)

    @property
    def p(self):
        return E(self.p_)

    @property
    def o(self):
        return E(self.o_)

    def __iter__(self):
        yield self.s
        yield self.p
        yield self.o

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Triple):
            return False
        return self.s_ == other.s_ and self.p_ == other.p_ and self.o_ == other.o_

    def __hash__(self):
        return (self.s_ ^ (self.p_ << 1) ^ (self.o_ << 2)) & ((1 << 128) - 1)

    def __repr__(self):
        return f"Triple(s={int(self.s)}, p={int(self.p)}, o={int(self.o)})"


class Value:
    """Some content to be put in the kv_store as a typed value."""

    def __init__(self, value: Any, type_: type):
        self.value = value
        self.type = type_

    def __repr__(self):
        return f"Value({self.value})"

    def __str__(self):
        return str(self.value)

    def __eq__(self, other: object) -> bool:
        return self.value == other.value if isinstance(other, Value) else False

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
    def __getitem__(self, key: slice | Triple | int) -> set[Triple]:
        """
        Get directly a result.

        May return a set of entities/ints, a dict of attributes, or a set of triples

        This is a mechanism inspired by the brilliant way numpy handles
        arrays and its vectorization methods.
        Another way of querying is the .get() method inspired by django which
        returns a Query object, representing a view on the dictionary to be evaluated lazily.
        """
        # Indexing store with an entity as single argument should return a dict with its attributes.
        if isinstance(key, int):
            return {
                Triple(key, PRED, OBJ)
                for PRED, objset in self._spo[key].items()
                for OBJ in objset
            }
        s: int | None = key.start  # type: ignore
        p: int | None = key.stop  # type: ignore
        o: int | None = key.step  # type: ignore

        assert isinstance(s, int | None)
        assert isinstance(p, int | None)
        assert isinstance(o, int | None)

        try:
            match (s is not None, p is not None, o is not None):
                case True, True, True:
                    assert isinstance(s, int)
                    assert isinstance(p, int)
                    assert isinstance(o, int)
                    if o in self._spo[s][p]:
                        return {Triple(s, p, o)}
                case True, True, False:
                    assert isinstance(s, int)
                    assert isinstance(p, int)
                    return {Triple(s, p, o) for o in self._spo[s][p]}
                case (True, False, True):
                    assert isinstance(s, int)
                    assert isinstance(o, int)
                    return {Triple(s, p_, o) for p_ in self._osp[o][s]}
                case False, True, True:
                    assert isinstance(p, int)
                    assert isinstance(o, int)
                    return {Triple(s_, p, o) for s_ in self._pos[p][o]}
                case True, False, False:
                    assert isinstance(s, int)
                    return {
                        Triple(s, PRED, OBJ)
                        for PRED, objset in self._spo[s].items()
                        for OBJ in objset
                    }
                case False, True, False:
                    assert isinstance(p, int)
                    return {
                        Triple(SUB, p, OBJ)
                        for OBJ, subset in self._pos[p].items()
                        for SUB in subset
                    }
                case False, False, True:
                    assert isinstance(o, int)
                    return {
                        Triple(SUB, PRED, o)
                        for SUB, predset in self._osp[o].items()
                        for PRED in predset
                    }
                case False, False, False:
                    return {
                        Triple(s_, p_, o_)
                        for s_, PRED in self._spo.items()
                        for p_, OBJ in PRED.items()
                        for o_ in OBJ
                    }
        except KeyError:
            return set()
        assert False, "Should never reach this point, but needed for type checking."
        return set()

    @beartype
    def __len__(self) -> int:
        return len(self._spo)

    @beartype
    def __iter__(self):
        """Return the same iterator as Store[::] for convenience."""
        return (
            Triple(SUB, PRED, OBJ)
            for SUB, predset in self._spo.items()
            for PRED, objset in predset.items()
            for OBJ in objset
        )

    @beartype
    def __contains__(self, triple: Triple) -> bool:
        try:
            return triple.o in self._spo[triple.s][triple.p]
        except KeyError:
            return False

    def add_triple(self, triple: Triple) -> Triple:
        assert isinstance(triple, Triple)
        s, p, o = triple
        return self._add_triple_to_indexes(s, p, o)

    def add(self, s: int, p: int, o: int) -> Triple:
        assert isinstance(s, int)
        assert isinstance(p, int)
        assert isinstance(o, int)
        return self._add_triple_to_indexes(s, p, o)

    def _add_triple_to_indexes(self, s: int, p: int, o: int):
        _add2index(self._spo, s, p, o)
        _add2index(self._pos, p, o, s)
        _add2index(self._osp, o, s, p)
        return Triple(s, p, o)

    @beartype
    def __setitem__(self, key: slice, value: int) -> Triple | list[Triple]:
        assert isinstance(key, slice), (
            "Must be assigned using a slice (ex: Store[:foo:] = 23)."
        )
        assert isinstance(key, slice)

        s = key.start
        p = key.stop
        o = value

        if not isinstance(s, (int, Triple)):
            return [self.add(s=s, p=p, o=o) for s in key.start]
        return self.add(s=key.start, p=p, o=o)

    @beartype
    def create_subjects_with(
        self, predobjects: dict[int, list[int]]
    ) -> Generator[Triple, None, None]:
        """Add all combinations of predicate:object to the store and create new entities for each combo.

        From a dict of key:[list of values] we produce a list of all combinations
        of [(key1,value1), (key1,value2)] from which we can build a new dict
        to pass into self.add as parameters.

        """
        combinations = product(*[[(k, v) for v in predobjects[k]] for k in predobjects])
        # Trick is to create new entities with a sentinel of None so there is an indefinite amount
        for C, s in zip(combinations, iter(int, None)):
            for p, o in C:
                yield self.add(s=s, p=p, o=o)

    @beartype
    def set_all(
        self, *, subjects: list[int], predobjects: dict[int, list[int]]
    ) -> None:
        for s in subjects:
            for p, O in predobjects.items():  # noqa: E741
                for o in O:
                    self.add(s=s, p=p, o=o)

    @beartype
    def get(self, clause_dict: dict[int, int], default: Any = None) -> Triple | None:
        """Get the item from the store that matches ALL clauses."""
        clauses = list(clause_dict.items())
        k, v = clauses.pop()
        result = set(self[:k:v])
        for k, v in clauses:
            result.intersection_update(set(self[:k:v]))
        if len(result) > 1:
            raise AttributeError("More than a single item matches the criteria.")
        elif not result:
            return default
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
        """Get the item that was last added to the store.

        BEWARE: This is not a promise! Depending on the backend, this may not be reliable.
        Use with caution. This is a convenience method for testing and debugging.
        """
        return list(self._spo.keys())[-1]

    @beartype
    def __delitem__(self, item: Triple) -> None:
        raise NotImplementedError

    @beartype
    def __str__(self) -> str:
        return "".join(f"{int(s)} {int(p)} {int(o)}\n" for s, p, o in self)


@dataclass
class Query:
    """Class representing a query to the store."""

    store: TripleStore
    triple: Triple

    @beartype
    def __call__(self) -> set[Triple]:
        return self.store[self.triple]


class QuerySet:
    def __init__(self, values: int):
        self.values = values

    @beartype
    def __getattr__(self, name: str):
        """Get the value of an attribute."""
        if name in self._sets:
            return self._sets[name]
        else:
            raise AttributeError(f"{name} is not a method or attribute of set or ")


def _add2index(index: dict[int, dict[int, set[int]]], a: int, b: int, c: int) -> None:
    if a not in index:
        index[a] = {b: {c}}
    else:
        if b not in index[a]:
            index[a][b] = {c}
        else:
            index[a][b].add(c)
