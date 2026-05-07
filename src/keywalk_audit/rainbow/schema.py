"""DuckDB schema for the rainbow table and the walk-id derivation."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import duckdb


CANDIDATES_DDL = """
CREATE TABLE IF NOT EXISTS candidates (
    walk_id         VARCHAR PRIMARY KEY,
    plaintext       VARCHAR NOT NULL,
    layout          VARCHAR NOT NULL,
    length          INTEGER NOT NULL,
    score           DOUBLE  NOT NULL,
    fingerprint     VARCHAR NOT NULL,
    is_shift_mirror BOOLEAN NOT NULL,
    is_reversal     BOOLEAN NOT NULL,
    is_composed     BOOLEAN NOT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CANDIDATES_INDEXES = (
    "CREATE INDEX IF NOT EXISTS idx_candidates_fingerprint ON candidates(fingerprint);",
    "CREATE INDEX IF NOT EXISTS idx_candidates_score ON candidates(score);",
)

HASHES_DDL = """
CREATE TABLE IF NOT EXISTS hashes (
    walk_id    VARCHAR NOT NULL,
    algorithm  VARCHAR NOT NULL,
    hash_value VARCHAR NOT NULL,
    PRIMARY KEY (walk_id, algorithm),
    FOREIGN KEY (walk_id) REFERENCES candidates(walk_id)
);
"""

HASHES_INDEXES = (
    "CREATE INDEX IF NOT EXISTS idx_hashes_value ON hashes(hash_value);",
    "CREATE INDEX IF NOT EXISTS idx_hashes_algo_value ON hashes(algorithm, hash_value);",
)

FUZZY_SIGNATURES_DDL = """
CREATE TABLE IF NOT EXISTS fuzzy_signatures (
    walk_id        VARCHAR PRIMARY KEY,
    geom_signature BLOB    NOT NULL,
    str_signature  BLOB    NOT NULL,
    FOREIGN KEY (walk_id) REFERENCES candidates(walk_id)
);
"""


def init_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """Create all tables and indexes if they don't already exist."""
    conn.execute(CANDIDATES_DDL)
    for stmt in CANDIDATES_INDEXES:
        conn.execute(stmt)
    conn.execute(HASHES_DDL)
    for stmt in HASHES_INDEXES:
        conn.execute(stmt)
    conn.execute(FUZZY_SIGNATURES_DDL)


def drop_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """Drop the rainbow tables. Used by `--rebuild`."""
    conn.execute("DROP TABLE IF EXISTS hashes;")
    conn.execute("DROP TABLE IF EXISTS fuzzy_signatures;")
    conn.execute("DROP TABLE IF EXISTS candidates;")


def walk_id_for(layout_name: str, plaintext: str) -> str:
    """Stable, collision-resistant ID for a (layout, plaintext) candidate.

    BLAKE2b-12 over ``layout_name + ":" + plaintext`` gives a 24-char hex
    string that is short enough for compact storage and large enough to
    avoid collisions across realistic rainbow-table sizes.
    """
    h = hashlib.blake2b(
        f"{layout_name}:{plaintext}".encode(),
        digest_size=12,
    )
    return h.hexdigest()
