"""Layout dataclass: physical-key grid, shift map, and adjacency math.

The geometric model has two layers:

- A **logical integer grid** (``char_to_pos``) where keys in the same
  column align across rows. Adjacency, direction, fingerprinting, and the
  calibrated walk scorer all operate on this grid so that vertical walks
  (``1qaz``) and shift mirrors behave predictably. This layer is the
  stable contract the rest of the pipeline depends on.
- An optional **physical stagger model** (``row_offsets``) that shifts each
  row horizontally by a fractional key-unit, approximating the real
  row-staggered geometry of a physical keyboard. This layer feeds
  ``physical_pos`` / ``euclidean_distance`` and the richer walk analysis
  without disturbing the integer-grid contract.

Layouts may also carry an optional **finger map** assigning each physical
key to the touch-typing finger that presses it, which powers hand- and
finger-alternation analysis.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import cached_property
from types import MappingProxyType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

# Finger identifiers for the touch-typing assignment. ``THUMB`` covers the
# space bar; the eight remaining values are the home-position fingers.
LEFT_PINKY = "left_pinky"
LEFT_RING = "left_ring"
LEFT_MIDDLE = "left_middle"
LEFT_INDEX = "left_index"
RIGHT_INDEX = "right_index"
RIGHT_MIDDLE = "right_middle"
RIGHT_RING = "right_ring"
RIGHT_PINKY = "right_pinky"
THUMB = "thumb"

# Hand each finger belongs to. The thumb is its own "hand" so that a walk
# crossing into the space bar is not miscounted as a hand alternation.
FINGER_HAND: Mapping[str, str] = MappingProxyType(
    {
        LEFT_PINKY: "left",
        LEFT_RING: "left",
        LEFT_MIDDLE: "left",
        LEFT_INDEX: "left",
        RIGHT_INDEX: "right",
        RIGHT_MIDDLE: "right",
        RIGHT_RING: "right",
        RIGHT_PINKY: "right",
        THUMB: "thumb",
    }
)


@dataclass(frozen=True)
class Layout:
    """A physical keyboard layout.

    Each character maps to a (row, col) position on a logical grid where
    keys in the same column align across rows. For example, on QWERTY US
    the keys 1, q, a, z all share the same column so vertical walks score
    correctly.

    The shift map encodes the modifier relationship between unshifted and
    shifted glyphs (e.g., "1" -> "!"). Adjacency, direction, and the
    physical_key resolver all operate on physical positions, so a walk and
    its shift mirror trace the same path.

    ``row_offsets`` optionally shifts each row horizontally (in key units)
    to approximate physical row stagger; it affects ``physical_pos`` and
    ``euclidean_distance`` only. ``finger_map`` optionally assigns each
    physical key to a touch-typing finger (see the ``*_PINKY`` etc.
    constants).
    """

    name: str
    char_to_pos: Mapping[str, tuple[int, int]]
    shift_map: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))
    row_offsets: Mapping[int, float] = field(default_factory=lambda: MappingProxyType({}))
    finger_map: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))

    @cached_property
    def inverse_shift_map(self) -> Mapping[str, str]:
        """Map each shifted glyph back to its unshifted physical key."""
        return MappingProxyType({v: k for k, v in self.shift_map.items()})

    def physical_key(self, c: str) -> str:
        """Return the unshifted physical key that produces `c` on this layout.

        For a shifted glyph (e.g., "!" or "Q") the unshifted form is returned.
        For an unshifted glyph already on the grid, `c` is returned as-is.
        """
        if c in self.inverse_shift_map:
            return self.inverse_shift_map[c]
        return c

    def has_key(self, c: str) -> bool:
        """Return True if `c` resolves to a position on this layout."""
        return self.physical_key(c) in self.char_to_pos

    def position(self, c: str) -> tuple[int, int]:
        """Return the (row, col) of the physical key that produces `c`."""
        key = self.physical_key(c)
        try:
            return self.char_to_pos[key]
        except KeyError as exc:
            raise KeyError(f"character {c!r} (key {key!r}) not on layout {self.name!r}") from exc

    def physical_pos(self, c: str) -> tuple[float, float]:
        """Return the stagger-adjusted physical (row, col) of `c`.

        The column is shifted by ``row_offsets[row]`` when defined, modelling
        the horizontal stagger of a real keyboard. With no offsets configured
        this is the integer grid position cast to float.
        """
        row, col = self.position(c)
        return (float(row), col + self.row_offsets.get(row, 0.0))

    def euclidean_distance(self, a: str, b: str) -> float:
        """Return the physical (stagger-aware) Euclidean distance between keys."""
        row_a, col_a = self.physical_pos(a)
        row_b, col_b = self.physical_pos(b)
        return math.hypot(row_a - row_b, col_a - col_b)

    def is_adjacent(self, a: str, b: str) -> bool:
        """Return True when both chars resolve to physical keys with
        |Δrow| <= 1 and |Δcol| <= 1, and they are not the same key.
        """
        key_a = self.physical_key(a)
        key_b = self.physical_key(b)
        if key_a == key_b:
            return False
        if key_a not in self.char_to_pos or key_b not in self.char_to_pos:
            return False
        row_a, col_a = self.char_to_pos[key_a]
        row_b, col_b = self.char_to_pos[key_b]
        return abs(row_a - row_b) <= 1 and abs(col_a - col_b) <= 1

    def direction(self, a: str, b: str) -> tuple[int, int]:
        """Return the step vector (Δrow, Δcol) between physical keys."""
        row_a, col_a = self.position(a)
        row_b, col_b = self.position(b)
        return (row_b - row_a, col_b - col_a)

    def neighbors(self, c: str) -> list[str]:
        """Return all physical keys adjacent to `c` on this layout."""
        if not self.has_key(c):
            return []
        center_row, center_col = self.position(c)
        center_key = self.physical_key(c)
        result: list[str] = []
        for key, (row, col) in self.char_to_pos.items():
            if key == center_key:
                continue
            if abs(row - center_row) <= 1 and abs(col - center_col) <= 1:
                result.append(key)
        result.sort()
        return result

    def finger_of(self, c: str) -> str | None:
        """Return the touch-typing finger for `c`, or None when unmapped."""
        if not self.finger_map:
            return None
        return self.finger_map.get(self.physical_key(c))

    def hand_of(self, c: str) -> str | None:
        """Return "left"/"right"/"thumb" for `c`, or None when unmapped."""
        finger = self.finger_of(c)
        if finger is None:
            return None
        return FINGER_HAND.get(finger)
