"""Layout dataclass: physical-key grid, shift map, and adjacency math."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from types import MappingProxyType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping


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
    """

    name: str
    char_to_pos: Mapping[str, tuple[int, int]]
    shift_map: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))

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
