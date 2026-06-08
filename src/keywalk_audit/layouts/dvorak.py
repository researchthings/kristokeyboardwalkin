"""Dvorak Simplified Keyboard (US) layout.

Dvorak relocates the letters onto the same ANSI physical key positions used
by QWERTY, so the grid coordinates and row stagger are identical; only which
glyph sits on each key changes. Finger assignment therefore follows the
physical position via ``fingers_for_positions``.
"""

from __future__ import annotations

from types import MappingProxyType

from keywalk_audit.layouts.base import Layout
from keywalk_audit.layouts.qwerty_us import ROW_STAGGER, fingers_for_positions

_CHAR_TO_POS: dict[str, tuple[int, int]] = {
    # Row 0: number row (unchanged from QWERTY).
    "`": (0, 0),
    "1": (0, 1),
    "2": (0, 2),
    "3": (0, 3),
    "4": (0, 4),
    "5": (0, 5),
    "6": (0, 6),
    "7": (0, 7),
    "8": (0, 8),
    "9": (0, 9),
    "0": (0, 10),
    "[": (0, 11),
    "]": (0, 12),
    # Row 1: ' , . p y f g c r l / =
    "'": (1, 1),
    ",": (1, 2),
    ".": (1, 3),
    "p": (1, 4),
    "y": (1, 5),
    "f": (1, 6),
    "g": (1, 7),
    "c": (1, 8),
    "r": (1, 9),
    "l": (1, 10),
    "/": (1, 11),
    "=": (1, 12),
    "\\": (1, 13),
    # Row 2: a o e u i d h t n s -
    "a": (2, 1),
    "o": (2, 2),
    "e": (2, 3),
    "u": (2, 4),
    "i": (2, 5),
    "d": (2, 6),
    "h": (2, 7),
    "t": (2, 8),
    "n": (2, 9),
    "s": (2, 10),
    "-": (2, 11),
    # Row 3: ; q j k x b m w v z
    ";": (3, 1),
    "q": (3, 2),
    "j": (3, 3),
    "k": (3, 4),
    "x": (3, 5),
    "b": (3, 6),
    "m": (3, 7),
    "w": (3, 8),
    "v": (3, 9),
    "z": (3, 10),
}


def _build_shift_map() -> dict[str, str]:
    sym_pairs = {
        "`": "~",
        "1": "!",
        "2": "@",
        "3": "#",
        "4": "$",
        "5": "%",
        "6": "^",
        "7": "&",
        "8": "*",
        "9": "(",
        "0": ")",
        "[": "{",
        "]": "}",
        "'": '"',
        ",": "<",
        ".": ">",
        "/": "?",
        "=": "+",
        "\\": "|",
        "-": "_",
        ";": ":",
    }
    letter_pairs = {chr(ord("a") + i): chr(ord("A") + i) for i in range(26)}
    return {**sym_pairs, **letter_pairs}


DVORAK: Layout = Layout(
    name="dvorak",
    char_to_pos=MappingProxyType(_CHAR_TO_POS),
    shift_map=MappingProxyType(_build_shift_map()),
    row_offsets=MappingProxyType(dict(ROW_STAGGER)),
    finger_map=MappingProxyType(fingers_for_positions(_CHAR_TO_POS)),
)
