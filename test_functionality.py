
from pytest import fixture
from unittest.mock import Mock
from unittest import skip

from store.triplestore import TripleStore, E, P, Query

@fixture
def store():
    return TripleStore()

def test_store(store):
    store.add(name="Anselm Kiefner")
    e = store.get_last()
    assert store[e].name == "Anselm Kiefner"