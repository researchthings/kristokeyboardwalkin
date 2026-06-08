"""Tests for audit/crack.py orchestration (hashcat invocation stubbed)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from keywalk_audit.audit.crack import candidate_plaintexts, crack_hashes
from keywalk_audit.hashing.computer import compute_hash
from keywalk_audit.hashing.hashcat_runner import HashcatResult
from keywalk_audit.layouts import QWERTY_US
from keywalk_audit.rainbow.builder import build_rainbow

if TYPE_CHECKING:
    from pathlib import Path


def _tiny_rainbow(db: Path) -> None:
    build_rainbow(
        layouts=[QWERTY_US],
        lengths=range(4, 5),
        algorithms=("ntlm",),
        db_path=db,
        rebuild=True,
        max_turns=0,
        max_segments=2,
        long_seed_cap=8,
    )


def test_candidate_plaintexts_ordered_and_filtered(tmp_path: Path) -> None:
    db = tmp_path / "rainbow.duckdb"
    _tiny_rainbow(db)
    all_seeds = candidate_plaintexts(db)
    assert all_seeds
    assert "1qaz" in all_seeds
    high = candidate_plaintexts(db, min_score=0.95)
    assert all(s in all_seeds for s in high)
    assert len(high) <= len(all_seeds)
    limited = candidate_plaintexts(db, limit=3)
    assert len(limited) <= 3


def test_candidate_plaintexts_missing_db(tmp_path: Path) -> None:
    assert candidate_plaintexts(tmp_path / "nope.duckdb") == []


def test_crack_hashes_with_stub_runner(tmp_path: Path) -> None:
    db = tmp_path / "rainbow.duckdb"
    _tiny_rainbow(db)
    target = compute_hash("ntlm", "1qaz")
    captured: dict[str, Any] = {}

    def fake_run(**kwargs: Any) -> HashcatResult:
        captured.update(kwargs)
        return HashcatResult(
            cracked={target: "1qaz"},
            runtime_seconds=0.01,
            speed_hashes_per_sec=1.0e6,
            exit_code=0,
        )

    report = crack_hashes(
        {"alice": target, "bob": "ffffffffffffffffffffffffffffffff"},
        db,
        tmp_path / "work",
        algorithm="ntlm",
        hashcat_binary=tmp_path / "fake-hashcat",
        run_hashcat=fake_run,
        mutate=False,
    )
    assert report.hashcat_invoked is True
    assert report.attempted == 2
    assert report.cracked == {target: "1qaz"}
    assert ("alice", "1qaz") in report.accounts_cracked
    assert report.wordlist_size > 0
    assert report.rules_used > 0
    # The rule file was passed to hashcat via -r.
    assert "-r" in captured["extra_args"]


def test_crack_hashes_without_hashcat(tmp_path: Path) -> None:
    """With no binary and none on PATH, the report degrades gracefully."""
    db = tmp_path / "rainbow.duckdb"
    _tiny_rainbow(db)

    report = crack_hashes(
        {"alice": compute_hash("ntlm", "1qaz")},
        db,
        tmp_path / "work",
        hashcat_binary=None,
    )
    # hashcat is not installed in the test environment.
    if not report.hashcat_invoked:
        assert report.errors
        assert report.cracked == {}
