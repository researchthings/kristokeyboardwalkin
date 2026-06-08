"""Keyboard layouts: physical-key grids, shift maps, and adjacency math."""

from __future__ import annotations

from keywalk_audit.layouts.azerty_fr import AZERTY_FR
from keywalk_audit.layouts.base import Layout
from keywalk_audit.layouts.colemak import COLEMAK
from keywalk_audit.layouts.dvorak import DVORAK
from keywalk_audit.layouts.numpad import NUMPAD
from keywalk_audit.layouts.phone_keypad import PHONE_KEYPAD
from keywalk_audit.layouts.qwerty_intl import QWERTY_INTL
from keywalk_audit.layouts.qwerty_uk import QWERTY_UK
from keywalk_audit.layouts.qwerty_us import QWERTY_US
from keywalk_audit.layouts.qwertz_de import QWERTZ_DE

LAYOUTS: dict[str, Layout] = {
    QWERTY_US.name: QWERTY_US,
    QWERTY_UK.name: QWERTY_UK,
    QWERTY_INTL.name: QWERTY_INTL,
    QWERTZ_DE.name: QWERTZ_DE,
    AZERTY_FR.name: AZERTY_FR,
    DVORAK.name: DVORAK,
    COLEMAK.name: COLEMAK,
    NUMPAD.name: NUMPAD,
    PHONE_KEYPAD.name: PHONE_KEYPAD,
}


def get_layout(name: str) -> Layout:
    """Return the Layout registered under `name`. Raises KeyError if missing."""
    try:
        return LAYOUTS[name]
    except KeyError as exc:
        known = ", ".join(sorted(LAYOUTS))
        raise KeyError(f"unknown layout {name!r}. Known layouts: {known}") from exc


__all__ = [
    "AZERTY_FR",
    "COLEMAK",
    "DVORAK",
    "LAYOUTS",
    "NUMPAD",
    "PHONE_KEYPAD",
    "QWERTY_INTL",
    "QWERTY_UK",
    "QWERTY_US",
    "QWERTZ_DE",
    "Layout",
    "get_layout",
]
