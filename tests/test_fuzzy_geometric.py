"""Tests for fuzzy/geometric_minhash.py."""

from __future__ import annotations

from typing import TYPE_CHECKING

from keywalk_audit.fuzzy import GeometricMinHashIndex
from keywalk_audit.layouts import QWERTY_US

if TYPE_CHECKING:
    from pathlib import Path

    from keywalk_audit.layouts.base import Layout


def test_index_basic_add_and_query(qwerty_us: Layout) -> None:
    idx = GeometricMinHashIndex(num_perm=128, threshold=0.5)
    idx.add("a", "1qaz", qwerty_us)
    idx.add("b", "1qaz", qwerty_us)
    idx.add("c", "qwerty", qwerty_us)
    hits = set(idx.query("1qaz", qwerty_us))
    assert {"a", "b"}.issubset(hits)


def test_shift_mirror_clusters_with_original(qwerty_us: Layout) -> None:
    """A walk and its shift mirror trace identical paths and must cluster."""
    idx = GeometricMinHashIndex(num_perm=128, threshold=0.8)
    idx.add("plain", "1qazxsw2", qwerty_us)
    idx.add("mirror", "!QAZXSW@", qwerty_us)
    hits_plain = set(idx.query("1qazxsw2", qwerty_us))
    hits_mirror = set(idx.query("!QAZXSW@", qwerty_us))
    assert {"plain", "mirror"}.issubset(hits_plain)
    assert {"plain", "mirror"}.issubset(hits_mirror)


def test_short_input_skipped(qwerty_us: Layout) -> None:
    idx = GeometricMinHashIndex(num_perm=64, threshold=0.5)
    idx.add("short", "1q", qwerty_us)
    assert "short" not in idx
    assert idx.query("1q", qwerty_us) == []


def test_minhash_deterministic_across_instances(qwerty_us: Layout) -> None:
    idx_a = GeometricMinHashIndex(num_perm=64, threshold=0.5)
    idx_b = GeometricMinHashIndex(num_perm=64, threshold=0.5)
    idx_a.add("w", "1qazxsw2", qwerty_us)
    idx_b.add("w", "1qazxsw2", qwerty_us)
    sig_a = idx_a._signatures["w"].digest().tolist()
    sig_b = idx_b._signatures["w"].digest().tolist()
    assert sig_a == sig_b


def test_save_and_load_roundtrip(qwerty_us: Layout, tmp_path: Path) -> None:
    idx = GeometricMinHashIndex(num_perm=64, threshold=0.5)
    idx.add("x", "1qazxsw2", qwerty_us)
    idx.add("y", "qweasdzxc", qwerty_us)
    out = tmp_path / "geom.pkl"
    idx.save(out)
    loaded = GeometricMinHashIndex.load(out)
    assert loaded.num_perm == 64
    assert loaded.threshold == 0.5
    assert "x" in loaded
    assert "y" in loaded
    assert set(loaded.query("1qazxsw2", QWERTY_US)) == set(idx.query("1qazxsw2", QWERTY_US))


def test_duplicate_add_is_idempotent(qwerty_us: Layout) -> None:
    idx = GeometricMinHashIndex(num_perm=64, threshold=0.5)
    idx.add("x", "1qaz", qwerty_us)
    idx.add("x", "1qaz", qwerty_us)
    assert len(idx) == 1


def test_len_and_contains(qwerty_us: Layout) -> None:
    idx = GeometricMinHashIndex(num_perm=64, threshold=0.5)
    assert len(idx) == 0
    assert "missing" not in idx
    idx.add("present", "1qaz", qwerty_us)
    assert len(idx) == 1
    assert "present" in idx
