"""Keyboard layouts: physical-key grids, shift maps, and adjacency math."""

from __future__ import annotations

from keywalk_audit.layouts.base import Layout
from keywalk_audit.layouts.numpad import NUMPAD
from keywalk_audit.layouts.qwerty_intl import QWERTY_INTL
from keywalk_audit.layouts.qwerty_uk import QWERTY_UK
from keywalk_audit.layouts.qwerty_us import QWERTY_US

LAYOUTS: dict[str, Layout] = {
    QWERTY_US.name: QWERTY_US,
    QWERTY_UK.name: QWERTY_UK,
    QWERTY_INTL.name: QWERTY_INTL,
    NUMPAD.name: NUMPAD,
}


def get_layout(name: str) -> Layout:
    """Return the Layout registered under `name`. Raises KeyError if missing."""
    try:
        return LAYOUTS[name]
    except KeyError as exc:
        known = ", ".join(sorted(LAYOUTS))
        raise KeyError(f"unknown layout {name!r}. Known layouts: {known}") from exc


__all__ = [
    "LAYOUTS",
    "NUMPAD",
    "QWERTY_INTL",
    "QWERTY_UK",
    "QWERTY_US",
    "Layout",
    "get_layout",
]
