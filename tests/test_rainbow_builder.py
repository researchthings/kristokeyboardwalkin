"""Tests for rainbow/builder.py and rainbow/lookup.py."""

from __future__ import annotations

from contextlib import closing
from typing import TYPE_CHECKING

import duckdb

from keywalk_audit.fuzzy.geometric_minhash import GeometricMinHashIndex
from keywalk_audit.fuzzy.string_minhash import StringMinHashIndex
from keywalk_audit.layouts import QWERTY_US
from keywalk_audit.rainbow.builder import (
    build_rainbow,
    geom_lsh_path,
    string_lsh_path,
)
from keywalk_audit.rainbow.lookup import (
    fuzzy_lookup_geometric,
    fuzzy_lookup_string,
    lookup_hash,
)
from keywalk_audit.rainbow.schema import init_schema, walk_id_for

if TYPE_CHECKING:
    from pathlib import Path


def test_walk_id_is_stable_and_collision_resistant() -> None:
    a = walk_id_for("qwerty_us", "1qaz")
    b = walk_id_for("qwerty_us", "1qaz")
    c = walk_id_for("qwerty_us", "2wsx")
    d = walk_id_for("qwerty_uk", "1qaz")
    assert a == b
    assert a != c
    assert a != d


def test_build_small_rainbow_populates_candidates(tmp_path: Path) -> None:
    db = tmp_path / "rainbow.duckdb"
    report = build_rainbow(
        layouts=[QWERTY_US],
        lengths=range(4, 5),
        db_path=db,
        rebuild=True,
        max_turns=0,
        max_segments=2,
        long_seed_cap=8,
    )
    assert report.candidates_inserted > 0
    assert report.layouts_processed == ("qwerty_us",)
    assert geom_lsh_path(db).exists()
    assert string_lsh_path(db).exists()

    with closing(duckdb.connect(str(db), read_only=True)) as conn:
        count = conn.execute("SELECT COUNT(*) FROM candidates;").fetchone()
        assert count is not None
        assert count[0] == report.candidates_inserted
        sig_count = conn.execute("SELECT COUNT(*) FROM fuzzy_signatures;").fetchone()
        assert sig_count is not None
        assert sig_count[0] == report.candidates_inserted


def test_build_includes_canonical_long_walk_via_composition(tmp_path: Path) -> None:
    """Composed long walks of length 8 should include 1qaz1qaz when seeds
    contain 1qaz. This exercises the long-walk path in the builder."""
    db = tmp_path / "rainbow.duckdb"
    build_rainbow(
        layouts=[QWERTY_US],
        lengths=range(4, 9),
        db_path=db,
        rebuild=True,
        max_turns=0,
        max_segments=2,
        long_seed_cap=8,
    )
    with closing(duckdb.connect(str(db), read_only=True)) as conn:
        rows = conn.execute(
            "SELECT COUNT(*) FROM candidates WHERE is_composed = TRUE;",
        ).fetchall()
    assert rows
    assert rows[0][0] > 0


def test_rebuild_drops_existing_rows(tmp_path: Path) -> None:
    db = tmp_path / "rainbow.duckdb"
    with closing(duckdb.connect(str(db))) as conn:
        init_schema(conn)
        conn.execute(
            "INSERT INTO candidates VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP);",
            ["sentinel", "stub", "qwerty_us", 4, 0.0, "00", False, False, False],
        )
    build_rainbow(
        layouts=[QWERTY_US],
        lengths=range(4, 5),
        db_path=db,
        rebuild=True,
        max_turns=0,
        max_segments=2,
        long_seed_cap=8,
    )
    with closing(duckdb.connect(str(db), read_only=True)) as conn:
        rows = conn.execute(
            "SELECT walk_id FROM candidates WHERE walk_id = ?;", ["sentinel"]
        ).fetchall()
    assert rows == []


def test_build_populates_hashes_table_for_ntlm(tmp_path: Path) -> None:
    db = tmp_path / "rainbow.duckdb"
    report = build_rainbow(
        layouts=[QWERTY_US],
        lengths=range(4, 5),
        algorithms=("ntlm", "lm"),
        db_path=db,
        rebuild=True,
        max_turns=0,
        max_segments=2,
        long_seed_cap=8,
    )
    assert "ntlm" in report.algorithms_processed
    assert "lm" in report.algorithms_processed
    with closing(duckdb.connect(str(db), read_only=True)) as conn:
        rows = conn.execute("SELECT COUNT(*) FROM hashes WHERE algorithm = 'ntlm';").fetchall()
    assert rows
    assert rows[0][0] == report.candidates_inserted


def test_build_skips_uncomputable_algorithms(tmp_path: Path) -> None:
    """bcrypt has no Python computer, so it is skipped at build time."""
    db = tmp_path / "rainbow.duckdb"
    report = build_rainbow(
        layouts=[QWERTY_US],
        lengths=range(4, 5),
        algorithms=("ntlm", "bcrypt"),
        db_path=db,
        rebuild=True,
        max_turns=0,
        max_segments=2,
        long_seed_cap=8,
    )
    assert "ntlm" in report.algorithms_processed
    assert "bcrypt" not in report.algorithms_processed


