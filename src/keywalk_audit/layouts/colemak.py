"""Colemak (US) layout.

Colemak keeps the QWERTY number row and most punctuation and relocates the
letters onto the same ANSI key positions, so grid coordinates, row stagger,
and per-position finger assignment are inherited from QWERTY.
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
    "-": (0, 11),
    "=": (0, 12),
    # Row 1: q w f p g j l u y ;
    "q": (1, 1),
    "w": (1, 2),
    "f": (1, 3),
    "p": (1, 4),
    "g": (1, 5),
    "j": (1, 6),
    "l": (1, 7),
    "u": (1, 8),
    "y": (1, 9),
    ";": (1, 10),
    "[": (1, 11),
    "]": (1, 12),
    "\\": (1, 13),
    # Row 2: a r s t d h n e i o
    "a": (2, 1),
    "r": (2, 2),
    "s": (2, 3),
    "t": (2, 4),
    "d": (2, 5),
    "h": (2, 6),
    "n": (2, 7),
    "e": (2, 8),
    "i": (2, 9),
    "o": (2, 10),
    "'": (2, 11),
    # Row 3: z x c v b k m , . /
    "z": (3, 1),
    "x": (3, 2),
    "c": (3, 3),
    "v": (3, 4),
    "b": (3, 5),
    "k": (3, 6),
    "m": (3, 7),
    ",": (3, 8),
    ".": (3, 9),
    "/": (3, 10),
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
        "-": "_",
        "=": "+",
        "[": "{",
        "]": "}",
        "\\": "|",
        ";": ":",
        "'": '"',
        ",": "<",
        ".": ">",
        "/": "?",
    }
    letter_pairs = {chr(ord("a") + i): chr(ord("A") + i) for i in range(26)}
    return {**sym_pairs, **letter_pairs}


COLEMAK: Layout = Layout(
    name="colemak",
    char_to_pos=MappingProxyType(_CHAR_TO_POS),
    shift_map=MappingProxyType(_build_shift_map()),
    row_offsets=MappingProxyType(dict(ROW_STAGGER)),
    finger_map=MappingProxyType(fingers_for_positions(_CHAR_TO_POS)),
)
