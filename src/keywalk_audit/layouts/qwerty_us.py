"""QWERTY US keyboard layout."""

from __future__ import annotations

from types import MappingProxyType

from keywalk_audit.layouts.base import Layout

_CHAR_TO_POS: dict[str, tuple[int, int]] = {
    # Row 0: number row.
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
    # Row 1: top letter row plus right-of-P keys.
    "q": (1, 1),
    "w": (1, 2),
    "e": (1, 3),
    "r": (1, 4),
    "t": (1, 5),
    "y": (1, 6),
    "u": (1, 7),
    "i": (1, 8),
    "o": (1, 9),
    "p": (1, 10),
    "[": (1, 11),
    "]": (1, 12),
    "\\": (1, 13),
    # Row 2: home row plus right-of-L keys.
    "a": (2, 1),
    "s": (2, 2),
    "d": (2, 3),
    "f": (2, 4),
    "g": (2, 5),
    "h": (2, 6),
    "j": (2, 7),
    "k": (2, 8),
    "l": (2, 9),
    ";": (2, 10),
    "'": (2, 11),
    # Row 3: bottom letter row.
    "z": (3, 1),
    "x": (3, 2),
    "c": (3, 3),
    "v": (3, 4),
    "b": (3, 5),
    "n": (3, 6),
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


QWERTY_US: Layout = Layout(
    name="qwerty_us",
    char_to_pos=MappingProxyType(_CHAR_TO_POS),
    shift_map=MappingProxyType(_build_shift_map()),
)
