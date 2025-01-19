import pytest  # noqa: F401
from hypothesis import given  # noqa: F401
from hypothesis import strategies as st  # noqa: F401
from triplestore.classes import E, Triple, TripleStore  # noqa: F401

store = TripleStore(kv_store={}, relations={})


@pytest.mark.xfail
def test_triplestore_get_valid(store: TripleStore):
    s, p, o = 1, 2, 3
    triple = store.add(s=s, p=p, o=o)
    assert store.get({s: p}) == triple


@pytest.mark.xfail
def test_triplestore_delitem(store: TripleStore):
    with raises(NotImplementedError):
        del store[1]


@pytest.mark.skip(reason="Not implemented")
def test_query_call(store: TripleStore):
    s, p, o = 1, 2, 3
    store.add(s=s, p=p, o=o)
    query = Query(store, Triple(s, p, o))
    assert query() == {Triple(s, p, o)}


@pytest.mark.skip(reason="Not implemented")
def test_queryset_getattr():
    qs = QuerySet([1, 2, 3])
    with raises(AttributeError):
        qs.nonexistent_attribute


@pytest.mark.xfail
def test_triplestore_get_all(store: TripleStore):
    s, p, o = 1, 2, 3
    store.add(s=s, p=p, o=o)
    assert store.get_all({s: p}) == {Triple(s, p, o)}
