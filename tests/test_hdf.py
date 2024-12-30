import uuid
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from triplestore.hdf import RelationStore


@pytest.fixture
def uuid_store():
    """
    Fixture to set up the UUIDStore and store some initial tuples.
    Cleans up the test file after each test.
    """
    file_path = Path("test_uuids.h5")
    if file_path.exists():
        file_path.unlink()  # Ensure the file is re-generated from scratch
    store = RelationStore(file_path)
    namespace = uuid.uuid5(uuid.NAMESPACE_DNS, "test")
    tuples = [
        (
            uuid.uuid5(namespace, str(i)),
            uuid.uuid5(namespace, str(i + 1)),
            uuid.uuid5(namespace, str(i + 2)),
        )
        for i in range(10)
    ]
    store.store_tuples(tuples)
    yield store, tuples
    if file_path.exists():
        file_path.unlink()


def test_store_and_retrieve_tuples(uuid_store):
    """
    Test storing and retrieving all tuples.
    """
    store, original_tuples = uuid_store
    retrieved_tuples = store.retrieve_tuples()
    assert len(retrieved_tuples) == len(original_tuples)
    assert retrieved_tuples == original_tuples


def test_retrieve_by_first_uuid(uuid_store):
    """
    Test retrieving tuples by the first UUID.
    """
    store, original_tuples = uuid_store
    first_uuid = original_tuples[0][0]
    retrieved_tuples = store.retrieve_by_first_uuid(first_uuid)
    expected_tuples = [t for t in original_tuples if t[0] == first_uuid]
    assert len(retrieved_tuples) == len(expected_tuples)
    assert retrieved_tuples == expected_tuples


@given(
    tuples=st.lists(
        st.tuples(st.uuids(version=5), st.uuids(version=5), st.uuids(version=5)),
        min_size=1,
        max_size=100,
    )
)
def test_store_and_retrieve_tuples_hypothesis(uuid_store, tuples):
    """
    Hypothesis test for storing and retrieving all tuples.
    """
    store, _ = uuid_store
    store.store_tuples(tuples)
    retrieved_tuples = store.retrieve_tuples()
    assert len(retrieved_tuples) == len(tuples)
    assert retrieved_tuples == tuples


@given(
    tuples=st.lists(
        st.tuples(st.uuids(version=5), st.uuids(version=5), st.uuids(version=5)),
        min_size=1,
        max_size=100,
    )
)
def test_retrieve_by_first_uuid_hypothesis(uuid_store, tuples):
    """
    Hypothesis test for retrieving tuples by the first UUID.
    """
    store, _ = uuid_store
    store.store_tuples(tuples)
    first_uuid = tuples[0][0]
    retrieved_tuples = store.retrieve_by_first_uuid(first_uuid)
    expected_tuples = [t for t in tuples if t[0] == first_uuid]
    assert len(retrieved_tuples) == len(expected_tuples)
    assert retrieved_tuples == expected_tuples


@given(
    tuples=st.lists(
        st.tuples(st.uuids(version=5), st.uuids(version=5), st.uuids(version=5)),
        min_size=1,
        max_size=100,
    ),
    new_tuple=st.tuples(st.uuids(version=5), st.uuids(version=5), st.uuids(version=5)),
)
def test_insert_and_retrieve_min_hypothesis(uuid_store, tuples, new_tuple):
    """
    Hypothesis test for inserting a new tuple and retrieving the minimum tuple.
    """
    store, _ = uuid_store
    store.store_tuples(tuples)
    store.insert_tuple(new_tuple)
    min_tuple = store.retrieve_min()
    assert min_tuple == min([new_tuple] + tuples, key=lambda x: int(x[0]))


if __name__ == "__main__":
    pytest.main()
