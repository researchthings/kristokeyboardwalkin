"""Tests for walks/generator.py."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

from keywalk_audit.walks.generator import generate_walks_long, generate_walks_short
from keywalk_audit.walks.scorer import score_walk

if TYPE_CHECKING:
    from keywalk_audit.layouts.base import Layout


def test_short_walks_returns_iterator(qwerty_us: Layout) -> None:
    walks = generate_walks_short(qwerty_us, min_len=4, max_len=4, max_turns=0)
    assert isinstance(walks, Iterator)


def test_short_walks_respect_min_max_len(qwerty_us: Layout) -> None:
    walks = list(generate_walks_short(qwerty_us, min_len=4, max_len=6, max_turns=2))
    assert all(4 <= len(w) <= 6 for w in walks)


def test_short_walks_have_full_adjacency(qwerty_us: Layout) -> None:
    """Every emitted short walk has adjacency_ratio == 1.0."""
    sample = list(generate_walks_short(qwerty_us, min_len=4, max_len=5, max_turns=2))
    assert sample, "expected non-empty sample of short walks"
    for w in sample[:300]:
        assert score_walk(w, qwerty_us).adjacency_ratio == 1.0


def test_short_walks_no_turns_only_straight_lines(qwerty_us: Layout) -> None:
    walks = list(generate_walks_short(qwerty_us, min_len=4, max_len=4, max_turns=0))
    assert "1qaz" in walks
    assert "qwer" in walks
    assert "asdf" in walks


def test_short_walks_includes_canonical_seeds(qwerty_us: Layout) -> None:
    walks = set(generate_walks_short(qwerty_us, min_len=4, max_len=8, max_turns=2))
    assert "1qazxsw2" in walks
    assert "1qaz" in walks


def test_short_walks_no_repeats_within(qwerty_us: Layout) -> None:
    """Single-key revisits are forbidden within a short walk."""
    for w in generate_walks_short(qwerty_us, min_len=4, max_len=8, max_turns=2):
        assert len(w) == len(set(w))


def test_short_walks_invalid_args_yield_nothing(qwerty_us: Layout) -> None:
    assert list(generate_walks_short(qwerty_us, min_len=10, max_len=4)) == []
    assert list(generate_walks_short(qwerty_us, min_len=2, max_len=8, max_turns=-1)) == []


def test_long_walks_compose(qwerty_us: Layout) -> None:
    shorts = ["1qaz", "2wsx"]
    out = list(generate_walks_long(qwerty_us, shorts, max_len=16, max_segments=3))
    assert "1qaz2wsx" in out
    assert "1qaz1qaz2wsx" in out


def test_long_walks_respect_max_len(qwerty_us: Layout) -> None:
    shorts = ["1qaz", "2wsx"]
    out = list(generate_walks_long(qwerty_us, shorts, max_len=8, max_segments=3))
    assert all(len(w) <= 8 for w in out)
    assert "1qaz1qaz" in out
    assert "1qaz2wsx" in out


def test_long_walks_min_segments_two(qwerty_us: Layout) -> None:
    shorts = ["1qaz"]
    out = list(generate_walks_long(qwerty_us, shorts, max_len=32, max_segments=1))
    assert out == []


def test_long_walks_skips_empty_inputs(qwerty_us: Layout) -> None:
    shorts: list[str] = []
    assert list(generate_walks_long(qwerty_us, shorts)) == []
