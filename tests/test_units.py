from uuid import NAMESPACE_DNS, uuid5

from hypothesis import given
from hypothesis import strategies as st
from pytest import raises
from triplestore.classes import (
    E,
    FailedToComply,
    Query,
    QuerySet,
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
def test_E_from_value(value):
    e4 = E.from_value(value=value)
    assert e4.value == value
    e5 = E.from_value(value=value)
    assert e4 == e5


def test_E_repr():
    e1 = E()
    assert repr(e1) == f"E({e1.id})"
    e2 = E.from_value("test")
    assert repr(e2) == f"E({uuid5(NAMESPACE_DNS, 'test').int})"


def test_triplestore_add_valid(store: TripleStore):
    s, p, o = E(1), E(2), E(3)
    triple = store.add(s, p, o)
    assert triple == Triple(s, p, o)
    assert triple in store


def test_triplestore_add_invalid(store):
    _s, p, o = 1, 2, 3
    with raises(FailedToComply):
        store.add(s=None, p=p, o=o)
    with raises(FailedToComply):
        store.add(s="invalid", p=p, o=o)


def test_triplestore_setitem_valid(store):
    s, p, o = 1, 2, 3
    store[s:p] = o
    assert (s, p, o) in store


def test_triplestore_setitem_invalid(store):
    with raises(AssertionError):
        store[1] = 2


def test_triplestore_create_subjects_with(store):
    predobjects = {1: [2, 3], 4: [5]}
    subjects = store.create_subjects_with(predobjects)
    assert len(subjects) == 2


def test_triplestore_set_all(store):
    subjects = [1, 2]
    predobjects = {3: [4, 5]}
    results = store.set_all(subjects=subjects, predobjects=predobjects)
    assert len(results) == 4


def test_triplestore_get_valid(store):
    s, p, o = 1, 2, 3
    store.add(s=s, p=p, o=o)
    assert store.get({s: p}) == Triple(s, p, o)


def test_triplestore_get_invalid(store):
    s, p, o = 1, 2, 3
    store.add(s=s, p=p, o=o)
    with raises(AttributeError):
        store.get({s: p, 4: 5})


def test_triplestore_get_all(store):
    s, p, o = 1, 2, 3
    store.add(s=s, p=p, o=o)
    assert store.get_all({s: p}) == {Triple(s, p, o)}


def test_triplestore_get_last_added(store):
    s, p, o = 1, 2, 3
    store.add(s=s, p=p, o=o)
    assert store.get_last_added() == s


def test_triplestore_str(store):
    s, p, o = 1, 2, 3
    store.add(s=s, p=p, o=o)
    assert str(store) == f"{s} {p} {o}\n"


def test_triplestore_delitem(store):
    with raises(NotImplementedError):
        del store[1]


def test_query_call(store):
    s, p, o = 1, 2, 3
    store.add(s=s, p=p, o=o)
    query = Query(store, Triple(s, p, o))
    assert query() == {Triple(s, p, o)}


def test_queryset_getattr():
    qs = QuerySet([1, 2, 3])
    with raises(AttributeError):
        qs.nonexistent_attribute


def test_triplestore_getitem_case1(store):
    s, p, o = 1, 2, 3
    store.add(s=s, p=p, o=o)
    assert store[s:p:o] == {Triple(s, p, o)}


def test_triplestore_getitem_case2(store):
    s, p, o = 1, 2, 3
    store.add(s=s, p=p, o=o)
    assert store[s:p:None] == ({o},)


def test_triplestore_getitem_case3(store):
    s, _, o = E(1), 2, E(3)
    store.add(s=s, p=4, o=o)
    assert store[s:None:o] == {4}


def test_triplestore_getitem_case4(store):
    s, p, o = 1, 2, 3
    store.add(s=s, p=p, o=o)
    store.add(s=s, p=4, o=o)
    assert store[s:None:None] == {Triple(s, p, o), Triple(s, 4, o)}


def test_triplestore_getitem_case5(store):
    s, p, o = 1, 2, 3
    store.add(s=s, p=p, o=o)
    assert store[None:p:o] == ({s},)


def test_triplestore_getitem_case6(store):
    s, p, o = 1, 2, 3
    store.add(s=s, p=p, o=o)
    assert store[None:p:None] == ({Triple(s, p, o)},)


def test_triplestore_getitem_case7(store):
    s, p, o = 1, 2, 3
    store.add(s=s, p=p, o=o)
    store.add(s=s, p=4, o=o)
    assert store[None:None:o] == {Triple(s, p, o), Triple(s, 4, o)}


def test_triplestore_getitem_case8(store):
    s, p, o = 1, 2, 3
    store.add(s=s, p=p, o=o)
    store.add(s=s, p=4, o=o)
    assert store[None:None:None] == {Triple(s, p, o), Triple(s, 4, o)}
