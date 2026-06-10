"""Walk scoring: a clamped 0..1 keyboard-walk score from two sub-scores.

The score recognizes two *kinds* of walk that live in different feature
subspaces, so it OR-combines an adjacency-driven sub-score with a
structural sub-score: ``total = clamp(max(adjacency_score, structural_score))``.

Adjacency features (summed with calibrated ``ScoreWeights``)
------------------------------------------------------------
1. Adjacency ratio: fraction of consecutive character pairs that are physically
   adjacent on the layout grid.
2. Longest run: length of the longest contiguous adjacency run, normalized by
   the expected segment length `len(p) / max(1, segment_count)`. This
   segment-aware normalization keeps composed walks like ``1qaz2wsx3edc4rfv``
   from being penalized for short individual segments.
3. Direction entropy: ``1 - H / log2(9)`` where ``H`` is the Shannon entropy
   of the observed direction-vector distribution and ``log2(9)`` is the
   maximum entropy across the 8 cardinal/diagonal unit directions plus zero.
4. Shift mirror: 1.0 when the second half of the input is the shift-mirror of
   the first half, else 0.0. Odd-length inputs return 0.0.
5. Reversal: 1.0 when the physical-key sequence is a palindrome, else 0.0.
6. Segment count: the number of contiguous adjacency runs of length >= 4,
   normalized by ``floor(len(p) / 4)``.

Structural sub-score (``StructuralWeights``)
--------------------------------------------
7. Periodicity: fraction of the physical-key sequence explained by a repeating
   base unit (``(n - q) / n`` for the smallest period ``q``), so ``base * k``
   repetitions score high. Combined with the shift-mirror and direction-entropy
   features, this flags low-adjacency-but-clearly-structured walks such as
   ``1a0k1a0k!A)K!A)K`` (number<->letter column jumps, repeated and
   shift-mirrored) that the adjacency sub-score alone rates near zero.

Because ``total`` is the *max* of the two sub-scores, the structural path can
only raise a score, never lower one the adjacency path already assigned -- so
every walk the adjacency model accepts stays accepted.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from keywalk_audit.walks.variants import shift_mirror

if TYPE_CHECKING:
    from keywalk_audit.layouts.base import Layout

_MIN_SEGMENT_LEN = 4
_MAX_DIRECTION_ENTROPY = math.log2(9)


@dataclass(frozen=True)
class ScoreWeights:
    """Linear-combination weights for the six scoring features.

    The defaults are calibrated so that all eight canonical reference walks
    score >= 0.7 while typical random passwords score below 0.5.
    """

    adjacency_ratio: float = 0.35
    longest_run: float = 0.20
    direction_entropy: float = 0.10
    shift_mirror: float = 0.10
    reversal: float = 0.10
    segment_count: float = 0.15


@dataclass(frozen=True)
class StructuralWeights:
    """Weights for the structural sub-score (periodicity, shift mirror, low
    direction entropy).

    These are intentionally NOT part of :class:`ScoreWeights`: the structural
    sub-score is OR-combined with the adjacency-driven sum (``total`` takes the
    max of the two) rather than added into it, so it has no reason to share the
    unit-sum budget and is clamped to ``[0, 1]`` independently. ``shift_mirror``
    carries the largest weight because it is 1.0 for the entire
    ``(base * k) + (shift_mirror(base) * k)`` family by construction, which
    gives the tightest member (``k = 1`` with a short base, where periodicity is
    only 0.5) margin above the 0.7 acceptance threshold. Random passwords carry
    no shift mirror and no periodicity, so their structural score stays near the
    small ``direction_entropy`` contribution.
    """

    periodicity: float = 0.40
    shift_mirror: float = 0.50
    direction_entropy: float = 0.15


@dataclass(frozen=True)
class WalkScore:
    """Result of scoring a candidate walk."""

    total: float
    adjacency_ratio: float
    longest_run: int
    longest_run_normalized: float
    direction_entropy: float
    shift_mirror: float
    reversal: float
    segment_count: int
    segment_count_normalized: float
    periodicity: float
    structural_score: float


def _adjacency_flags(plaintext: str, layout: Layout) -> list[bool]:
    return [layout.is_adjacent(plaintext[i], plaintext[i + 1]) for i in range(len(plaintext) - 1)]


def _longest_run(flags: list[bool]) -> int:
    """Return the longest contiguous adjacency run as a character count.

    A run of `k` consecutive True flags corresponds to `k + 1` characters.
    Returns 0 when the input has no characters and 1 when it has exactly one.
    """
    if not flags:
        return 0
    best_pairs = 0
    current = 0
    for flag in flags:
        if flag:
            current += 1
            best_pairs = max(best_pairs, current)
        else:
            current = 0
    return best_pairs + 1 if best_pairs > 0 else 1


def _segment_lengths(flags: list[bool]) -> list[int]:
    """Return character-length of each contiguous adjacency run."""
    lengths: list[int] = []
    pairs = 0
    for flag in flags:
        if flag:
            pairs += 1
        else:
            if pairs > 0:
                lengths.append(pairs + 1)
            pairs = 0
    if pairs > 0:
        lengths.append(pairs + 1)
    return lengths


def _direction_entropy_feature(plaintext: str, layout: Layout) -> float:
    if len(plaintext) < 2:
        return 0.0
    counts: dict[tuple[int, int], int] = {}
    total = 0
    for i in range(len(plaintext) - 1):
        a, b = plaintext[i], plaintext[i + 1]
        if not (layout.has_key(a) and layout.has_key(b)):
            continue
        delta = layout.direction(a, b)
        counts[delta] = counts.get(delta, 0) + 1
        total += 1
    if total == 0:
        return 0.0
    entropy = 0.0
    for count in counts.values():
        p = count / total
        entropy -= p * math.log2(p)
    return max(0.0, 1.0 - entropy / _MAX_DIRECTION_ENTROPY)


def _shift_mirror_feature(plaintext: str, layout: Layout) -> float:
    n = len(plaintext)
    if n < 2 or n % 2 != 0:
        return 0.0
    half = n // 2
    first = plaintext[:half]
    second = plaintext[half:]
    return 1.0 if shift_mirror(first, layout) == second else 0.0


def _reversal_feature(plaintext: str, layout: Layout) -> float:
    if len(plaintext) < 2:
        return 0.0
    keys = [layout.physical_key(c) for c in plaintext]
    return 1.0 if keys == list(reversed(keys)) else 0.0


def _periodicity_feature(plaintext: str, layout: Layout) -> float:
    """Return the fraction of the physical-key sequence explained by repetition.

    Finds the smallest period ``q`` (``1 <= q <= n // 2``) for which the
    physical-key sequence repeats, and returns ``(n - q) / n`` -- the fraction
    of the string covered by repeats of the base unit. A walk formed as
    ``base * k`` for any ``k >= 2`` is fully periodic and scores high; an
    aperiodic string scores 0. Operating on *physical* keys means a shift mirror
    such as ``1a0k!A)K`` (keys ``1a0k1a0k``) is recognized as periodic.
    """
    keys = [layout.physical_key(c) for c in plaintext]
    n = len(keys)
    if n < 2:
        return 0.0
    for q in range(1, n // 2 + 1):
        if all(keys[i] == keys[i - q] for i in range(q, n)):
            return (n - q) / n
    return 0.0


DEFAULT_WEIGHTS = ScoreWeights()
DEFAULT_STRUCTURAL_WEIGHTS = StructuralWeights()


def score_walk(
    plaintext: str,
    layout: Layout,
    weights: ScoreWeights = DEFAULT_WEIGHTS,
    structural_weights: StructuralWeights = DEFAULT_STRUCTURAL_WEIGHTS,
) -> WalkScore:
    """Compute the walk score for `plaintext` on `layout`."""
    n = len(plaintext)
    if n < 2:
        return WalkScore(
            total=0.0,
            adjacency_ratio=0.0,
            longest_run=n,
            longest_run_normalized=0.0,
            direction_entropy=0.0,
            shift_mirror=0.0,
            reversal=0.0,
            segment_count=0,
            segment_count_normalized=0.0,
            periodicity=0.0,
            structural_score=0.0,
        )

    flags = _adjacency_flags(plaintext, layout)
    pairs = len(flags)
    adjacency_ratio = sum(flags) / pairs if pairs > 0 else 0.0

    segment_lengths = _segment_lengths(flags)
    long_segments = [length for length in segment_lengths if length >= _MIN_SEGMENT_LEN]
    segment_count_int = len(long_segments)

    longest_run_chars = _longest_run(flags)
    expected_segment_len = n / max(1, segment_count_int)
    longest_run_normalized = min(1.0, longest_run_chars / max(1.0, expected_segment_len))

    direction_entropy = _direction_entropy_feature(plaintext, layout)
    mirror = _shift_mirror_feature(plaintext, layout)
    rev = _reversal_feature(plaintext, layout)

    segment_max = n // _MIN_SEGMENT_LEN
    segment_count_normalized = min(1.0, segment_count_int / segment_max) if segment_max > 0 else 0.0

    periodicity = _periodicity_feature(plaintext, layout)

    adjacency_total = (
        weights.adjacency_ratio * adjacency_ratio
        + weights.longest_run * longest_run_normalized
        + weights.direction_entropy * direction_entropy
        + weights.shift_mirror * mirror
        + weights.reversal * rev
        + weights.segment_count * segment_count_normalized
    )
    structural_score = min(
        1.0,
        structural_weights.periodicity * periodicity
        + structural_weights.shift_mirror * mirror
        + structural_weights.direction_entropy * direction_entropy,
    )
    total = max(0.0, min(1.0, max(adjacency_total, structural_score)))

    return WalkScore(
        total=total,
        adjacency_ratio=adjacency_ratio,
        longest_run=longest_run_chars,
        longest_run_normalized=longest_run_normalized,
        direction_entropy=direction_entropy,
        shift_mirror=mirror,
        reversal=rev,
        segment_count=segment_count_int,
        segment_count_normalized=segment_count_normalized,
        periodicity=periodicity,
        structural_score=structural_score,
    )
