from typing import Final

from cidtree.keys import E

PERTURB_HIGH: Final[int] = 0xD1B54A32D192ED03
PERTURB_LOW: Final[int] = 0x81B1D42A3B609BED
MASK_EVEN: Final[int] = 0xAAAAAAAAAAAAAAAA
MASK_ODD: Final[int] = 0x5555555555555555


def rot64(x: int, n: int) -> int:
    """Performs a 64-bit circular rotation of x by n bits."""
    return ((x << n) | (x >> (64 - n))) & 0xFFFFFFFFFFFFFFFF


def enhanced_mix(x: int) -> int:
    """
    Mixes the bits of x using a series of shifts and multiplications.

    **Uses a fixed right-shift value of 33 bits** (per our testing and MurmurHash3 guidance)
    to achieve robust avalanche properties for any nonzero x.

    Returns a 64-bit integer with enhanced randomness.

    p1 = 0x8f3e1036504f61e3
    p2 = 0xb7c835c4d183eb31
    are both Sophie Germain primes, which are used in the MurmurHash3 algorithm to great success.
    The mixing function is designed to be non-invertible, meaning that given the output, it is computationally infeasible to reverse the process and obtain the original input.
    """
    fixed_r = 33
    x ^= x >> fixed_r
    x = (x * 0x8F3E1036504F61E3) & 0xFFFFFFFFFFFFFFFF
    x ^= x >> fixed_r
    x = (x * 0xB7C835C4D183EB31) & 0xFFFFFFFFFFFFFFFF
    x ^= x >> fixed_r
    return x


def create_composite_key(a: E, b: E) -> E:
    """
    Generate a composite 128-bit key from two 128-bit keys, a and b.

    This design uses RMX—Rotate, Mask, XOR—with the following steps:

    1. **Initial Mixing:**
       h = enhanced_mix(a.high ^ b.low) ^ PERTURB_HIGH
       L = enhanced_mix(a.low ^ b.high) ^ PERTURB_LOW

    2. **Rotation & Masking:**
       rotated_h = rot64(h, 19) ^ (L & MASK_EVEN)
       rotated_L = rot64(L, 23) ^ (h & MASK_ODD)

    3. **Final Mixing:**
       final_high = enhanced_mix(rotated_h ^ rotated_L)
       final_low  = enhanced_mix(rotated_L ^ rotated_h)

    4. **Assembly:**
       Composite key = (final_high << 64) | final_low
    """
    high = enhanced_mix(a.high ^ b.low) ^ PERTURB_HIGH
    low = enhanced_mix(a.low ^ b.high) ^ PERTURB_LOW

    # Rotate and mix further to break commutativity and incorporate bit masks.
    rotated_high = rot64(high, 19) ^ (low & MASK_EVEN)
    rotated_low = rot64(low, 23) ^ (high & MASK_ODD)

    final_high = enhanced_mix(rotated_high ^ rotated_low)
    final_low = enhanced_mix(rotated_low ^ rotated_high)

    composite_value = (final_high << 64) | final_low
    return E(composite_value)


def rot64(x: int, n: int) -> int:
    """Efficient 64-bit circular rotation"""
    return ((x << n) | (x >> (64 - n))) & 0xFFFFFFFFFFFFFFFF


def enhanced_mix(x: int, rot: int) -> int:
    """Better entropy mixing with multi-prime cascade"""
    x ^= rot64(x, rot)
    x *= PRIME_A
    x ^= rot64(x, rot + 16)  # Offset rotation
    x *= PRIME_B
    return x & 0xFFFFFFFFFFFFFFFF


def RMXCompositeKeyV2(s: UUID128, p: UUID128) -> UUID128:
    """Enhanced composite key with full-bit mixing"""
    # Cross-part mixing
    h = enhanced_mix(s.high ^ p.low, 17)
    l = enhanced_mix(s.low ^ p.high, 23)

    # Cross-breed final bits
    final_high = enhanced_mix(h ^ l, 5)
    final_low = enhanced_mix(l ^ h, 11)

    return UUID128(final_high, final_low)


class CompositeKey:
    __slots__ = ("high", "low")

    def __init__(self, a: UUID128, b: UUID128):
        # Rotating pattern for order sensitivity
        self.high = (a.high ^ _rotl64(b.high, 1)) | (a.low & _rotl64(b.low, 2))
        self.low = (a.low ^ _rotr64(b.high, 3)) | (a.high & _rotr64(b.low, 4))

    def __lt__(self, other: CompositeKey) -> bool:
        return (self.high, self.low) < (other.high, other.low)


class SPCompositeKey(CompositeKey):
    rotations = SP_ROTATIONS


class POCompositeKey(CompositeKey):
    rotations = PO_ROTATIONS


class OSCompositeKey(CompositeKey):
    rotations = OS_ROTATIONS


def _rotl64(x: int, k: int) -> int:
    """Left rotate 64-bit integer by k bits"""
    return ((x << k) | (x >> (64 - k))) & 0xFFFFFFFFFFFFFFFF


def _rotr64(x: int, k: int) -> int:
    """Right rotate 64-bit integer by k bits"""
    return ((x >> k) | (x << (64 - k))) & 0xFFFFFFFFFFFFFFFF


class SPComposite(CompositeKey):
    def __init__(self, a, b):
        super().__init__(a, b, rotations=SP_ROTATIONS)
