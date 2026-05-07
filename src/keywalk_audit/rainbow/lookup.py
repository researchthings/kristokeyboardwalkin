"""Rainbow-table lookup: exact-by-hash and fuzzy-by-MinHash queries."""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import duckdb

from keywalk_audit.fuzzy.geometric_minhash import GeometricMinHashIndex
from keywalk_audit.fuzzy.string_minhash import StringMinHashIndex
from keywalk_audit.rainbow.builder import geom_lsh_path, string_lsh_path

if TYPE_CHECKING:
    from pathlib import Path

    from keywalk_audit.layouts.base import Layout


@dataclass(frozen=True)
class Candidate:
    """A row from the candidates table."""

    walk_id: str
    plaintext: str
    layout: str
    length: int
    score: float
    fingerprint: str
    is_shift_mirror: bool
    is_reversal: bool
    is_composed: bool


def _row_to_candidate(row: tuple[Any, ...]) -> Candidate:
    return Candidate(
        walk_id=str(row[0]),
        plaintext=str(row[1]),
        layout=str(row[2]),
        length=int(row[3]),
        score=float(row[4]),
        fingerprint=str(row[5]),
        is_shift_mirror=bool(row[6]),
        is_reversal=bool(row[7]),
        is_composed=bool(row[8]),
    )


def _select_candidates_by_walk_ids(
    conn: duckdb.DuckDBPyConnection, walk_ids: list[str]
) -> list[Candidate]:
    if not walk_ids:
        return []
    placeholders = ",".join(["?"] * len(walk_ids))
    rows = conn.execute(
        "SELECT walk_id, plaintext, layout, length, score, fingerprint, "
        "is_shift_mirror, is_reversal, is_composed FROM candidates "
        f"WHERE walk_id IN ({placeholders});",
        walk_ids,
    ).fetchall()
    return [_row_to_candidate(r) for r in rows]


def lookup_hash(db_path: Path, algorithm: str, hash_value: str) -> Candidate | None:
    """Return the candidate whose hash matches, or None.

    When multiple candidates share a hash (e.g., LM truncates to 14 chars),
    the highest-scored candidate is returned.
    """
    with closing(duckdb.connect(str(db_path), read_only=True)) as conn:
        rows = conn.execute(
            """
            SELECT c.walk_id, c.plaintext, c.layout, c.length, c.score,
                   c.fingerprint, c.is_shift_mirror, c.is_reversal, c.is_composed
            FROM hashes h
            JOIN candidates c USING (walk_id)
            WHERE h.algorithm = ? AND h.hash_value = ?
            ORDER BY c.score DESC, c.length ASC
            LIMIT 1;
            """,
            [algorithm, hash_value],
        ).fetchall()
    if not rows:
        return None
    return _row_to_candidate(rows[0])


def fuzzy_lookup_geometric(
    db_path: Path,
    plaintext: str,
    layout: Layout,
    threshold: float = 0.8,
) -> list[Candidate]:
    """Return candidates whose geometric signature is similar to `plaintext`."""
    lsh_path = geom_lsh_path(db_path)
    if not lsh_path.exists():
        return []
    idx = GeometricMinHashIndex.load(lsh_path)
    if idx.threshold != threshold:
        # Rebuild a temp index at the requested threshold via re-rank only:
        # the LSH candidate set is permissive, so we set threshold and re-query.
        idx._threshold = threshold
    walk_ids = idx.query(plaintext, layout)
    if not walk_ids:
        return []
    with closing(duckdb.connect(str(db_path), read_only=True)) as conn:
        return _select_candidates_by_walk_ids(conn, walk_ids)


def fuzzy_lookup_string(
    db_path: Path,
    plaintext: str,
    threshold: float = 0.8,
) -> list[Candidate]:
    """Return candidates whose string signature is similar to `plaintext`."""
    lsh_path = string_lsh_path(db_path)
    if not lsh_path.exists():
        return []
    idx = StringMinHashIndex.load(lsh_path)
    if idx.threshold != threshold:
        idx._threshold = threshold
    walk_ids = idx.query(plaintext)
    if not walk_ids:
        return []
    with closing(duckdb.connect(str(db_path), read_only=True)) as conn:
        return _select_candidates_by_walk_ids(conn, walk_ids)
