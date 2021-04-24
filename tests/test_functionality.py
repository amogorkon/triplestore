import os
import sys

here = os.path.split(os.path.abspath(os.path.dirname(__file__)))
src = os.path.join(here[0], "src")
sys.path.insert(0,src)

from unittest import skip
from unittest.mock import Mock

from pytest import fixture, raises
from triplestore.store import E, Predicate, Query, Triple, TripleStore


@fixture
def body():
    return TripleStore()

@fixture
def name():
    class Name(Predicate):
        pass
    return Name()

@fixture
def is_a():
    class Is_a(Predicate):
        pass
    return Is_a()

@fixture
def destroyed():
    class Destroyed(Predicate):
        pass
    return Destroyed()

@fixture
def has():
    class Has(Predicate):
        pass
    return Has()
    
def test_bodily_functions(body, name, is_a):
    # Let's make a new entity in body with the name "head".
    e = body.create_subjects_with({name:["head"]})[0]
    # Indexing body with the entity as single argument should return a dict with its attributes.
    assert body[e] == {name: {"head"}}
    # body.get should return a single entity, not an iterator.
    assert body.get({name:"head"}) == e
    # body.get_all should return a set
    assert body.get_all({name: "head"}) == {e}
    # Let's see if this works with an enitity made outside.
    e2 = E()
    # We should be able to use the dict of attributes of a single index as argument to set_all.
    body.set_all(subjects=[e2], predobjects=body[e])
    # body.get_last_added should return the entity inserted last into the store.
    assert body.get_last_added() == e2
    # body[::] should return a set with all triples in the store, the iterator over body should produce the same.
    assert body[::] == {(e, name, "head"), (e2, name, "head")} == {x for x in body}
    # Using the index-assignment pattern should work for 1 or many entities as subjects, a given pred and an object.
    body[body[:name:"head"]:is_a] = "part"
    # body.get_all with a dict should produce the same result as using slices and ANDing the produced sets.
    assert body.get_all({is_a:"part", name:"head"}) == {e, e2} == body[:name:"head"] & body[:is_a:"part"]
    

def test_Triple_as_subject(body, has, destroyed):
    hand = E(name="hand")
    ring = E(name="ring")
    body[hand:has] = ring
    assert Triple(hand, has, ring) in body
    body[Triple(hand, has, ring):destroyed] = True
