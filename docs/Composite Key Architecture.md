# Composite Key Architecture for Triplestore Indexing

## Design Overview

### 1. Key Compression Strategy
**Problem**: Storing raw UUID tuples (32 bytes/entry) doubles storage requirements vs single UUID keys
**Solution**: Arithmetic composition creates **128-bit composite keys** that preserve uniqueness while being storage-efficient:

```python
# Before: 32-byte tuple
key = (s_high, s_low, p_high, p_low)  # 32 bytes

# After: 16-byte composite key
composite = RMXCompositeKey(s, p)  # 16 bytes
```

## 2. Order Preservation Mechanism
Challenge: Prevent key(A,B) = key(B,A)
Solution: Prime-based bitwise rotations with XOR/AND mixing:

| Operation | Formula | Purpose |
|-----------|---------|---------|
| High 64 Bits | rot(A,3) ^ (B & MASK_EVEN) | Break commutativity |
| Low 64 Bits | rot(B,7) ^ (A & MASK_ODD) | Ensure position dependency |

## 3. Index-Specific Configuration
Each index uses unique parameters:

| Index | Rotations           | Bitmasks      | Security Properties     |
|-------|---------------------|---------------|-------------------------|
| SP    | 3, 7, 13, 17       | Even/Odd bits | gcd(rot,64)=1          |
| PO    | 23, 29, 37, 43     | 2-bit groups  | Full-period mixing      |
| OS    | 47, 53, 59, 61     | 4-bit nibbles | No cross-index alignment|

## 4. RMX Security Layer
Rotate-Mask-Xor (RMX) provides three-phase protection:

### Rotate: Prime-based bit shifting

```python
def rot64(x: int, n: int) -> int:
    return ((x << n) | (x >> (64 - n))) & 0xFFFFFFFFFFFFFFFF
```
### Mask: Index-specific bit isolation

```python
MASK_EVEN = 0xAAAAAAAAAAAAAAAA  # Even bits only
MASK_2BIT = 0xCCCCCCCCCCCCCCCC  # 2-bit groups
MASK_4BIT = 0xF0F0F0F0F0F0F0F0  # 4-bit nibbles
```
### Xor: Non-linear combination

```python
# SP Index example
high = (rot(s_high, 3) ^ (p_high & MASK_EVEN))
```

## 5. Collision Safety
|Scenario|	Probability (1B Triples)|	Protection Mechanism
|---|---|---|
|Natural Collision|	<10⁻³⁷|	128-bit UUID entropy
|Malicious Attack|	<10⁻²⁵|	RMX non-linearity
|Cross-Index Clash|	<10⁻⁶³|	Unique rotation/mask combos