"""Deep walk analysis: physical travel, hand/finger dynamics, and layout ID.

This module layers richer, descriptive metrics on top of the calibrated
six-feature :func:`keywalk_audit.walks.scorer.score_walk`. The calibrated score
is deliberately left untouched (so the acceptance thresholds stay stable); the
analysis here adds signals that are useful for triage and reporting but are not
part of the score:

- **Physical travel** uses the layout's stagger-aware Euclidean model to
  measure how far the fingers move, and what fraction of steps are short
  (neighbour-to-neighbour) -- a high "smoothness" is characteristic of walks.
- **Hand and finger dynamics** use the layout finger map to count hand
  alternations and same-finger repeats.
- **Repeat structure** detects runs of the same physical key (``aaaa`` is not a
  walk even though its adjacency ratio is undefined).
- **Layout identification** scores a candidate against every registered layout
  and returns the best-fitting one, so ``azerty`` is attributed to AZERTY and
  ``qwertz`` to QWERTZ rather than to the default US layout.
- **Walk guessability** estimates the bits of search an attacker enumerating
  walks on the layout would spend to reach the candidate.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from keywalk_audit.layouts import LAYOUTS, get_layout
from keywalk_audit.walks.scorer import WalkScore, score_walk

if TYPE_CHECKING:
    from collections.abc import Sequence

    from keywalk_audit.layouts.base import Layout

# A step counts as "smooth" (walk-like) when the stagger-aware Euclidean
# distance between the two physical keys is at most this many key units. A
# vertical neighbour spans ~1.1u and a staggered diagonal up to ~1.5u, so 1.6
# admits genuine neighbour moves while excluding cross-keyboard jumps.
_SMOOTH_MAX_DISTANCE = 1.6

# log2 of the eight cardinal/diagonal directions, used by the walk-guessability
# estimate: each direction change multiplies the attacker's walk search space.
_LOG2_DIRECTIONS = 3.0


@dataclass(frozen=True)
class WalkAnalysis:
    """A comprehensive, descriptive analysis of a candidate walk."""

    plaintext: str
    layout: str
    length: int
    score: WalkScore
    physical_travel: float
    mean_step_distance: float
    physical_smoothness: float
    hands_used: tuple[str, ...]
    hand_alternations: int
    hand_alternation_ratio: float
    same_finger_repeats: int
    same_finger_ratio: float
    max_repeat_run: int
    repeat_ratio: float
    turn_count: int
    unique_directions: int
    walk_guess_bits: float


@dataclass(frozen=True)
class LayoutMatch:
    """A layout name paired with the candidate's walk score on that layout."""

    layout: str
    score: float


def _resolved_pairs(plaintext: str, layout: Layout) -> list[tuple[str, str]]:
    """Return consecutive (a, b) pairs where both chars resolve on the layout."""
    pairs: list[tuple[str, str]] = []
    for i in range(len(plaintext) - 1):
        a, b = plaintext[i], plaintext[i + 1]
        if layout.has_key(a) and layout.has_key(b):
            pairs.append((a, b))
    return pairs


def _physical_metrics(plaintext: str, layout: Layout) -> tuple[float, float, float]:
    """Return (total_travel, mean_step_distance, smoothness)."""
    pairs = _resolved_pairs(plaintext, layout)
    if not pairs:
        return (0.0, 0.0, 0.0)
    distances = [layout.euclidean_distance(a, b) for a, b in pairs]
    total = math.fsum(distances)
    mean = total / len(distances)
    smooth = sum(1 for d in distances if d <= _SMOOTH_MAX_DISTANCE) / len(distances)
    return (total, mean, smooth)


def _hand_metrics(plaintext: str, layout: Layout) -> tuple[tuple[str, ...], int, float, int, float]:
    """Return (hands_used, hand_alternations, alt_ratio, same_finger, sf_ratio)."""
    hands: list[str] = []
    for ch in plaintext:
        hand = layout.hand_of(ch)
        if hand is not None:
            hands.append(hand)
    hands_used = tuple(sorted(set(hands)))

    pairs = _resolved_pairs(plaintext, layout)
    considered = 0
    alternations = 0
    same_finger = 0
    for a, b in pairs:
        hand_a, hand_b = layout.hand_of(a), layout.hand_of(b)
        finger_a, finger_b = layout.finger_of(a), layout.finger_of(b)
        if hand_a is None or hand_b is None:
            continue
        considered += 1
        if hand_a != hand_b:
            alternations += 1
        elif finger_a is not None and finger_a == finger_b:
            same_finger += 1
    alt_ratio = alternations / considered if considered else 0.0
    sf_ratio = same_finger / considered if considered else 0.0
    return (hands_used, alternations, alt_ratio, same_finger, sf_ratio)


