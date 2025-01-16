import os
import uuid
from pathlib import Path
from random import shuffle

import psutil
from beartype import beartype
from bplustree.tree import BPlusTree
from pympler import asizeof

size = 10


@beartype
def generate_uuids() -> list[uuid.UUID]:
    return [uuid.uuid4() for _ in range(size)]


@beartype
def shuffled(uuids: list[uuid.UUID]) -> list[uuid.UUID]:
    uuids_copy = uuids[:]
    shuffle(uuids_copy)
    return uuids_copy


uuids = generate_uuids()

_sp: dict[int, int] = dict(zip(shuffled(uuids), shuffled(uuids)))
_po: dict[int, int] = dict(zip(shuffled(uuids), shuffled(uuids)))
_os: dict[int, int] = dict(zip(shuffled(uuids), shuffled(uuids)))

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


class BTreeStore:
    @beartype
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.tree = BPlusTree(str(file_path), order=50)

    @beartype
    def insert(self, key: int, value: bytes):
        self.tree[key] = value

    @beartype
    def get(self, key: int) -> bytes:
        return self.tree[key]

    @beartype
    def close(self):
        self.tree.close()


# Example usage
if __name__ == "__main__":
    store = BTreeStore(Path("btree.db"))
    store.insert(1, b"Hello")
    print(store.get(1))  # Output: b'Hello'
    store.close()
