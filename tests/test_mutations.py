"""Tests for keywalk_audit.hashing.mutations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from keywalk_audit.hashing.mutations import (
    DEFAULT_RULES,
    expand_wordlist,
    python_mutations,
    walk_masks,
    write_rule_file,
)

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# DEFAULT_RULES
# ---------------------------------------------------------------------------


def test_default_rules_non_empty() -> None:
    assert len(DEFAULT_RULES) > 0


def test_default_rules_all_strings() -> None:
    assert all(isinstance(r, str) for r in DEFAULT_RULES)


def test_default_rules_contains_passthrough() -> None:
    assert ":" in DEFAULT_RULES


def test_default_rules_contains_digit_append() -> None:
    assert "$1" in DEFAULT_RULES


def test_default_rules_contains_capitalize_rule() -> None:
    # 'c' alone should be present
    assert "c" in DEFAULT_RULES


def test_default_rules_contains_capitalize_with_digit() -> None:
    # a combined capitalize-then-append-digit rule
    assert "c$1" in DEFAULT_RULES


def test_default_rules_no_duplicates() -> None:
    assert len(DEFAULT_RULES) == len(set(DEFAULT_RULES))


# ---------------------------------------------------------------------------
# write_rule_file
# ---------------------------------------------------------------------------


def test_write_rule_file_returns_correct_count(tmp_path: Path) -> None:
    rules = [":", "c", "$1", "r"]
    out = tmp_path / "test.rule"
    count = write_rule_file(rules, out)
    assert count == len(rules)


def test_write_rule_file_roundtrip(tmp_path: Path) -> None:
    rules = [":", "c", "$1", "r", "d", "u"]
    out = tmp_path / "roundtrip.rule"
    write_rule_file(rules, out)
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines == rules


def test_write_rule_file_empty(tmp_path: Path) -> None:
    out = tmp_path / "empty.rule"
    count = write_rule_file([], out)
    assert count == 0


# ---------------------------------------------------------------------------
# python_mutations
# ---------------------------------------------------------------------------


def test_python_mutations_original_first() -> None:
    pw = "1qaz2wsx"
    result = python_mutations(pw)
    assert result[0] == pw


def test_python_mutations_includes_symbol_append() -> None:
    result = python_mutations("1qaz2wsx")
    assert "1qaz2wsx!" in result


def test_python_mutations_includes_capitalize() -> None:
    # capitalize() makes first char upper, rest lower
    result = python_mutations("1qaz2wsx")
    assert "1qaz2wsx".capitalize() in result


def test_python_mutations_includes_duplicate() -> None:
    pw = "1qaz2wsx"
    result = python_mutations(pw)
    assert pw + pw in result


def test_python_mutations_no_duplicates() -> None:
    result = python_mutations("1qaz2wsx")
    assert len(result) == len(set(result))


def test_python_mutations_leet_on_passe() -> None:
    # "passe" -> leet: a->@, s->$, s->$, e->3  => "p@$$3"
    result = python_mutations("passe")
    assert "p@$$3" in result


def test_python_mutations_includes_year() -> None:
    result = python_mutations("1qaz2wsx")
    assert "1qaz2wsx2023" in result


def test_python_mutations_includes_digit_appends() -> None:
    result = python_mutations("abc")
    for digit in "0123456789":
        assert "abc" + digit in result


def test_python_mutations_includes_upper_and_lower() -> None:
    result = python_mutations("Hello")
    assert "HELLO" in result
    assert "hello" in result


def test_python_mutations_includes_reverse() -> None:
    result = python_mutations("abcdef")
    assert "fedcba" in result


# ---------------------------------------------------------------------------
# expand_wordlist
# ---------------------------------------------------------------------------


def test_expand_wordlist_no_mutate_unique(tmp_path: Path) -> None:
    words = ["alpha", "beta", "alpha", "gamma"]
    out = tmp_path / "plain.txt"
    count = expand_wordlist(words, out)
    lines = out.read_text(encoding="utf-8").splitlines()
    assert count == 3
    assert lines == ["alpha", "beta", "gamma"]


def test_expand_wordlist_no_mutate_count_matches_file(tmp_path: Path) -> None:
    words = ["one", "two", "three"]
    out = tmp_path / "count.txt"
    count = expand_wordlist(words, out)
    lines = out.read_text(encoding="utf-8").splitlines()
    assert count == len(lines)


def test_expand_wordlist_mutate_is_superset(tmp_path: Path) -> None:
    words = ["abc"]
    plain_out = tmp_path / "plain.txt"
    mutated_out = tmp_path / "mutated.txt"
    plain_count = expand_wordlist(words, plain_out)
    mutated_count = expand_wordlist(words, mutated_out, mutate=True)
    assert mutated_count > plain_count


def test_expand_wordlist_mutate_count_matches_file(tmp_path: Path) -> None:
    words = ["abc", "xyz"]
    out = tmp_path / "mutated_count.txt"
    count = expand_wordlist(words, out, mutate=True)
    lines = out.read_text(encoding="utf-8").splitlines()
    assert count == len(lines)


def test_expand_wordlist_mutate_no_duplicates(tmp_path: Path) -> None:
    # duplicate source words should not cause duplicate mutations
    words = ["abc", "abc", "abc"]
    out = tmp_path / "dedup.txt"
    expand_wordlist(words, out, mutate=True)
    lines = out.read_text(encoding="utf-8").splitlines()
    assert len(lines) == len(set(lines))


def test_expand_wordlist_empty(tmp_path: Path) -> None:
    out = tmp_path / "empty.txt"
    count = expand_wordlist([], out)
    assert count == 0
    assert out.read_text(encoding="utf-8") == ""


# ---------------------------------------------------------------------------
# walk_masks
# ---------------------------------------------------------------------------


def test_walk_masks_non_empty() -> None:
    assert len(walk_masks()) > 0


def test_walk_masks_all_strings() -> None:
    assert all(isinstance(m, str) for m in walk_masks())


def test_walk_masks_contain_digit_token() -> None:
    masks = walk_masks()
    assert any("?d" in m for m in masks)


def test_walk_masks_contain_lower_token() -> None:
    masks = walk_masks()
    assert any("?l" in m for m in masks)


def test_walk_masks_custom_range() -> None:
    masks = walk_masks(min_len=4, max_len=4)
    assert all(m.count("?") == 4 for m in masks)


def test_walk_masks_no_duplicates() -> None:
    masks = walk_masks()
    assert len(masks) == len(set(masks))


def test_walk_masks_respect_min_len() -> None:
    masks = walk_masks(min_len=8, max_len=10)
    for mask in masks:
        assert mask.count("?") >= 8


def test_walk_masks_respect_max_len() -> None:
    masks = walk_masks(min_len=6, max_len=8)
    for mask in masks:
        assert mask.count("?") <= 8
