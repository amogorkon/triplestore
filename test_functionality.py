
from pytest import fixture
from unittest.mock import Mock
from unittest import skip

from store.triplestore import TripleStore, E, P

@fixture
def store():
    return TripleStore()

@skip("not there yet..")
def test_store(store):
    store[E("anselm"):P("name")] = "Anselm Kiefner"
    assert list(store[::]) == [('anselm', 'name', 'Anselm Kiefner')]
    assert store.query([("anselm", "?name")]) == "Anselm Kiefner"