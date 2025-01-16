from cassandra.cluster import Cluster
import uuid
import json


class CassandraKeyValueStore:
    def __init__(self, keyspace="kv_store", table="kv", contact_points=None):
        if contact_points is None:
            contact_points = ["127.0.0.1"]
        self.cluster = Cluster(contact_points)
        self.session = self.cluster.connect()
        self.keyspace = keyspace
        self.table = table
        self._initialize_db()

    def _initialize_db(self):
        self.session.execute(f"""
            CREATE KEYSPACE IF NOT EXISTS {self.keyspace}
            WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': '1'}}
        """)
        self.session.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.keyspace}.{self.table} (
                key UUID PRIMARY KEY,
                value TEXT
            )
        """)

    def _serialize(self, value):
        return json.dumps(value)

    def _deserialize(self, value):
        return json.loads(value)

    def set(self, key, value):
        value_str = self._serialize(value)
        self.session.execute(
            f"""
            INSERT INTO {self.keyspace}.{self.table} (key, value)
            VALUES (%s, %s)
        """,
            (key, value_str),
        )

    def get(self, key):
        result = self.session.execute(
            f"""
            SELECT value FROM {self.keyspace}.{self.table}
            WHERE key = %s
        """,
            (key,),
        )
        row = result.one()
        if row is None:
            raise KeyError("Key not found")
        return self._deserialize(row.value)


# Example usage
if __name__ == "__main__":
    store = CassandraKeyValueStore()
    namespace = uuid.uuid5(uuid.NAMESPACE_DNS, "test")
    key = uuid.uuid5(namespace, "example_key")
    value = {"name": "example", "value": 42}
    store.set(key, value)
    retrieved_value = store.get(key)
    print(retrieved_value)
