"""Rainbow table: DuckDB-backed candidate, hash, and fuzzy-signature storage."""

from __future__ import annotations

from keywalk_audit.rainbow.builder import RainbowBuildReport, build_rainbow
from keywalk_audit.rainbow.lookup import (
    Candidate,
    fuzzy_lookup_geometric,
    fuzzy_lookup_string,
    lookup_hash,
)
from keywalk_audit.rainbow.schema import (
    CANDIDATES_DDL,
    FUZZY_SIGNATURES_DDL,
    HASHES_DDL,
    init_schema,
    walk_id_for,
)

__all__ = [
    "CANDIDATES_DDL",
    "FUZZY_SIGNATURES_DDL",
    "HASHES_DDL",
    "Candidate",
    "RainbowBuildReport",
    "build_rainbow",
    "fuzzy_lookup_geometric",
    "fuzzy_lookup_string",
    "init_schema",
    "lookup_hash",
    "walk_id_for",
]
