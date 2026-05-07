"""Audit runner: cross-reference SAM hashes against the rainbow table.

The runner detects the SAM format, iterates entries, and for each one
attempts an exact-hash lookup against the configured algorithms (NTLM by
default, with LM as a secondary). If an exact match is found and the
matched candidate's walk score meets ``threshold``, the runner emits a
finding and decorates it with geometric and string fuzzy clusters from
the saved LSH indexes.

Hashcat-based cracking of unknown captured hashes is intentionally
out of scope for this runner: it is a separate, optional step. The
``hashcat_runner`` module exposes the primitives if a caller wants to
chain it.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from keywalk_audit.layouts import get_layout
from keywalk_audit.rainbow.lookup import (
    Candidate,
    fuzzy_lookup_geometric,
    fuzzy_lookup_string,
    lookup_hash,
)
from keywalk_audit.sam.autodetect import detect_format
from keywalk_audit.sam.hive_parser import parse_hive
from keywalk_audit.sam.pwdump_parser import SamEntry, parse_pwdump

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_ALGOS: tuple[str, ...] = ("ntlm", "lm")


@dataclass(frozen=True)
class AuditFinding:
    """A SAM account whose hash matched a walk-pattern candidate."""

    username: str
    rid: int
    matched_algorithm: str
    plaintext: str
    walk_score: float
    layout: str
    fingerprint: str
    fuzzy_geom_cluster: tuple[str, ...]
    fuzzy_str_cluster: tuple[str, ...]


@dataclass(frozen=True)
class AuditReport:
    """Result of an audit pass over a SAM source."""

    total_accounts: int
    walk_accounts: int
    findings: tuple[AuditFinding, ...]
    threshold: float
    runtime_seconds: float
    errors: tuple[str, ...] = field(default_factory=tuple)


def _iter_entries(
    sam_path: Path,
    sam_hive_path: Path | None,
    system_hive_path: Path | None,
) -> Iterable[SamEntry]:
    fmt = detect_format(sam_path)
    if fmt == "pwdump":
        return parse_pwdump(sam_path)
    if sam_hive_path is None or system_hive_path is None:
        msg = "hive format detected but sam_hive_path and system_hive_path were not supplied"
        raise ValueError(msg)
    return parse_hive(sam_hive_path, system_hive_path)


def _build_finding(
    entry: SamEntry,
    candidate: Candidate,
    matched_algorithm: str,
    db_path: Path,
) -> AuditFinding:
    geom_cluster: tuple[str, ...] = ()
    str_cluster: tuple[str, ...] = ()
    try:
        layout = get_layout(candidate.layout)
        geom_hits = fuzzy_lookup_geometric(db_path, candidate.plaintext, layout)
        geom_cluster = tuple(c.walk_id for c in geom_hits if c.walk_id != candidate.walk_id)
    except (KeyError, OSError):
        logger.exception("geometric fuzzy lookup failed for %s", entry.username)
    try:
        str_hits = fuzzy_lookup_string(db_path, candidate.plaintext)
        str_cluster = tuple(c.walk_id for c in str_hits if c.walk_id != candidate.walk_id)
    except OSError:
        logger.exception("string fuzzy lookup failed for %s", entry.username)
    return AuditFinding(
        username=entry.username,
        rid=entry.rid,
        matched_algorithm=matched_algorithm,
        plaintext=candidate.plaintext,
        walk_score=candidate.score,
        layout=candidate.layout,
        fingerprint=candidate.fingerprint,
        fuzzy_geom_cluster=geom_cluster,
        fuzzy_str_cluster=str_cluster,
    )


def _try_match(
    entry: SamEntry, db_path: Path, algorithms: Sequence[str]
) -> tuple[Candidate, str] | None:
    for algo in algorithms:
        if algo == "ntlm":
            hit = lookup_hash(db_path, "ntlm", entry.nt_hash)
        elif algo == "lm":
            hit = lookup_hash(db_path, "lm", entry.lm_hash)
        else:
            continue
        if hit is not None:
            return hit, algo
    return None


def audit(
    sam_path: Path,
    db_path: Path,
    threshold: float = 0.7,
    *,
    algorithms: Sequence[str] = DEFAULT_ALGOS,
    sam_hive_path: Path | None = None,
    system_hive_path: Path | None = None,
) -> AuditReport:
    """Audit `sam_path` against the rainbow at `db_path`.

    Returns an ``AuditReport``. Findings are produced only when the
    matched candidate's walk score meets ``threshold``.
    """
    start = time.time()
    findings: list[AuditFinding] = []
    errors: list[str] = []
    total = 0

    try:
        entries = list(_iter_entries(sam_path, sam_hive_path, system_hive_path))
    except (OSError, ValueError) as exc:
        return AuditReport(
            total_accounts=0,
            walk_accounts=0,
            findings=(),
            threshold=threshold,
            runtime_seconds=time.time() - start,
            errors=(f"failed to read SAM source: {exc}",),
        )

    for entry in entries:
        total += 1
        try:
            match = _try_match(entry, db_path, algorithms)
        except OSError as exc:
            errors.append(f"{entry.username}: {exc}")
            continue
        if match is None:
            continue
        candidate, algo = match
        if candidate.score < threshold:
            continue
        findings.append(_build_finding(entry, candidate, algo, db_path))

    return AuditReport(
        total_accounts=total,
        walk_accounts=len(findings),
        findings=tuple(findings),
        threshold=threshold,
        runtime_seconds=time.time() - start,
        errors=tuple(errors),
    )
