from __future__ import annotations

"""
TripleStore.
"""

from dataclasses import dataclass
from itertools import product
from typing import Any, Final, Generator

import numpy as np
from beartype import beartype
from numpy.typing import NDArray

from .keys import E

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
    """A triplet of subjects, predicates, and objects."""

    __slots__ = ("s_", "p_", "o_")

    def __init__(self, s: E, p: E, o: E):
        self.s_ = s
        self.p_ = p
        self.o_ = o

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
        return f"Triple(s={self.s}, p={self.p}, o={self.o})"


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


from uuid import UUID

import numpy as np

# from tree import BPlusTree, TreeConfig


class UUID128:
    def __init__(self, uuid: UUID):
        self.high = uuid.int >> 64
        self.low = uuid.int & 0xFFFFFFFFFFFFFFFF

    def to_hdf5(self) -> np.ndarray:
        return np.array((self.high, self.low), dtype=[("high", "<u8"), ("low", "<u8")])


class CompositeKeyEngine:
    """Responsible for secure composite key generation"""

    # Verified 64-bit primes (Miller-Rabin)
    PERTURB_HIGH = 0xD1B54A32D192ED03
    PERTURB_LOW = 0x81B1D42A3B609BED
    MASK_EVEN = 0xAAAAAAAAAAAAAAAA
    MASK_ODD = 0x5555555555555555

    @staticmethod
    def _rot64(x: int, n: int) -> int:
        return ((x << n) | (x >> (64 - n))) & 0xFFFFFFFFFFFFFFFF

    @classmethod
    def create_key(cls, a: UUID128, b: UUID128) -> np.ndarray:
        """Generate composite key for index storage"""
        # Your V4 composite key logic
        h = cls._enhanced_mix(a.high ^ b.low, 17) ^ cls.PERTURB_HIGH
        l = cls._enhanced_mix(a.low ^ b.high, 23) ^ cls.PERTURB_LOW

        rotated_h = cls._rot64(h, 19) ^ (l & cls.MASK_EVEN)
        rotated_l = cls._rot64(l, 23) ^ (h & cls.MASK_ODD)

        final_high = cls._enhanced_mix(rotated_h ^ rotated_l, 5)
        final_low = cls._enhanced_mix(rotated_l ^ rotated_h, 11)

        return np.array(
            (final_high, final_low), dtype=[("high", "<u8"), ("low", "<u8")]
        )


class TripleStore:
    def __init__(self, storage_path: Path):
        config = TreeConfig()
        self._sp = BPlusTree(storage_path / "sp.h5", config)
        self._po = BPlusTree(storage_path / "po.h5", config)
        self._os = BPlusTree(storage_path / "os.h5", config)
        self._keygen = CompositeKeyEngine()

    def add(self, s: UUID, p: UUID, o: UUID):
        """Add triple through composite key derivation"""
        s_uuid = UUID128(s)
        p_uuid = UUID128(p)
        o_uuid = UUID128(o)

        # Generate index-specific composite keys
        sp_key = self._keygen.create_key(s_uuid, p_uuid)
        po_key = self._keygen.create_key(p_uuid, o_uuid)
        os_key = self._keygen.create_key(o_uuid, s_uuid)

        # Store in respective B+Trees
        self._sp.insert(sp_key, o_uuid.to_hdf5())
        self._po.insert(po_key, s_uuid.to_hdf5())
        self._os.insert(os_key, p_uuid.to_hdf5())

    def query(self, s: UUID, p: UUID) -> list[UUID]:
        """Query using composite key derivation"""
        sp_key = self._keygen.create_key(UUID128(s), UUID128(p))
        results = self._sp.get(sp_key)
        return [UUID(int=(r["high"] << 64) | r["low"]) for r in results]
