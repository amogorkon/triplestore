import pytest
from triplestore.classes import E, Triple


@pytest.mark.xfail
def test_bodily_functions(body, name, is_a):
    # Let's make a new entity in body with the name "head".
    e = body.create_subjects_with({name: ["head"]})[0]
    # Indexing body with the entity as single argument should return a dict with its attributes.
    assert body[e] == {name: {"head"}}
    # body.get should return a single entity, not an iterator.
    assert body.get({name: "head"}) == e
    # body.get_all should return a set
    assert body.get_all({name: "head"}) == {e}
    # Let's see if this works with an enitity made outside.
    e2 = E()
    # We should be able to use the dict of attributes of a single index as argument to set_all.
    body.set_all(subjects=[e2], predobjects=body[e])
    # body.get_last_added should return the entity inserted last into the store.
    assert body.get_last_added() == e2
    # body[::] should return a set with all triples in the store, the iterator over body should produce the same.
    assert body[::] == {(e, name, "head"), (e2, name, "head")} == set(body)
    # Using the index-assignment pattern should work for 1 or many entities as subjects, a given pred and an object.
    body[body[:name:"head"] : is_a] = "part"
    # body.get_all with a dict should produce the same result as using slices and ANDing the produced sets.
    assert (
        body.get_all({is_a: "part", name: "head"})
        == {e, e2}
        == body[:name:"head"] & body[:is_a:"part"]
    )


@pytest.mark.xfail
def test_Triple_as_subject(store, has, destroyed):
    hand = E(name="hand")
    ring = E(name="ring")
    store[hand:has] = ring
    assert Triple(hand, has, ring) in store
    store[Triple(hand, has, ring) : destroyed] = True