def _repeat_metrics(plaintext: str, layout: Layout) -> tuple[int, float]:
    """Return (max_repeat_run, repeat_ratio) over identical consecutive keys.

    ``max_repeat_run`` is the longest run of the same physical key as a
    character count (``aaaa`` -> 4). ``repeat_ratio`` is the fraction of
    consecutive character pairs that press the identical physical key.
    """
    if len(plaintext) < 2:
        return (len(plaintext), 0.0)
    keys = [layout.physical_key(c) for c in plaintext]
    best_run = 1
    current = 1
    repeats = 0
    for i in range(1, len(keys)):
        if keys[i] == keys[i - 1]:
            current += 1
            repeats += 1
            best_run = max(best_run, current)
        else:
            current = 1
    return (best_run, repeats / (len(keys) - 1))


def _direction_metrics(plaintext: str, layout: Layout) -> tuple[int, int]:
    """Return (turn_count, unique_directions) over the resolved key path."""
    directions: list[tuple[int, int]] = []
    for a, b in _resolved_pairs(plaintext, layout):
        if layout.physical_key(a) == layout.physical_key(b):
            continue
        directions.append(layout.direction(a, b))
    if not directions:
        return (0, 0)
    turns = sum(1 for i in range(1, len(directions)) if directions[i] != directions[i - 1])
    return (turns, len(set(directions)))


def _walk_guess_bits(layout: Layout, turn_count: int) -> float:
    """Estimate bits of attacker search to enumerate this walk on the layout.

    Heuristic: an attacker enumerating keyboard walks chooses a start key
    (``log2`` of the key count) and then pays roughly ``log2(8)`` bits at each
    direction change, since straight continuations are nearly free. This is a
    walk-specific guessability proxy, not a general password-strength estimate.
    """
    key_count = max(1, len(layout.char_to_pos))
    return math.log2(key_count) + turn_count * _LOG2_DIRECTIONS


def analyze_walk(plaintext: str, layout: Layout) -> WalkAnalysis:
    """Return a full :class:`WalkAnalysis` for ``plaintext`` on ``layout``."""
    score = score_walk(plaintext, layout)
    travel, mean_step, smoothness = _physical_metrics(plaintext, layout)
    hands_used, alternations, alt_ratio, same_finger, sf_ratio = _hand_metrics(plaintext, layout)
    max_run, repeat_ratio = _repeat_metrics(plaintext, layout)
    turns, unique_dirs = _direction_metrics(plaintext, layout)
    return WalkAnalysis(
        plaintext=plaintext,
        layout=layout.name,
        length=len(plaintext),
        score=score,
        physical_travel=travel,
        mean_step_distance=mean_step,
        physical_smoothness=smoothness,
        hands_used=hands_used,
        hand_alternations=alternations,
        hand_alternation_ratio=alt_ratio,
        same_finger_repeats=same_finger,
        same_finger_ratio=sf_ratio,
        max_repeat_run=max_run,
        repeat_ratio=repeat_ratio,
        turn_count=turns,
        unique_directions=unique_dirs,
        walk_guess_bits=_walk_guess_bits(layout, turns),
    )


def rank_layouts(plaintext: str, layout_names: Sequence[str] | None = None) -> list[LayoutMatch]:
    """Score ``plaintext`` against each layout, best walk score first.

    Ties are broken by layout name for determinism. ``layout_names`` defaults
    to every registered layout.
    """
    names = list(layout_names) if layout_names is not None else list(LAYOUTS)
    matches = [
        LayoutMatch(layout=name, score=score_walk(plaintext, get_layout(name)).total)
        for name in names
    ]
    matches.sort(key=lambda m: (-m.score, m.layout))
    return matches


def best_layout(plaintext: str, layout_names: Sequence[str] | None = None) -> LayoutMatch:
    """Return the single best-fitting layout for ``plaintext``."""
    return rank_layouts(plaintext, layout_names)[0]
