"""German QWERTZ layout (ISO).

QWERTZ swaps the Y and Z keys relative to QWERTY (so the top row reads
``qwertz``) and adds the umlauts ``ü ö ä`` and ``ß`` plus the ``<`` key left of
Y. The digit row matches QWERTY. Letter positions follow the ANSI grid, so
finger assignment is taken from the physical position.
"""

from __future__ import annotations

from types import MappingProxyType

from keywalk_audit.layouts.base import Layout
from keywalk_audit.layouts.qwerty_us import ROW_STAGGER, fingers_for_positions

_CHAR_TO_POS: dict[str, tuple[int, int]] = {
    # Row 0: number row.
    "^": (0, 0),
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
    "ß": (0, 11),
    "´": (0, 12),
    # Row 1: q w e r t z u i o p ü +
    "q": (1, 1),
    "w": (1, 2),
    "e": (1, 3),
    "r": (1, 4),
    "t": (1, 5),
    "z": (1, 6),
    "u": (1, 7),
    "i": (1, 8),
    "o": (1, 9),
    "p": (1, 10),
    "ü": (1, 11),
    "+": (1, 12),
    # Row 2: a s d f g h j k l ö ä #
    "a": (2, 1),
    "s": (2, 2),
    "d": (2, 3),
    "f": (2, 4),
    "g": (2, 5),
    "h": (2, 6),
    "j": (2, 7),
    "k": (2, 8),
    "l": (2, 9),
    "ö": (2, 10),
    "ä": (2, 11),
    "#": (2, 12),
    # Row 3: < y x c v b n m , . -
    "<": (3, 0),
    "y": (3, 1),
    "x": (3, 2),
    "c": (3, 3),
    "v": (3, 4),
    "b": (3, 5),
    "n": (3, 6),
    "m": (3, 7),
    ",": (3, 8),
    ".": (3, 9),
    "-": (3, 10),
}


def _build_shift_map() -> dict[str, str]:
    sym_pairs = {
        "^": "°",
        "1": "!",
        "2": '"',
        "3": "§",
        "4": "$",
        "5": "%",
        "6": "&",
        "7": "/",
        "8": "(",
        "9": ")",
        "0": "=",
        "ß": "?",
        "´": "`",
        "ü": "Ü",
        "+": "*",
        "ö": "Ö",
        "ä": "Ä",
        "#": "'",
        "<": ">",
        ",": ";",
        ".": ":",
        "-": "_",
    }
    letter_pairs = {chr(ord("a") + i): chr(ord("A") + i) for i in range(26)}
    return {**sym_pairs, **letter_pairs}


QWERTZ_DE: Layout = Layout(
    name="qwertz_de",
    char_to_pos=MappingProxyType(_CHAR_TO_POS),
    shift_map=MappingProxyType(_build_shift_map()),
    row_offsets=MappingProxyType(dict(ROW_STAGGER)),
    finger_map=MappingProxyType(fingers_for_positions(_CHAR_TO_POS)),
)
