"""Tests for fuzzy/string_minhash.py."""

from __future__ import annotations

from typing import TYPE_CHECKING

from keywalk_audit.fuzzy import StringMinHashIndex

if TYPE_CHECKING:
    from pathlib import Path


def test_index_basic_add_and_query() -> None:
    idx = StringMinHashIndex(num_perm=128, threshold=0.5)
    idx.add("a", "1qaz")
    idx.add("b", "1qaz")
    idx.add("c", "qwerty")
    hits = set(idx.query("1qaz"))
    assert {"a", "b"}.issubset(hits)


def test_reversed_segment_pair_clusters_at_threshold_080() -> None:
    """Acceptance criterion #3: reversed-segment pair must cluster at 0.8."""
    idx = StringMinHashIndex(num_perm=256, threshold=0.8)
    idx.add("forward", "1qaz2wsx3edc4rfv")
    idx.add("backward", "4rfv3edc2wsx1qaz")
    hits_forward = set(idx.query("1qaz2wsx3edc4rfv"))
    hits_backward = set(idx.query("4rfv3edc2wsx1qaz"))
    assert {"forward", "backward"}.issubset(hits_forward)
    assert {"forward", "backward"}.issubset(hits_backward)


def test_short_input_skipped() -> None:
    idx = StringMinHashIndex(num_perm=64, threshold=0.5)
    idx.add("short", "x")
    assert "short" not in idx
    assert idx.query("x") == []


def test_minhash_deterministic_across_instances() -> None:
    idx_a = StringMinHashIndex(num_perm=64, threshold=0.5)
    idx_b = StringMinHashIndex(num_perm=64, threshold=0.5)
    idx_a.add("p", "password1")
    idx_b.add("p", "password1")
    sig_a = idx_a._signatures["p"].digest().tolist()
    sig_b = idx_b._signatures["p"].digest().tolist()
    assert sig_a == sig_b


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    idx = StringMinHashIndex(num_perm=64, threshold=0.5)
    idx.add("x", "1qaz2wsx")
    idx.add("y", "abcdefgh")
    out = tmp_path / "string.pkl"
    idx.save(out)
    loaded = StringMinHashIndex.load(out)
    assert loaded.num_perm == 64
    assert loaded.threshold == 0.5
    assert "x" in loaded
    assert "y" in loaded
    assert set(loaded.query("1qaz2wsx")) == set(idx.query("1qaz2wsx"))


def test_disjoint_strings_do_not_cluster() -> None:
    idx = StringMinHashIndex(num_perm=128, threshold=0.8)
    idx.add("walk", "1qaz2wsx3edc4rfv")
    idx.add("random", "Tx7mP$qz")
    hits = set(idx.query("1qaz2wsx3edc4rfv"))
    assert "random" not in hits


def test_suffix_append_clusters_at_low_threshold() -> None:
    idx = StringMinHashIndex(num_perm=128, threshold=0.5)
    idx.add("base", "password")
    idx.add("plus1", "password1")
    hits = set(idx.query("password"))
    assert {"base", "plus1"}.issubset(hits)


def test_duplicate_add_is_idempotent() -> None:
    idx = StringMinHashIndex(num_perm=64, threshold=0.5)
    idx.add("x", "1qaz")
    idx.add("x", "1qaz")
    assert len(idx) == 1
