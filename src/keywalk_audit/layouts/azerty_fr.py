"""French AZERTY layout (ISO).

AZERTY differs from QWERTY most visibly in the top letter row (``azerty``
replaces ``qwerty``) and in the number row, where the digits are the *shifted*
glyphs: typing an unshifted top-row key yields ``& é " ' ( - è _ ç à``, and the
digits ``1``-``0`` require Shift. Modelling the digits in the shift map lets a
numeric walk like ``1234`` resolve to the same physical keys a French user
presses. Letter positions follow the ANSI grid, so finger assignment is taken
from the physical position.
"""

from __future__ import annotations

from types import MappingProxyType

from keywalk_audit.layouts.base import Layout
from keywalk_audit.layouts.qwerty_us import ROW_STAGGER, fingers_for_positions

_CHAR_TO_POS: dict[str, tuple[int, int]] = {
    # Row 0: number row. Unshifted glyphs are symbols; digits are shifted.
    "²": (0, 0),
    "&": (0, 1),
    "é": (0, 2),
    '"': (0, 3),
    "'": (0, 4),
    "(": (0, 5),
    "-": (0, 6),
    "è": (0, 7),
    "_": (0, 8),
    "ç": (0, 9),
    "à": (0, 10),
    ")": (0, 11),
    "=": (0, 12),
    # Row 1: a z e r t y u i o p ^ $
    "a": (1, 1),
    "z": (1, 2),
    "e": (1, 3),
    "r": (1, 4),
    "t": (1, 5),
    "y": (1, 6),
    "u": (1, 7),
    "i": (1, 8),
    "o": (1, 9),
    "p": (1, 10),
    "^": (1, 11),
    "$": (1, 12),
    # Row 2: q s d f g h j k l m ù *
    "q": (2, 1),
    "s": (2, 2),
    "d": (2, 3),
    "f": (2, 4),
    "g": (2, 5),
    "h": (2, 6),
    "j": (2, 7),
    "k": (2, 8),
    "l": (2, 9),
    "m": (2, 10),
    "ù": (2, 11),
    "*": (2, 12),
    # Row 3: < w x c v b n , ; : !
    "<": (3, 0),
    "w": (3, 1),
    "x": (3, 2),
    "c": (3, 3),
    "v": (3, 4),
    "b": (3, 5),
    "n": (3, 6),
    ",": (3, 7),
    ";": (3, 8),
    ":": (3, 9),
    "!": (3, 10),
}


def _build_shift_map() -> dict[str, str]:
    sym_pairs = {
        "&": "1",
        "é": "2",
        '"': "3",
        "'": "4",
        "(": "5",
        "-": "6",
        "è": "7",
        "_": "8",
        "ç": "9",
        "à": "0",
        ")": "°",
        "=": "+",
        "^": "¨",
        "$": "£",
        "ù": "%",
        "*": "µ",
        "<": ">",
        ",": "?",
        ";": ".",
        ":": "/",
        "!": "§",
    }
    letter_pairs = {chr(ord("a") + i): chr(ord("A") + i) for i in range(26)}
    return {**sym_pairs, **letter_pairs}


AZERTY_FR: Layout = Layout(
    name="azerty_fr",
    char_to_pos=MappingProxyType(_CHAR_TO_POS),
    shift_map=MappingProxyType(_build_shift_map()),
    row_offsets=MappingProxyType(dict(ROW_STAGGER)),
    finger_map=MappingProxyType(fingers_for_positions(_CHAR_TO_POS)),
)