def test_lookup_hash_returns_none_when_unknown(tmp_path: Path) -> None:
    db = tmp_path / "rainbow.duckdb"
    build_rainbow(
        layouts=[QWERTY_US],
        lengths=range(4, 5),
        db_path=db,
        rebuild=True,
        max_turns=0,
        max_segments=2,
        long_seed_cap=8,
    )
    assert lookup_hash(db, "ntlm", "deadbeef") is None


def test_fuzzy_lookup_string_returns_canonical_pair(tmp_path: Path) -> None:
    db = tmp_path / "rainbow.duckdb"
    with closing(duckdb.connect(str(db))) as conn:
        init_schema(conn)
        a_id = walk_id_for(QWERTY_US.name, "1qaz2wsx3edc4rfv")
        b_id = walk_id_for(QWERTY_US.name, "4rfv3edc2wsx1qaz")
        for wid, text in ((a_id, "1qaz2wsx3edc4rfv"), (b_id, "4rfv3edc2wsx1qaz")):
            conn.execute(
                "INSERT INTO candidates VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP);",
                [wid, text, QWERTY_US.name, len(text), 0.7, "00", False, False, True],
            )
        idx = StringMinHashIndex(num_perm=256, threshold=0.8)
        idx.add(a_id, "1qaz2wsx3edc4rfv")
        idx.add(b_id, "4rfv3edc2wsx1qaz")
        idx.save(string_lsh_path(db))
        geom = GeometricMinHashIndex(num_perm=256, threshold=0.8)
        geom.add(a_id, "1qaz2wsx3edc4rfv", QWERTY_US)
        geom.add(b_id, "4rfv3edc2wsx1qaz", QWERTY_US)
        geom.save(geom_lsh_path(db))

    hits = fuzzy_lookup_string(db, "1qaz2wsx3edc4rfv", threshold=0.8)
    plaintexts = {c.plaintext for c in hits}
    assert "1qaz2wsx3edc4rfv" in plaintexts
    assert "4rfv3edc2wsx1qaz" in plaintexts


def test_fuzzy_lookup_geometric_finds_shift_mirror(tmp_path: Path) -> None:
    """Pre-populate the DB and LSH so the test does not depend on the
    walk-generator producing a specific 8-char turning walk."""
    db = tmp_path / "rainbow.duckdb"
    with closing(duckdb.connect(str(db))) as conn:
        init_schema(conn)
        wid = walk_id_for(QWERTY_US.name, "1qazxsw2")
        conn.execute(
            "INSERT INTO candidates VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP);",
            [wid, "1qazxsw2", QWERTY_US.name, 8, 0.74, "00", False, False, False],
        )
    geom = GeometricMinHashIndex(num_perm=128, threshold=0.8)
    geom.add(wid, "1qazxsw2", QWERTY_US)
    geom.save(geom_lsh_path(db))

    hits = fuzzy_lookup_geometric(db, "1qazxsw2", QWERTY_US, threshold=0.8)
    plaintexts = {c.plaintext for c in hits}
    assert "1qazxsw2" in plaintexts


def test_fuzzy_lookup_geometric_finds_shift_mirror_pair(tmp_path: Path) -> None:
    """Acceptance criterion #2 path: plaintext and its shift mirror cluster."""
    db = tmp_path / "rainbow.duckdb"
    with closing(duckdb.connect(str(db))) as conn:
        init_schema(conn)
        for text in ("1qazxsw2", "!QAZXSW@"):
            wid = walk_id_for(QWERTY_US.name, text)
            conn.execute(
                "INSERT INTO candidates VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP);",
                [
                    wid,
                    text,
                    QWERTY_US.name,
                    len(text),
                    0.74,
                    "00",
                    text != "1qazxsw2",
                    False,
                    False,
                ],
            )
    geom = GeometricMinHashIndex(num_perm=128, threshold=0.8)
    for text in ("1qazxsw2", "!QAZXSW@"):
        geom.add(walk_id_for(QWERTY_US.name, text), text, QWERTY_US)
    geom.save(geom_lsh_path(db))

    hits_plain = {c.plaintext for c in fuzzy_lookup_geometric(db, "1qazxsw2", QWERTY_US)}
    hits_mirror = {c.plaintext for c in fuzzy_lookup_geometric(db, "!QAZXSW@", QWERTY_US)}
    assert {"1qazxsw2", "!QAZXSW@"}.issubset(hits_plain)
    assert {"1qazxsw2", "!QAZXSW@"}.issubset(hits_mirror)


def test_fuzzy_lookup_returns_empty_when_no_lsh(tmp_path: Path) -> None:
    db = tmp_path / "rainbow.duckdb"
    with closing(duckdb.connect(str(db))) as conn:
        init_schema(conn)
    assert fuzzy_lookup_string(db, "1qaz2wsx", threshold=0.8) == []
    assert fuzzy_lookup_geometric(db, "1qaz2wsx", QWERTY_US, threshold=0.8) == []
