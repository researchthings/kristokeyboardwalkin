"""QWERTY US keyboard layout."""

from __future__ import annotations

from types import MappingProxyType

from keywalk_audit.layouts.base import (
    LEFT_INDEX,
    LEFT_MIDDLE,
    LEFT_PINKY,
    LEFT_RING,
    RIGHT_INDEX,
    RIGHT_MIDDLE,
    RIGHT_PINKY,
    RIGHT_RING,
    Layout,
)

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


# Approximate ANSI row stagger as a horizontal column offset (in key units)
# applied per row. These feed the physical Euclidean-distance model only; the
# integer-grid adjacency and direction math are unaffected. The values place
# Q ~0.5u right of `1`, A ~0.25u right of Q, and Z ~0.5u right of A, matching
# the staggering of a physical ANSI board to within a small approximation.
ROW_STAGGER: dict[int, float] = {0: 0.0, 1: 0.5, 2: 0.75, 3: 1.25}

# Standard touch-typing finger assignment for the QWERTY family. Shared by the
# US, US-International, and (with two extra keys) UK layouts.
QWERTY_FINGERS: dict[str, str] = {
    # Row 0: number row.
    "`": LEFT_PINKY,
    "1": LEFT_PINKY,
    "2": LEFT_RING,
    "3": LEFT_MIDDLE,
    "4": LEFT_INDEX,
    "5": LEFT_INDEX,
    "6": RIGHT_INDEX,
    "7": RIGHT_INDEX,
    "8": RIGHT_MIDDLE,
    "9": RIGHT_RING,
    "0": RIGHT_PINKY,
    "-": RIGHT_PINKY,
    "=": RIGHT_PINKY,
    # Row 1: top letter row.
    "q": LEFT_PINKY,
    "w": LEFT_RING,
    "e": LEFT_MIDDLE,
    "r": LEFT_INDEX,
    "t": LEFT_INDEX,
    "y": RIGHT_INDEX,
    "u": RIGHT_INDEX,
    "i": RIGHT_MIDDLE,
    "o": RIGHT_RING,
    "p": RIGHT_PINKY,
    "[": RIGHT_PINKY,
    "]": RIGHT_PINKY,
    "\\": RIGHT_PINKY,
    # Row 2: home row.
    "a": LEFT_PINKY,
    "s": LEFT_RING,
    "d": LEFT_MIDDLE,
    "f": LEFT_INDEX,
    "g": LEFT_INDEX,
    "h": RIGHT_INDEX,
    "j": RIGHT_INDEX,
    "k": RIGHT_MIDDLE,
    "l": RIGHT_RING,
    ";": RIGHT_PINKY,
    "'": RIGHT_PINKY,
    # Row 3: bottom letter row.
    "z": LEFT_PINKY,
    "x": LEFT_RING,
    "c": LEFT_MIDDLE,
    "v": LEFT_INDEX,
    "b": LEFT_INDEX,
    "n": RIGHT_INDEX,
    "m": RIGHT_INDEX,
    ",": RIGHT_MIDDLE,
    ".": RIGHT_RING,
    "/": RIGHT_PINKY,
}


# Finger assignment keyed by physical grid position. Layouts that relocate the
# letters onto the same ANSI key positions (Dvorak, Colemak, QWERTZ, AZERTY)
# build their finger maps from this so a key keeps the finger of its position.
POS_FINGERS: dict[tuple[int, int], str] = {
    _CHAR_TO_POS[ch]: finger for ch, finger in QWERTY_FINGERS.items() if ch in _CHAR_TO_POS
}


def fingers_for_positions(char_to_pos: dict[str, tuple[int, int]]) -> dict[str, str]:
    """Build a char->finger map by looking each char's position up in POS_FINGERS.

    Characters whose position has no QWERTY finger assignment are omitted.
    """
    return {ch: POS_FINGERS[pos] for ch, pos in char_to_pos.items() if pos in POS_FINGERS}


QWERTY_US: Layout = Layout(
    name="qwerty_us",
    char_to_pos=MappingProxyType(_CHAR_TO_POS),
    shift_map=MappingProxyType(_build_shift_map()),
    row_offsets=MappingProxyType(dict(ROW_STAGGER)),
    finger_map=MappingProxyType(dict(QWERTY_FINGERS)),
)
