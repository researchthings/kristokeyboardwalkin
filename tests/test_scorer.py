"""Tests for walks/scorer.py."""

from __future__ import annotations

from typing import TYPE_CHECKING

from hypothesis import given
from hypothesis import strategies as st

from keywalk_audit.layouts import QWERTY_US
from keywalk_audit.walks.scorer import ScoreWeights, score_walk

if TYPE_CHECKING:
    from collections.abc import Sequence

    from keywalk_audit.layouts.base import Layout

CANONICAL_THRESHOLD = 0.7
RANDOM_MAX = 0.5


def test_default_weights_sum_to_one() -> None:
    w = ScoreWeights()
    total = (
        w.adjacency_ratio
        + w.longest_run
        + w.direction_entropy
        + w.shift_mirror
        + w.reversal
        + w.segment_count
    )
    assert abs(total - 1.0) < 1e-9


def test_canonical_walks_all_above_threshold(
    qwerty_us: Layout, canonical_walks: Sequence[str]
) -> None:
    for walk in canonical_walks:
        result = score_walk(walk, qwerty_us)
        assert result.total >= CANONICAL_THRESHOLD, (
            f"{walk!r} scored {result.total:.3f}; expected >= {CANONICAL_THRESHOLD}"
        )


def test_random_passwords_below_threshold(
    qwerty_us: Layout, random_passwords: Sequence[str]
) -> None:
    for pw in random_passwords:
        result = score_walk(pw, qwerty_us)
        assert result.total < RANDOM_MAX, (
            f"{pw!r} unexpectedly scored {result.total:.3f}; expected < {RANDOM_MAX}"
        )


def test_total_clamped_to_unit_interval(qwerty_us: Layout) -> None:
    for s in ("1qazxsw2!QAZXSW@", "Tx7mP$qz", "", "x", "qq"):
        result = score_walk(s, qwerty_us)
        assert 0.0 <= result.total <= 1.0


def test_short_input_returns_zero(qwerty_us: Layout) -> None:
    result = score_walk("a", qwerty_us)
    assert result.total == 0.0
    assert result.adjacency_ratio == 0.0
    assert result.longest_run == 1


def test_empty_input(qwerty_us: Layout) -> None:
    result = score_walk("", qwerty_us)
    assert result.total == 0.0
    assert result.longest_run == 0


def test_full_adjacency_ratio_for_walk(qwerty_us: Layout) -> None:
    result = score_walk("1qazxsw2", qwerty_us)
    assert result.adjacency_ratio == 1.0


def test_longest_run_segment_aware_normalization(qwerty_us: Layout) -> None:
    """Composed walk with 4 segments of length 4 must hit longest_run = 1.0."""
    result = score_walk("1qaz2wsx3edc4rfv", qwerty_us)
    assert result.segment_count == 4
    assert result.longest_run_normalized == 1.0


def test_shift_mirror_feature_set_for_canonical(qwerty_us: Layout) -> None:
    result = score_walk("1qaz!QAZ", qwerty_us)
    assert result.shift_mirror == 1.0


def test_reversal_feature_for_palindrome(qwerty_us: Layout) -> None:
    result = score_walk("asdfdsa", qwerty_us)
    # Physical keys form a palindrome; reversal feature should fire.
    assert result.reversal == 1.0


def test_reversal_feature_for_non_palindrome(qwerty_us: Layout) -> None:
    result = score_walk("1qaz2wsx", qwerty_us)
    assert result.reversal == 0.0


def test_shift_mirror_zero_for_odd_length(qwerty_us: Layout) -> None:
    result = score_walk("1qa", qwerty_us)
    assert result.shift_mirror == 0.0


@given(st.text(alphabet="qwertyuiopasdfghjklzxcvbnm", min_size=4, max_size=10))
def test_score_total_in_unit_interval(s: str) -> None:
    result = score_walk(s, QWERTY_US)
    assert 0.0 <= result.total <= 1.0


def test_adjacency_ratio_one_for_known_walks(qwerty_us: Layout) -> None:
    """Pure walks should have adjacency_ratio == 1.0 before any composition."""
    for walk in ("1qaz", "qwerty", "asdfgh", "zxcvbnm", "1qazxsw2", "qaz"):
        result = score_walk(walk, qwerty_us)
        assert result.adjacency_ratio == 1.0, f"{walk!r}: {result.adjacency_ratio}"
