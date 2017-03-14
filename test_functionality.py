
from pytest import fixture
from unittest.mock import Mock

from store.triplestore import TripleStore, E, P

@fixture
def store():
    return TripleStore()

def test_store(store):
    store[E("spam")] = P("ham"), E("eggs")
    assert list(store[E("spam")::]) == [(E("spam"),P("ham"), E("eggs"))]