"""Numeric keypad layout.

Three columns by four rows. The 0 key is centered under 1 and 2 to capture
common numpad walks like 1230 and 0258. The decimal point sits at column 2
of the bottom row.
"""

from __future__ import annotations

from types import MappingProxyType

from keywalk_audit.layouts.base import (
    RIGHT_INDEX,
    RIGHT_MIDDLE,
    RIGHT_RING,
    THUMB,
    Layout,
)

_CHAR_TO_POS: dict[str, tuple[int, int]] = {
    "7": (0, 0),
    "8": (0, 1),
    "9": (0, 2),
    "4": (1, 0),
    "5": (1, 1),
    "6": (1, 2),
    "1": (2, 0),
    "2": (2, 1),
    "3": (2, 2),
    "0": (3, 1),
    ".": (3, 2),
}

# The numeric keypad is operated by the right hand: index on the left column,
# middle on the centre column, ring on the right column, thumb on the zero.
_NUMPAD_FINGERS: dict[str, str] = {
    "7": RIGHT_INDEX,
    "4": RIGHT_INDEX,
    "1": RIGHT_INDEX,
    "8": RIGHT_MIDDLE,
    "5": RIGHT_MIDDLE,
    "2": RIGHT_MIDDLE,
    "9": RIGHT_RING,
    "6": RIGHT_RING,
    "3": RIGHT_RING,
    ".": RIGHT_RING,
    "0": THUMB,
}


NUMPAD: Layout = Layout(
    name="numpad",
    char_to_pos=MappingProxyType(_CHAR_TO_POS),
    shift_map=MappingProxyType({}),
    finger_map=MappingProxyType(_NUMPAD_FINGERS),
)
