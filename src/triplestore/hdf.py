import uuid

import h5py
import numpy as np


class RelationStore:
    def __init__(self, file_path):
        self.file_path = file_path

    def _uuid_to_ints(self, u):
        u_int = int(u)
        return (u_int >> 64, u_int & ((1 << 64) - 1))

    def _ints_to_uuid(self, high, low):
        high = int(high)
        low = int(low)
        return uuid.UUID(int=(high << 64) | low)

    def store_tuples(self, tuples):
        with h5py.File(self.file_path, "w") as f:
            data = np.array(
                [
                    [
                        *self._uuid_to_ints(u1),
                        *self._uuid_to_ints(u2),
                        *self._uuid_to_ints(u3),
                    ]
                    for u1, u2, u3 in tuples
                ],
                dtype="uint64",
            )
            f.create_dataset("uuids", data=data, compression="gzip")

    def retrieve_tuples(self):
        with h5py.File(self.file_path, "r") as f:
            data = f["uuids"][:]
            return [
                (
                    self._ints_to_uuid(u1_high, u1_low),
                    self._ints_to_uuid(u2_high, u2_low),
                    self._ints_to_uuid(u3_high, u3_low),
                )
                for u1_high, u1_low, u2_high, u2_low, u3_high, u3_low in data
            ]

    def retrieve_by_first_uuid(self, first_uuid):
        first_uuid_high, first_uuid_low = self._uuid_to_ints(first_uuid)
        with h5py.File(self.file_path, "r") as f:
            dataset = f["uuids"]
            filtered_data = [
                dataset[i]
                for i in range(len(dataset))
                if dataset[i, 0] == first_uuid_high and dataset[i, 1] == first_uuid_low
            ]
            return [
                (
                    self._ints_to_uuid(u1_high, u1_low),
                    self._ints_to_uuid(u2_high, u2_low),
                    self._ints_to_uuid(u3_high, u3_low),
                )
                for u1_high, u1_low, u2_high, u2_low, u3_high, u3_low in filtered_data
            ]


# Example usage
if __name__ == "__main__":
    store = RelationStore("uuids.h5")
    tuples = [(uuid.uuid4(), uuid.uuid4(), uuid.uuid4()) for _ in range(10)]
    store.store_tuples(tuples)
    first_uuid = tuples[0][0]
    retrieved_tuples = store.retrieve_by_first_uuid(first_uuid)
    print(retrieved_tuples)
