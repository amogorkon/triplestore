from uuid import NAMESPACE_DNS, uuid5

from hypothesis import given
from hypothesis import strategies as st
from triplestore.classes import (
    E,
    Triple,
    TripleStore,
)


def test_E_equality():
    e1 = E()
    e2 = eval(repr(e1))
    assert e1 == e2
    assert e1 is not e2


def test_E_new_uuid():
    e1 = E()
    e2 = E()
    assert e1 != e2


@given(st.text())
def test_E_from_value(value: str):
    e4 = E.from_str(value=value)
    assert e4.value == value  # type: ignore
    e5 = E.from_str(value=value)
    assert e4 == e5


def test_E_repr():
    e1 = E()
    assert repr(e1) == f"E({int(e1)})"
    e2 = E.from_str("test")
    assert repr(e2) == f"E({uuid5(NAMESPACE_DNS, 'test').int})"


def test_triplestore_add_valid(store: TripleStore):
    s, p, o = E(1), E(2), E(3)
    triple = store.add(s, p, o)
    assert triple == Triple(1, 2, 3)
    assert triple in store


def test_triplestore_setitem_valid(store: TripleStore):
    s, p, o = 1, 2, 3
    store[s:p] = o
    assert Triple(s, p, o) in store


def test_triplestore_create_subjects_with(store: TripleStore):
    predobjects = {1: [2, 3], 4: [5]}
    entries = store.create_subjects_with(predobjects)
    assert len(list(entries)) == 4


def test_triplestore_set_all(store: TripleStore):
    subjects = [1, 2]
    predobjects = {3: [4, 5]}
    store.set_all(subjects=subjects, predobjects=predobjects)
    assert len(store[1::]) == 2 and len(store[2::]) == 2


def test_triplestore_get_invalid(store: TripleStore):
    s, p, o = 1, 2, 3
    store.add(s=s, p=p, o=o)
    assert store.get({s: p, 4: 5}) is None


def test_triplestore_get_last_added(store: TripleStore):
    s, p, o = 1, 2, 3
    store.add(s=s, p=p, o=o)
    assert store.get_last_added() == s


def test_triplestore_str(store: TripleStore):
    s, p, o = 1, 2, 3
    store.add(s=s, p=p, o=o)
    assert str(store) == f"{s} {p} {o}\n"


def test_triplestore_getitem_case1(store: TripleStore):
    s, p, o = 1, 2, 3
    store.add(s=s, p=p, o=o)
    assert store[s:p:o] == {Triple(s, p, o)}


def test_triplestore_getitem_case2(store: TripleStore):
    s, p, o = 1, 2, 3
    store.add(s=s, p=p, o=o)
    assert store[s:p:None] == {Triple(s=1, p=2, o=3)}


def test_triplestore_getitem_case3(store: TripleStore):
    s, _, o = E(1), 2, E(3)
    store.add(s=s, p=4, o=o)
    assert store[s:None:o] == {Triple(s=E(1), p=4, o=E(3))}


def test_triplestore_getitem_case4(store: TripleStore):
    s, p, o = 1, 2, 3
    store.add(s=s, p=p, o=o)
    store.add(s=s, p=4, o=o)
    assert store[s:None:None] == {Triple(s, p, o), Triple(s, 4, o)}


def test_triplestore_getitem_case5(store: TripleStore):
    s, p, o = 1, 2, 3
    store.add(s=s, p=p, o=o)
    assert store[None:p:o] == {Triple(s=1, p=2, o=3)}


def test_triplestore_getitem_case6(store: TripleStore):
    s, p, o = 1, 2, 3
    store.add(s=s, p=p, o=o)
    assert store[None:p:None] == {Triple(s, p, o)}


def test_triplestore_getitem_case7(store: TripleStore):
    s, p, o = 1, 2, 3
    store.add(s=s, p=p, o=o)
    store.add(s=s, p=4, o=o)
    assert store[None:None:o] == {Triple(s, p, o), Triple(s, 4, o)}


def test_triplestore_getitem_case8(store: TripleStore):
    s, p, o = 1, 2, 3
    store.add(s=s, p=p, o=o)
    store.add(s=s, p=4, o=o)
    assert store[None:None:None] == {Triple(s, p, o), Triple(s, 4, o)}


def test_triple_equality():
    s, p, o = E(1), E(2), E(3)
    triple1 = Triple(s, p, o)
    triple2 = Triple(s, p, o)
    assert triple1 == triple2


def test_triple_inequality():
    s1, p1, o1 = E(1), E(2), E(3)
    s2, p2, o2 = E(4), E(5), E(6)
    triple1 = Triple(s1, p1, o1)
    triple2 = Triple(s2, p2, o2)
    assert triple1 != triple2


def test_triple_repr():
    s, p, o = E(1), E(2), E(3)
    triple = Triple(s, p, o)
    assert eval(repr(triple)) == triple


def test_triple_str():
    s, p, o = E(1), E(2), E(3)
    triple = Triple(s, p, o)
    assert str(triple) == "Triple(s=1, p=2, o=3)"


def test_triple_hash():
    s, p, o = E(1), E(2), E(3)
    triple = Triple(s, p, o)
    # test if hash is consistent
    assert hash(triple) == hash(Triple(s, p, o))
    # test if the hash is sensitive to order
    assert hash(triple) != hash(Triple(s, o, p))
    # test if hash is 128 bit and thus usable as uuid
    assert 0 <= hash(triple) < 2**128
