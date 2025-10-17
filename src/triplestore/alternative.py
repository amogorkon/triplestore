# https://chat.deepseek.com/a/chat/s/01183b38-0fa0-4e91-80e6-cf01cb2f7898
# https://copilot.microsoft.com/chats/wcQMkoZUX5URVgq5AXNRB
# https://gemini.google.com/app/082899d1a367e856?hl=de


from dataclasses import dataclass
from functools import lru_cache
from typing import Any
from uuid import NAMESPACE_DNS

import numpy as np
import redis

# Redis connection pool (cluster-aware)
redis_pool = redis.ConnectionPool(max_connections=100)
r = redis.Redis(connection_pool=redis_pool, decode_responses=False)


@dataclass(frozen=True, eq=True, unsafe_hash=True)
class CompactUUID:
    """Memory-optimized interned UUID representation"""

    __slots__ = ("bytes",)
    bytes: bytes

    def __new__(cls, data: bytes):
        return uuid_cache.setdefault(data, super().__new__(cls))


uuid_cache = {}


class TriplestoreUUID:
    """Flyweight pattern for triplestore-optimized UUID handling"""

    _hdf5_dtype = np.dtype("V16")  # 16-byte void type

    def __init__(self, btree_path: str):
        self.btree = self._mmap_btree(btree_path)
        self._redis = redis.Redis(connection_pool=redis_pool)

    @staticmethod
    def _mmap_btree(path: str) -> np.memmap:
        """Memory-map HDF5 B+ tree structure"""
        return np.memmap(path, dtype="V16", mode="r+")

    @lru_cache(maxsize=10_000_000)
    def from_str(self, value: str) -> CompactUUID:
        """Batch-optimized UUID5 creation with Redis metadata"""
        # Generate UUID bytes without intermediate objects
        namespace = NAMESPACE_DNS.bytes
        hash_bytes = sha1(namespace + value.encode()).digest()
        uuid_bytes = hash_bytes[:16]
        uuid_bytes = (
            uuid_bytes[:6] + bytes([uuid_bytes[6] & 0x0F | 0x50]) + uuid_bytes[7:]
        )

        # Redis pipeline for batch metadata
        p = self._redis.pipeline()
        p.hget("uuid:meta", uuid_bytes)
        p.hsetnx("uuid:meta", uuid_bytes, msgpack.dumps(value))
        _, stored = p.execute()

        return CompactUUID(uuid_bytes)

    def bulk_load(self, data: np.ndarray) -> None:
        """Direct memory mapping for HDF5 bulk inserts"""
        # Zero-copy HDF5 to B+ tree insertion
        self.btree.resize((self.btree.shape[0] + data.shape[0],))
        self.btree[-data.shape[0] :] = data

    def bulk_dump(self, chunk_size: int = 10_000) -> np.ndarray:
        """Memory-mapped batch extraction"""
        return np.lib.stride_tricks.sliding_window_view(
            self.btree, window_shape=(chunk_size,)
        )

    def resolve_batch(self, uuids: list[CompactUUID]) -> dict[CompactUUID, Any]:
        """Parallel Redis metadata resolution"""
        with self._redis.pipeline(transaction=False) as p:
            for u in uuids:
                p.hget("uuid:meta", u.bytes)
            return {
                u: msgpack.loads(res)
                for u, res in zip(uuids, p.execute())
                if res is not None
            }
