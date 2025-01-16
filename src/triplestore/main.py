"""
This triplestore works as follows:

There are three parts: the key-value store, the hdf5-relationship matrix, and the triplestore with the logic. The key-value store can be anything that implements a dict-like interface and can be easily swapped out for a more performant version. As the relationship matrix is hdf5-based, it is already quite performant and can be used as is, but different options can be explored.
The triplestore is the logic that ties everything together and provides a simple interface to the user. It is the only part that the user should interact with directly.

There is a simple key-value with {int: Any}, where the key is the uuid5 of the value. If you want the key, just calculate the hash (sha-1).

The triplestore itself is a set of three dicts that work together as one. Each dict is a mapping of {int: {int: Set[int]}}, only operating on the uuids of entities and predicates.
To resolve the uuids back to their names, we check the key-value store.
The triplestore-dicts can be implemented in different ways, taking into account that they are only dealing with {int: Set[int]}.

"""

from triplestore.classes import TripleStore, Value

kv_store: dict[int, Value] = {}
relations: dict[int, set[int]] = {}

store = TripleStore(kv_store=kv_store, relations=relations)
