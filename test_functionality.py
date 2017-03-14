
from pytest import fixture
from unittest.mock import Mock

from store.triplestore import TripleStore, E, P

@fixture
def store():
    return TripleStore()

def test_store(store):
    store[E("anselm"):P("name")] = "Anselm Kiefner"
    assert list(store[::]) == [('anselm', 'name', 'Anselm Kiefner')]