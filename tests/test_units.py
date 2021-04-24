import os
import sys

here = os.path.split(os.path.abspath(os.path.dirname(__file__)))
src = os.path.join(here[0], "src")
sys.path.insert(0,src)


from unittest import TestCase, skip

from hypothesis import assume, given
from hypothesis import strategies as st
from pytest import fixture, raises
from triplestore.store import E, Predicate, Query, QuerySet, TripleStore


@given(st.text())
def test_E(url):
    # hypothesis testing on name should be possible, but it must be an identifier
    e1 = E()
    e2 = eval(repr(e1))
    # Equality is determined by their UUID, which must be the same now.
    assert e1 == e2
    # However, they can't be the same object.
    assert e1 is not e2
    # On the other hand, an entity created on its own must have a new UUID.
    e3 = E()
    assert e1 != e3
    # The id argument must be a valid UUID.
    with raises(AttributeError):
        E(id_=2)
    # Let's use all arguments.
    e4 = E(name='test', id_='b19102c6-20b8-4afb-8520-ef910b1dc93b',url=url)
    assert str(e4) == "test"
    assert repr(e4) == f"E(name='test', id_='b19102c6-20b8-4afb-8520-ef910b1dc93b', url='{url}')"
    # repr code often is quite noisy, so we need to check that
    assert repr(e1) == f"E(id_='{e1.id}')"
    test = E(name="test")
    assert str(test) == "test"
    assert repr(test) == f"E(name='test', id_='{test.id}')"
    
def test_Predicate():
    class Test(Predicate):
        def validate(self, value):
            return isinstance(value, str)
        
    test = Test()
    assert test.validate("test")
    assert test.name == "Test"
    