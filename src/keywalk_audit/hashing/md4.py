"""Pure-Python MD4 message-digest algorithm (RFC 1320).

OpenSSL 3 dropped MD4 from its default provider, which means ``hashlib.new('md4')``
raises ``ValueError`` on many modern systems. This module provides a dependency-free
implementation so the build-time hash computer can produce raw MD4 digests (e.g. for
NTLM NT-hash computation) regardless of the host OpenSSL configuration.

Public API
----------
- ``md4(data: bytes) -> bytes``  — 16-byte raw digest.
- ``md4_hex(data: bytes) -> str`` — lowercase hex digest.
"""

from __future__ import annotations

import struct

# ---------------------------------------------------------------------------
# RFC 1320 constants
# ---------------------------------------------------------------------------

# Initial hash values (§3.3 — stored as little-endian 32-bit words)
_A0: int = 0x67452301
_B0: int = 0xEFCDAB89
_C0: int = 0x98BADCFE
_D0: int = 0x10325476

# Additive constants for rounds 2 and 3 (§3.4)
_K2: int = 0x5A827999
_K3: int = 0x6ED9EBA1

# 32-bit mask — Python integers are arbitrary precision; we must truncate.
_MASK32: int = 0xFFFFFFFF


# ---------------------------------------------------------------------------
# Auxiliary bit functions (§3.4)
# Note: Python's ~ operator returns an arbitrary-precision negative integer
# so every NOT must be masked to 32 bits before combining with & or |.
# ---------------------------------------------------------------------------


def _f(x: int, y: int, z: int) -> int:
    return (x & y) | ((~x & _MASK32) & z)


def _g(x: int, y: int, z: int) -> int:
    return (x & y) | (x & z) | (y & z)


def _h(x: int, y: int, z: int) -> int:
    return x ^ y ^ z


def _rotl32(value: int, shift: int) -> int:
    """Rotate ``value`` left by ``shift`` bits within a 32-bit word.

    ``value`` is first truncated to 32 bits so that the right-shift does not
    inadvertently include carry bits from an un-masked intermediate sum.
    """
    value &= _MASK32
    return ((value << shift) | (value >> (32 - shift))) & _MASK32


# ---------------------------------------------------------------------------
# Padding (§3.1 of RFC 1320)
# ---------------------------------------------------------------------------


def _pad(data: bytes) -> bytes:
    """Return ``data`` after MD4 / MD5-family Merkle-Damgård padding.

    Appends a 0x80 byte, then zero bytes until the message length is
    congruent to 56 mod 64, then the 64-bit little-endian bit-length.
    """
    bit_len: int = len(data) * 8
    data += b"\x80"
    # Pad with zeros until len ≡ 56 (mod 64)
    while len(data) % 64 != 56:
        data += b"\x00"
    # Append original bit length as 64-bit little-endian
    data += struct.pack("<Q", bit_len)
    return data


# ---------------------------------------------------------------------------
# Per-round helpers (§3.4)
# Each helper performs one RFC 1320 round on (a, b, c, d) and returns the
# updated quadruple.  Splitting the 48-operation compression into three
# functions keeps each one under the statement-count linter threshold.
# ---------------------------------------------------------------------------


def _round1(a: int, b: int, c: int, d: int, x: list[int]) -> tuple[int, int, int, int]:
    """Round 1 of MD4 (§3.4, step 1) — F function, no additive constant."""
    # [ABCD  0  3]  [DABC  1  7]  [CDAB  2 11]  [BCDA  3 19]
    a = _rotl32(a + _f(b, c, d) + x[0], 3)
    d = _rotl32(d + _f(a, b, c) + x[1], 7)
    c = _rotl32(c + _f(d, a, b) + x[2], 11)
    b = _rotl32(b + _f(c, d, a) + x[3], 19)
    # [ABCD  4  3]  [DABC  5  7]  [CDAB  6 11]  [BCDA  7 19]
    a = _rotl32(a + _f(b, c, d) + x[4], 3)
    d = _rotl32(d + _f(a, b, c) + x[5], 7)
    c = _rotl32(c + _f(d, a, b) + x[6], 11)
    b = _rotl32(b + _f(c, d, a) + x[7], 19)
    # [ABCD  8  3]  [DABC  9  7]  [CDAB 10 11]  [BCDA 11 19]
    a = _rotl32(a + _f(b, c, d) + x[8], 3)
    d = _rotl32(d + _f(a, b, c) + x[9], 7)
    c = _rotl32(c + _f(d, a, b) + x[10], 11)
    b = _rotl32(b + _f(c, d, a) + x[11], 19)
    # [ABCD 12  3]  [DABC 13  7]  [CDAB 14 11]  [BCDA 15 19]
    a = _rotl32(a + _f(b, c, d) + x[12], 3)
    d = _rotl32(d + _f(a, b, c) + x[13], 7)
    c = _rotl32(c + _f(d, a, b) + x[14], 11)
    b = _rotl32(b + _f(c, d, a) + x[15], 19)
    return a, b, c, d


