"""Geometric fingerprint for walks based on physical-key direction vectors.

The fingerprint is BLAKE2b-128 over a byte sequence in which each step is
encoded with a fixed 9-symbol alphabet over the unit-clipped direction
vector (the 8 cardinal/diagonal directions plus the zero vector).

Two walks that trace the same physical-key path produce identical
fingerprints. In particular, a walk and its shift mirror share a
fingerprint because shift mirroring preserves the physical-key sequence.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from keywalk_audit.layouts.base import Layout

_DIGEST_SIZE = 16

# Fixed encoding of (sign(row_delta), sign(col_delta)) tuples as bytes.
# The three values for each axis (-1, 0, 1) shift to (0, 1, 2), giving a
# zero-based 3x3 indexing. This is stable across runs and platforms.
_DIRECTION_BYTES: dict[tuple[int, int], int] = {
    (dr, dc): (dr + 1) * 3 + (dc + 1) for dr in (-1, 0, 1) for dc in (-1, 0, 1)
}


def _sign(value: int) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def geometric_fingerprint(plaintext: str, layout: Layout) -> str:
    """Return the hex BLAKE2b-128 fingerprint of the walk's physical path."""
    keys = [layout.physical_key(c) for c in plaintext]
    payload = bytearray()
    payload.extend(layout.name.encode("ascii"))
    payload.append(0)
    for i in range(len(keys) - 1):
        a, b = keys[i], keys[i + 1]
        if a not in layout.char_to_pos or b not in layout.char_to_pos:
            payload.append(255)
            continue
        delta_row = layout.char_to_pos[b][0] - layout.char_to_pos[a][0]
        delta_col = layout.char_to_pos[b][1] - layout.char_to_pos[a][1]
        clipped = (_sign(delta_row), _sign(delta_col))
        payload.append(_DIRECTION_BYTES[clipped])
    return hashlib.blake2b(bytes(payload), digest_size=_DIGEST_SIZE).hexdigest()
