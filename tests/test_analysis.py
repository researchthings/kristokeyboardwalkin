"""Tests for walks/analysis.py deep analysis and layout identification."""

from __future__ import annotations

from typing import TYPE_CHECKING

from keywalk_audit.walks.analysis import analyze_walk, best_layout, rank_layouts

if TYPE_CHECKING:
    from keywalk_audit.layouts.base import Layout


def test_analyze_composed_walk(qwerty_us: Layout) -> None:
    a = analyze_walk("1qaz2wsx3edc4rfv", qwerty_us)
    assert a.layout == "qwerty_us"
    assert a.length == 16
    assert a.score.total >= 0.7
    assert a.max_repeat_run == 1
    assert a.repeat_ratio == 0.0
    # Within-segment steps are smooth; the 3 inter-segment jumps are not, so
    # 12 of 15 steps are short -> 0.8.
    assert a.physical_smoothness == 0.8
    assert "left" in a.hands_used
    assert a.walk_guess_bits > 0.0


def test_analyze_pure_repeat(qwerty_us: Layout) -> None:
    a = analyze_walk("aaaa", qwerty_us)
    assert a.max_repeat_run == 4
    assert a.repeat_ratio == 1.0
    # A pure repeat is not a walk.
    assert a.score.total < 0.5


def test_physical_travel_horizontal_run(qwerty_us: Layout) -> None:
    a = analyze_walk("qwer", qwerty_us)
    # Three unit steps along a row.
    assert abs(a.physical_travel - 3.0) < 1e-9
    assert abs(a.mean_step_distance - 1.0) < 1e-9
    assert a.physical_smoothness == 1.0


def test_hand_and_finger_metrics(qwerty_us: Layout) -> None:
    a = analyze_walk("fghj", qwerty_us)
    # f,g left; h,j right -> exactly one hand alternation (g->h) of three pairs.
    assert a.hand_alternations == 1
    # f,g share the left index; h,j share the right index -> two same-finger pairs.
    assert a.same_finger_repeats == 2
    assert set(a.hands_used) == {"left", "right"}


def test_rank_layouts_identifies_azerty() -> None:
    best = best_layout("azerty")
    assert best.layout == "azerty_fr"
    ranking = rank_layouts("azerty")
    assert ranking[0].layout == "azerty_fr"
    assert ranking[0].score >= ranking[-1].score


def test_rank_layouts_identifies_qwertz() -> None:
    assert best_layout("qwertz").layout == "qwertz_de"


def test_rank_layouts_qwerty_family_for_qwerty() -> None:
    # qwerty resolves identically on the three QWERTY variants; the best fit
    # must be one of them, never azerty or a keypad.
    assert best_layout("qwerty").layout.startswith("qwerty")


def test_rank_layouts_respects_explicit_subset() -> None:
    ranking = rank_layouts("1qaz", layout_names=["numpad", "qwerty_us"])
    assert {m.layout for m in ranking} == {"numpad", "qwerty_us"}
    assert ranking[0].layout == "qwerty_us"


def test_walk_guess_bits_increases_with_turns(qwerty_us: Layout) -> None:
    straight = analyze_walk("qwert", qwerty_us)
    turning = analyze_walk("1qaz2wsx", qwerty_us)
    assert turning.turn_count >= straight.turn_count
    assert turning.walk_guess_bits >= straight.walk_guess_bits