def _round2(a: int, b: int, c: int, d: int, x: list[int]) -> tuple[int, int, int, int]:
    """Round 2 of MD4 (§3.4, step 2) — G function, constant 0x5A827999."""
    # [ABCD  0  3]  [DABC  4  5]  [CDAB  8  9]  [BCDA 12 13]
    a = _rotl32(a + _g(b, c, d) + x[0] + _K2, 3)
    d = _rotl32(d + _g(a, b, c) + x[4] + _K2, 5)
    c = _rotl32(c + _g(d, a, b) + x[8] + _K2, 9)
    b = _rotl32(b + _g(c, d, a) + x[12] + _K2, 13)
    # [ABCD  1  3]  [DABC  5  5]  [CDAB  9  9]  [BCDA 13 13]
    a = _rotl32(a + _g(b, c, d) + x[1] + _K2, 3)
    d = _rotl32(d + _g(a, b, c) + x[5] + _K2, 5)
    c = _rotl32(c + _g(d, a, b) + x[9] + _K2, 9)
    b = _rotl32(b + _g(c, d, a) + x[13] + _K2, 13)
    # [ABCD  2  3]  [DABC  6  5]  [CDAB 10  9]  [BCDA 14 13]
    a = _rotl32(a + _g(b, c, d) + x[2] + _K2, 3)
    d = _rotl32(d + _g(a, b, c) + x[6] + _K2, 5)
    c = _rotl32(c + _g(d, a, b) + x[10] + _K2, 9)
    b = _rotl32(b + _g(c, d, a) + x[14] + _K2, 13)
    # [ABCD  3  3]  [DABC  7  5]  [CDAB 11  9]  [BCDA 15 13]
    a = _rotl32(a + _g(b, c, d) + x[3] + _K2, 3)
    d = _rotl32(d + _g(a, b, c) + x[7] + _K2, 5)
    c = _rotl32(c + _g(d, a, b) + x[11] + _K2, 9)
    b = _rotl32(b + _g(c, d, a) + x[15] + _K2, 13)
    return a, b, c, d


def _round3(a: int, b: int, c: int, d: int, x: list[int]) -> tuple[int, int, int, int]:
    """Round 3 of MD4 (§3.4, step 3) — H function, constant 0x6ED9EBA1."""
    # [ABCD  0  3]  [DABC  8  9]  [CDAB  4 11]  [BCDA 12 15]
    a = _rotl32(a + _h(b, c, d) + x[0] + _K3, 3)
    d = _rotl32(d + _h(a, b, c) + x[8] + _K3, 9)
    c = _rotl32(c + _h(d, a, b) + x[4] + _K3, 11)
    b = _rotl32(b + _h(c, d, a) + x[12] + _K3, 15)
    # [ABCD  2  3]  [DABC 10  9]  [CDAB  6 11]  [BCDA 14 15]
    a = _rotl32(a + _h(b, c, d) + x[2] + _K3, 3)
    d = _rotl32(d + _h(a, b, c) + x[10] + _K3, 9)
    c = _rotl32(c + _h(d, a, b) + x[6] + _K3, 11)
    b = _rotl32(b + _h(c, d, a) + x[14] + _K3, 15)
    # [ABCD  1  3]  [DABC  9  9]  [CDAB  5 11]  [BCDA 13 15]
    a = _rotl32(a + _h(b, c, d) + x[1] + _K3, 3)
    d = _rotl32(d + _h(a, b, c) + x[9] + _K3, 9)
    c = _rotl32(c + _h(d, a, b) + x[5] + _K3, 11)
    b = _rotl32(b + _h(c, d, a) + x[13] + _K3, 15)
    # [ABCD  3  3]  [DABC 11  9]  [CDAB  7 11]  [BCDA 15 15]
    a = _rotl32(a + _h(b, c, d) + x[3] + _K3, 3)
    d = _rotl32(d + _h(a, b, c) + x[11] + _K3, 9)
    c = _rotl32(c + _h(d, a, b) + x[7] + _K3, 11)
    b = _rotl32(b + _h(c, d, a) + x[15] + _K3, 15)
    return a, b, c, d


def _compress(a: int, b: int, c: int, d: int, block: bytes) -> tuple[int, int, int, int]:
    """Process one 64-byte block; return the updated (A, B, C, D) state."""
    aa: int = a
    bb: int = b
    cc: int = c
    dd: int = d
    x: list[int] = list(struct.unpack("<16I", block))
    a, b, c, d = _round1(a, b, c, d, x)
    a, b, c, d = _round2(a, b, c, d, x)
    a, b, c, d = _round3(a, b, c, d, x)
    return (aa + a) & _MASK32, (bb + b) & _MASK32, (cc + c) & _MASK32, (dd + d) & _MASK32


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def md4(data: bytes) -> bytes:
    """Return the 16-byte MD4 digest of ``data`` (RFC 1320)."""
    padded: bytes = _pad(data)
    a: int = _A0
    b: int = _B0
    c: int = _C0
    d: int = _D0
    for offset in range(0, len(padded), 64):
        a, b, c, d = _compress(a, b, c, d, padded[offset : offset + 64])
    return struct.pack("<4I", a, b, c, d)


def md4_hex(data: bytes) -> str:
    """Return the lowercase hex MD4 digest of ``data``."""
    return md4(data).hex()
