import random
import statistics

import numpy as np
from tqdm import tqdm


class E(int):
    """A simple wrapper for a 128-bit key."""

    def __new__(cls, value):
        return int.__new__(cls, value)

    @property
    def high(self):
        return self >> 64

    @property
    def low(self):
        return self & ((1 << 64) - 1)


PERTURB_1 = 13287301680950405831  # Random Prime
PERTURB_2 = 17772150785748878159 * 2 + 1  # Germain Prime b2
PERTURB_3 = 17772150785748878159  # Germain Prime b1
MASK = (1 << 64) - 1  # 0xfffff... to stay within the size limit
MASK_EVEN = 0xAAAAAAAAAAAAAAAA  # even bits set (0b101010...)
MASK_ODD = 0x5555555555555555  # odd bits set  (0b010101...)
KNUTH_CONSTANT = 0x9E3779B97F4A7C15  # Well-known constant for mixing (also related to the golden ratio)

CONSTANT1 = 0x19E3779B97F4A7C15  # Well-known constant for mixing related to the golden ratio, Knuth's constant
CONSTANT2 = 0xF39CC0605CEDC834  # second part of Knuth's constant
CONSTANT3 = 0x1082276BF3A27251  # third part of Knuth's constant

FIX_R = 33


def mix(x):
    x ^= x >> FIX_R
    x *= PERTURB_1
    x &= MASK
    x ^= x >> FIX_R
    x *= PERTURB_2
    x &= MASK
    x ^= x >> FIX_R
    x ^= PERTURB_3
    x &= MASK
    return x


def rot(x: int, n: int) -> int:
    """Performs a 64-bit circular rotation of x by n bits."""
    return ((x << n) | (x >> (64 - n))) & MASK


def create_composite_key(a: E, b: E, r: int) -> E:
    Ha = mix(a.high)
    Hb = mix(b.high)
    La = mix(a.low)
    Lb = mix(b.low)

    combined_high = (Ha * CONSTANT1 + Hb * CONSTANT2) & MASK
    combined_low = (La * CONSTANT1 + Lb * CONSTANT2) & MASK

    rotated_high = rot(combined_high, r) ^ (combined_low & MASK_EVEN)
    rotated_low = rot(combined_low, r) ^ (combined_high & MASK_ODD)

    final_high = mix(rotated_high)
    final_low = mix(rotated_low)

    composite_value = (final_high << 64) | final_low
    return E(composite_value)


# ---------------------------------------
# Statistics
# ---------------------------------------
def hamming_distance(a: E, b: E) -> int:
    """
    Calculate the Hamming distance between two 128-bit integers.
    """
    return bin(a ^ b).count("1")


def hamming_test(a, b, r):
    composite_orig = create_composite_key(a, b, r)

    # Flip a random bit in the 128-bit value 'a'.
    bit_to_flip = random.randint(0, 127)
    a_flipped = E(a ^ (1 << bit_to_flip))

    composite_flipped = create_composite_key(a_flipped, b, r)

    return hamming_distance(composite_orig, composite_flipped)


def avalanche_composite_statistics(num_samples: int = 1000000, r=3):
    """
    For a given composite key creation function (create_key_fn), generate a number
    of random 128-bit key pairs (a, b) and measure the number of differing bits between
    composite_key(a, b) and composite_key(a_flipped, b), where a_flipped is the key "a"
    with one arbitrary bit flipped.

    Returns (mean, stddev) of the Hamming distances (over 128 bits).
    """
    distances = []
    for _ in tqdm(range(num_samples)):
        # Generate random 128-bit integers for a and b.
        a = random.getrandbits(128)
        b = random.getrandbits(128)
        distances.append(hamming_test(E(a), E(b), r))

    return (
        statistics.mean(distances),
        statistics.stdev(distances),
        min(distances),
        max(distances),
    )


def statistics_for(a, b, r, num_samples=10000):
    distances = []
    for _ in tqdm(range(num_samples)):
        distances.append(hamming_test(a, b, r))
    return (
        statistics.mean(distances),
        statistics.stdev(distances),
        min(distances),
        max(distances),
    )


import pytest


@pytest.fixture
def test_values():
    """Generate test values including edge cases"""
    return [
        (E((1 << 128) - 1), E((1 << 128) - 1)),  # All ones
        (E(0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA), E(0x55555555555555555555555555555555)),
        (E(12345), E(67890)),
        (E(0xDEADBEEF), E(0xCAFEBABE)),
        (E(1 << 64), E(1 << 32)),  # High bit vs low bit
    ]


def test_avalanche_effect():
    """Verify single-bit flips change ~50% of output bits"""

    distances = []

    for _ in tqdm(range(1000000), desc="Single Bit Test"):
        a = (1 << 128) - 1
        bit_to_flip = random.randint(0, 127)
        a_flipped = E(a ^ (1 << bit_to_flip))
        b = E(random.getrandbits(128))
        key_a = create_composite_key(E(a), b, 3)
        key_b = create_composite_key(a_flipped, b, 3)
        distances.append(hamming_distance(key_a, key_b))

    mean = np.mean(distances)
    std = np.std(distances)

    assert abs(mean - 64) < 1, f"Bad avalanche mean: {mean}"
    assert abs(std - 5.66) < 1, f"Unexpected stddev: {std}"
    assert min(distances) >= 35, "Weak diffusion detected"
    assert max(distances) <= 95, "Overmixing detected"


def test_order_sensitivity(test_values):
    """Verify key(a,b) != key(b,a) for different inputs"""
    for a, b in test_values:
        if a == b:
            continue
        key_ab = create_composite_key(a, b, 3)
        key_ba = create_composite_key(b, a, 3)
        assert key_ab != key_ba, f"Order insensitivity detected: {a} vs {b}"

        # Test with reversed rotation
        key_ab_r = create_composite_key(a, b, 11)
        key_ba_r = create_composite_key(b, a, 11)
        assert key_ab_r != key_ba_r, "Rotation order issue"


def test_collision_resistance():
    """Check collision rates across random inputs"""
    NUM_SAMPLES = 1_000_000
    hashes = set()

    for _ in tqdm(range(NUM_SAMPLES), desc="Collision Test"):
        a = E(random.getrandbits(128))
        b = E(random.getrandbits(128))
        key = create_composite_key(a, b, 3)
        assert key not in hashes, "Collision detected"
        hashes.add(key)


# --- Edge Case Tests ---


def test_zero_inputs():
    """Verify handling of all-zero inputs"""
    zero = E(0)
    key = create_composite_key(zero, zero, 3)
    assert key != zero, "Zero identity failure"

    # Different rotation should produce different zero
    key2 = create_composite_key(zero, zero, 7)
    assert key != key2, "Rotation doesn't affect zero keys"


# --- Consistency Tests ---


def test_determinism():
    """Same inputs should always produce same output"""
    a = E(0x123456789ABCDEF0)
    b = E(0xFEDCBA9876543210)

    key1 = create_composite_key(a, b, 5)
    key2 = create_composite_key(a, b, 5)
    assert key1 == key2

    # Different rotation should differ
    key3 = create_composite_key(a, b, 7)
    assert key1 != key3


def test_rotation_impact():
    """Different rotation values should produce different keys"""
    a = E(random.getrandbits(128))
    b = E(random.getrandbits(128))

    keys = {create_composite_key(a, b, r) for r in range(64)}
    assert len(keys) == 64, "Rotation values not impactful enough"


# --- Run Tests ---
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
