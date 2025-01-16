import os
import uuid
from pathlib import Path
from random import shuffle
import time

import psutil
from pympler import asizeof
from beartype import beartype

from triplestore.hdf import RelationStore


@beartype
def generate_uuids() -> list[uuid.UUID]:
    random_uuids = [uuid.uuid4() for _ in range(300_000)]
    non_random_uuids = [
        uuid.uuid5(uuid.NAMESPACE_DNS, f"name{i}") for i in range(600_000)
    ]
    return random_uuids + non_random_uuids


@beartype
def shuffled(uuids: list[uuid.UUID]) -> list[uuid.UUID]:
    X = uuids.copy()
    shuffle(X)
    return X


uuids = generate_uuids()

_sp: dict[int, int] = {int(i): int(j) for i, j in zip(shuffled(uuids), shuffled(uuids))}
_po: dict[int, int] = {int(i): int(j) for i, j in zip(shuffled(uuids), shuffled(uuids))}
_os: dict[int, int] = {int(i): int(j) for i, j in zip(shuffled(uuids), shuffled(uuids))}

print(f"_sp: {list(_sp.items())[:5]}")  # Print first 5 items for verification
print(f"_po: {list(_po.items())[:5]}")  # Print first 5 items for verification
print(f"_os: {list(_os.items())[:5]}")  # Print first 5 items for verification

# Measure the size of the dictionaries
print(f"Size of _sp: {asizeof.asizeof(_sp) / (1024 * 1024):.2f} MB")
print(f"Size of _po: {asizeof.asizeof(_po) / (1024 * 1024):.2f} MB")
print(f"Size of _os: {asizeof.asizeof(_os) / (1024 * 1024):.2f} MB")

# Measure the memory usage of the entire program
process = psutil.Process(os.getpid())
memory_info = process.memory_info()
memory_usage_mb = memory_info.rss / (1024 * 1024)

print(f"Total memory usage: {memory_usage_mb:.2f} MB")

# Store the dictionaries using RelationStore
start_time = time.time()
with RelationStore(Path(__file__).parent / "uuids.h5") as store:
    store.store_dict("sp", _sp)
    store.store_dict("po", _po)
    store.store_dict("os", _os)
write_time = time.time() - start_time
print(f"Time taken to write dictionaries: {write_time:.2f} seconds")

# Load the dictionaries back
start_time = time.time()
with RelationStore(Path(__file__).parent / "uuids.h5") as store:
    new_sp = store.retrieve_dict("sp")
    new_po = store.retrieve_dict("po")
    new_os = store.retrieve_dict("os")
read_time = time.time() - start_time
print(f"Time taken to read dictionaries: {read_time:.2f} seconds")

# Compare the new dictionaries with the original dictionaries
print(f"_sp equals new_sp: {_sp == new_sp}")
print(f"_po equals new_po: {_po == new_po}")
print(f"_os equals new_os: {_os == new_os}")
