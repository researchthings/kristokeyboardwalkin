"""Tests for walks/variants.py."""

from __future__ import annotations

from typing import TYPE_CHECKING

from keywalk_audit.walks.variants import all_variants, reversal, shift_mirror

if TYPE_CHECKING:
    from keywalk_audit.layouts.base import Layout


def test_shift_mirror_basic(qwerty_us: Layout) -> None:
    assert shift_mirror("1qaz", qwerty_us) == "!QAZ"
    assert shift_mirror("!QAZ", qwerty_us) == "1qaz"


def test_shift_mirror_idempotent_pairwise(qwerty_us: Layout) -> None:
    """Shift-mirroring twice returns the original input."""
    s = "1qazxsw2"
    assert shift_mirror(shift_mirror(s, qwerty_us), qwerty_us) == s


def test_shift_mirror_passthrough_unknown(qwerty_us: Layout) -> None:
    """Characters outside the shift map pass through unchanged."""
    assert shift_mirror("é", qwerty_us) == "é"


def test_shift_mirror_canonical_pairs(
    qwerty_us: Layout, shift_mirror_pairs: list[tuple[str, str]]
) -> None:
    for raw, mirrored in shift_mirror_pairs:
        assert shift_mirror(raw, qwerty_us) == mirrored


def test_reversal() -> None:
    assert reversal("1qaz") == "zaq1"
    assert reversal("") == ""
    assert reversal("a") == "a"


def test_all_variants_includes_self_and_mirror(qwerty_us: Layout) -> None:
    variants = all_variants("1qaz", qwerty_us)
    assert "1qaz" in variants
    assert "!QAZ" in variants
    assert "zaq1" in variants
    assert "ZAQ!" in variants


def test_all_variants_palindrome_collapses(qwerty_us: Layout) -> None:
    """A palindromic input has its reversal equal to itself."""
    variants = all_variants("aza", qwerty_us)
    assert "aza" in variants
    assert "AZA" in variants
