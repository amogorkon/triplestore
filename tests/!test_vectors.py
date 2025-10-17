from uuid import uuid4

from entry import UUID128, CompositeKey


def test_composite_key_uniqueness():
    # Test collision resistance
    seen = set()
    for _ in range(1_000_000):
        s = UUID128.from_uuid(uuid4())
        p = UUID128.from_uuid(uuid4())
        key = CompositeKey.create(s, p)
        assert key not in seen
        seen.add(key)


def test_order_sensitivity():
    s = UUID128.from_uuid(uuid4())
    p = UUID128.from_uuid(uuid4())
    assert CompositeKey.create(s, p) != CompositeKey.create(p, s)
