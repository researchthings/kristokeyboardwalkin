"""Telephone keypad layout (ITU E.161 / ISO 9995-8).

The phone keypad is the vertical inverse of the computer numeric keypad: the
1-2-3 row is on top and 0 sits at the bottom, between * and #. This distinction
matters for PIN-walk detection, because a "top-row" walk like 123 traces a
different physical path on a phone than on a numpad. The keypad is typically
thumb-typed, so no finger map is assigned.
"""

from __future__ import annotations

from types import MappingProxyType

from keywalk_audit.layouts.base import Layout

_CHAR_TO_POS: dict[str, tuple[int, int]] = {
    "1": (0, 0),
    "2": (0, 1),
    "3": (0, 2),
    "4": (1, 0),
    "5": (1, 1),
    "6": (1, 2),
    "7": (2, 0),
    "8": (2, 1),
    "9": (2, 2),
    "*": (3, 0),
    "0": (3, 1),
    "#": (3, 2),
}


PHONE_KEYPAD: Layout = Layout(
    name="phone_keypad",
    char_to_pos=MappingProxyType(_CHAR_TO_POS),
    shift_map=MappingProxyType({}),
)
