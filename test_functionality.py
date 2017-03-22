
from pytest import fixture
from unittest.mock import Mock
from unittest import skip

from store.store import TripleStore, E, BasePredicate, Query

@fixture
def store():
    return TripleStore()

@fixture
def P():
    class Predicate(BasePredicate):
        name = 1
        side = 2
        is_a = 3
    return Predicate

def test_store(store, P):
    e = E()
    store[e:P.name] = "Anselm"
    assert store[e].name == {"Anselm"}