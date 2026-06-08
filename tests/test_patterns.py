"""Tests for walks/patterns.py structural generators."""

from __future__ import annotations

from typing import TYPE_CHECKING

from keywalk_audit.layouts import AZERTY_FR, QWERTZ_DE
from keywalk_audit.walks.patterns import (
    FAMOUS_WALKS,
    columns,
    generate_doublings,
    generate_knight_walks,
    generate_known,
    generate_pattern_walks,
    generate_sweeps,
    generate_zigzags,
    rows,
)

if TYPE_CHECKING:
    from keywalk_audit.layouts.base import Layout


def test_rows_and_columns_basic(qwerty_us: Layout) -> None:
    assert rows(qwerty_us)[1].startswith("qwerty")
    assert columns(qwerty_us)[1] == "1qaz"
    assert columns(qwerty_us)[2] == "2wsx"


def test_sweeps_are_on_layout_and_in_bounds(qwerty_us: Layout) -> None:
    sweeps = list(generate_sweeps(qwerty_us, 4, 8))
    assert sweeps
    assert "qwer" in sweeps
    assert "1qaz" in sweeps
    for w in sweeps:
        assert 4 <= len(w) <= 8
        assert all(qwerty_us.has_key(c) for c in w)


def test_known_walks_filtered_by_layout(qwerty_us: Layout, numpad: Layout) -> None:
    qwerty_known = set(generate_known(qwerty_us, 4, 16))
    assert "qwerty" in qwerty_known
    assert "qazwsx" in qwerty_known
    numpad_known = set(generate_known(numpad, 4, 16))
    assert "qwerty" not in numpad_known
    assert "147258" in numpad_known


def test_known_walks_apply_to_native_layouts() -> None:
    assert "azerty" in set(generate_known(AZERTY_FR, 4, 16))
    assert "qwertz" in set(generate_known(QWERTZ_DE, 4, 16))


def test_zigzags_interleave_rows(qwerty_us: Layout) -> None:
    zz = list(generate_zigzags(qwerty_us, 4, 12))
    assert zz
    # Rows 1 and 2 interleaved by column begin q,a,w,s,e,d,...
    assert any(w.startswith("qawsed") for w in zz)
    for w in zz:
        assert 4 <= len(w) <= 12
        assert all(qwerty_us.has_key(c) for c in w)


def test_doublings_respect_max_len() -> None:
    out = list(generate_doublings(["1qaz"], max_len=8))
    assert "1qaz1qaz" in out
    assert all(len(w) <= 8 for w in out)
    # Tripling 1qaz is length 12, excluded at max_len 8 but present at 12.
    out12 = list(generate_doublings(["1qaz"], max_len=12))
    assert "1qaz1qaz1qaz" in out12


def test_pattern_walks_deduplicated_and_bounded(qwerty_us: Layout) -> None:
    walks = list(generate_pattern_walks(qwerty_us, 4, 12))
    assert walks
    assert len(walks) == len(set(walks)), "patterns must be unique"
    assert "qwerty" in walks
    for w in walks:
        assert 4 <= len(w) <= 12


def test_pattern_walks_invalid_bounds_yield_nothing(qwerty_us: Layout) -> None:
    assert list(generate_pattern_walks(qwerty_us, 12, 4)) == []


def test_knight_walks_are_capped(qwerty_us: Layout) -> None:
    walks = list(generate_knight_walks(qwerty_us, 4, 6, cap=25))
    assert len(walks) <= 25
    for w in walks:
        assert 4 <= len(w) <= 6
        assert all(qwerty_us.has_key(c) for c in w)


def test_knight_walks_are_opt_in(qwerty_us: Layout) -> None:
    without = set(generate_pattern_walks(qwerty_us, 4, 6))
    with_knight = set(generate_pattern_walks(qwerty_us, 4, 6, include_knight=True, knight_cap=200))
    assert without <= with_knight
    assert len(with_knight) > len(without)


def test_famous_walks_constant_nonempty() -> None:
    assert FAMOUS_WALKS
    assert "qwerty" in FAMOUS_WALKS
    assert all(isinstance(w, str) for w in FAMOUS_WALKS)
