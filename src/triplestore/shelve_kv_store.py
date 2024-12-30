import shelve
import uuid


class ShelveKeyValueStore(dict):
    def __init__(self, file_path):
        self.file_path = file_path
        self._load_store()

    def _load_store(self):
        with shelve.open(self.file_path) as store:
            for key in store:
                super().__setitem__(key, store[key])

    def _save_store(self):
        with shelve.open(self.file_path, "c") as store:
            for key, value in self.items():
                store[key] = value

    def __setitem__(self, key, value):
        key_str = str(key)
        super().__setitem__(key_str, value)
        self._save_store()

    def __getitem__(self, key):
        key_str = str(key)
        return super().__getitem__(key_str)

    def __delitem__(self, key):
        key_str = str(key)
        super().__delitem__(key_str)
        with shelve.open(self.file_path, "c") as store:
            del store[key_str]

    def __contains__(self, key):
        key_str = str(key)
        return super().__contains__(key_str)

    def get(self, key, default=None):
        key_str = str(key)
        return super().get(key_str, default)

    def setdefault(self, key, default=None):
        key_str = str(key)
        return super().setdefault(key_str, default)

    def update(self, *args, **kwargs):
        super().update(*args, **kwargs)
        self._save_store()


# Example usage
if __name__ == "__main__":
    store = ShelveKeyValueStore("kv_store.db")
    namespace = uuid.uuid5(uuid.NAMESPACE_DNS, "test")
    key = uuid.uuid5(namespace, "example_key")
    value = {"name": "example", "value": 42}
    store[key] = value
    retrieved_value = store[key]
    print(retrieved_value)
