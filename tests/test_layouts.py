"""Tests for keyboard layouts and Layout.adjacency math."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from keywalk_audit.layouts import LAYOUTS, get_layout

if TYPE_CHECKING:
    from keywalk_audit.layouts.base import Layout


def test_qwerty_us_column_alignment(qwerty_us: Layout) -> None:
    """Keys 1, q, a, z share a column so vertical walks score correctly."""
    cols = {qwerty_us.position(c)[1] for c in ("1", "q", "a", "z")}
    assert len(cols) == 1


def test_qwerty_us_adjacency_basic(qwerty_us: Layout) -> None:
    assert qwerty_us.is_adjacent("1", "q")
    assert qwerty_us.is_adjacent("q", "a")
    assert qwerty_us.is_adjacent("a", "z")
    assert qwerty_us.is_adjacent("z", "x")
    assert qwerty_us.is_adjacent("x", "s")
    assert qwerty_us.is_adjacent("s", "w")
    assert qwerty_us.is_adjacent("w", "2")


def test_qwerty_us_adjacency_self_is_false(qwerty_us: Layout) -> None:
    assert not qwerty_us.is_adjacent("q", "q")


def test_qwerty_us_adjacency_through_shift(qwerty_us: Layout) -> None:
    """Shifted glyphs resolve to their physical key for adjacency."""
    assert qwerty_us.is_adjacent("!", "Q")
    assert qwerty_us.is_adjacent("Q", "A")
    assert qwerty_us.is_adjacent("Z", "X")


def test_qwerty_us_non_adjacent_jumps(qwerty_us: Layout) -> None:
    assert not qwerty_us.is_adjacent("z", "2")
    assert not qwerty_us.is_adjacent("1", "p")
    assert not qwerty_us.is_adjacent("q", "/")


def test_qwerty_us_direction(qwerty_us: Layout) -> None:
    assert qwerty_us.direction("1", "q") == (1, 0)
    assert qwerty_us.direction("q", "a") == (1, 0)
    assert qwerty_us.direction("z", "x") == (0, 1)
    assert qwerty_us.direction("x", "s") == (-1, 0)


def test_physical_key_for_shifted_glyphs(qwerty_us: Layout) -> None:
    assert qwerty_us.physical_key("!") == "1"
    assert qwerty_us.physical_key("Q") == "q"
    assert qwerty_us.physical_key("@") == "2"


def test_physical_key_passthrough(qwerty_us: Layout) -> None:
    assert qwerty_us.physical_key("1") == "1"
    assert qwerty_us.physical_key("q") == "q"


def test_qwerty_uk_at_is_shift_apostrophe(qwerty_uk: Layout) -> None:
    """On UK, @ is Shift-' so its physical key is the apostrophe."""
    assert qwerty_uk.physical_key("@") == "'"


def test_qwerty_uk_doublequote_is_shift_2(qwerty_uk: Layout) -> None:
    assert qwerty_uk.physical_key('"') == "2"


def test_qwerty_uk_has_hash_and_backslash(qwerty_uk: Layout) -> None:
    assert qwerty_uk.has_key("#")
    assert qwerty_uk.has_key("\\")
    assert qwerty_uk.has_key("|")  # via shift map of \


def test_qwerty_intl_matches_us(qwerty_intl: Layout, qwerty_us: Layout) -> None:
    assert dict(qwerty_intl.char_to_pos) == dict(qwerty_us.char_to_pos)
    assert dict(qwerty_intl.shift_map) == dict(qwerty_us.shift_map)


def test_numpad_layout_basics(numpad: Layout) -> None:
    assert numpad.position("7") == (0, 0)
    assert numpad.position("9") == (0, 2)
    assert numpad.position("0") == (3, 1)
    assert numpad.is_adjacent("1", "2")
    assert numpad.is_adjacent("4", "5")
    assert numpad.is_adjacent("0", "1")
    assert numpad.is_adjacent("0", "2")
    assert numpad.is_adjacent("0", "3")


def test_numpad_no_shift_map(numpad: Layout) -> None:
    assert dict(numpad.shift_map) == {}


def test_neighbors_returns_sorted_unique(qwerty_us: Layout) -> None:
    n = qwerty_us.neighbors("s")
    assert n == sorted(n)
    assert len(n) == len(set(n))
    assert "s" not in n
    # s = (2, 2). Neighbors are the 8 keys in rows 1-3, cols 1-3 except s itself.
    expected = {"q", "w", "e", "a", "d", "z", "x", "c"}
    assert set(n) == expected


def test_neighbors_for_top_row_includes_letter_row(qwerty_us: Layout) -> None:
    """A number-row key has neighbors in row 1 directly below."""
    n = qwerty_us.neighbors("2")
    assert "1" in n
    assert "q" in n
    assert "w" in n
    assert "3" in n


def test_get_layout_returns_known(qwerty_us: Layout) -> None:
    assert get_layout("qwerty_us") is qwerty_us


def test_get_layout_unknown_raises() -> None:
    with pytest.raises(KeyError):
        get_layout("dvorak")


def test_position_unknown_char_raises(qwerty_us: Layout) -> None:
    with pytest.raises(KeyError):
        qwerty_us.position("é")  # acute e, not on US grid


def test_layouts_registry_complete() -> None:
    assert set(LAYOUTS.keys()) == {"qwerty_us", "qwerty_uk", "qwerty_intl", "numpad"}
