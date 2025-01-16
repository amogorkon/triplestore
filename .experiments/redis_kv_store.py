import json
import uuid

import redis


class RedisKeyValueStore:
    def __init__(self, host="localhost", port=6379, db=0):
        self.client = redis.StrictRedis(
            host=host, port=port, db=db, decode_responses=True
        )

    def _uuid_to_str(self, u):
        return str(u)

    def _serialize(self, value):
        return json.dumps(value)

    def _deserialize(self, value):
        return json.loads(value)

    def set(self, key, value):
        key_str = self._uuid_to_str(key)
        value_str = self._serialize(value)
        self.client.set(key_str, value_str)

    def get(self, key):
        key_str = self._uuid_to_str(key)
        value_str = self.client.get(key_str)
        if value_str is None:
            raise KeyError("Key not found")
        return self._deserialize(value_str)


# Example usage
if __name__ == "__main__":
    store = RedisKeyValueStore()
    namespace = uuid.uuid5(uuid.NAMESPACE_DNS, "test")
    key = uuid.uuid5(namespace, "example_key")
    value = {"name": "example", "value": 42}
    store.set(key, value)
    retrieved_value = store.get(key)
    print(retrieved_value)
