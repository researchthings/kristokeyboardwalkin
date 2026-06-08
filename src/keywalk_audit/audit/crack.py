"""Audit-time cracking orchestration for hashes that miss the rainbow table.

The rainbow table answers exact lookups instantly for the fast algorithms it
materializes. Hashes that are not found there -- a different algorithm, or a
walk derivative the build did not enumerate -- are handed to hashcat. This
module assembles the attack: it reads the rainbow's candidate plaintexts as a
seed wordlist, optionally expands them through the walk-mutation engine, writes
a hashcat rule file, and invokes hashcat against the target hashes.

The hashcat invocation is injected (``run_hashcat``) so the orchestration is
unit-testable without the binary present, mirroring the builder's design.
"""

from __future__ import annotations

import time
from contextlib import closing
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import duckdb

from keywalk_audit.hashing.algorithms import get_algo
from keywalk_audit.hashing.hashcat_runner import (
    HashcatExecutionError,
    HashcatNotFoundError,
    HashcatResult,
    HashcatVersionError,
    detect_hashcat,
)
from keywalk_audit.hashing.hashcat_runner import run_hashcat as _default_run_hashcat
from keywalk_audit.hashing.mutations import DEFAULT_RULES, expand_wordlist, write_rule_file

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence
    from pathlib import Path


@dataclass(frozen=True)
class CrackReport:
    """Outcome of an audit-time hashcat crack of unmatched hashes."""

    attempted: int
    cracked: dict[str, str]
    accounts_cracked: tuple[tuple[str, str], ...]
    wordlist_size: int
    rules_used: int
    hashcat_invoked: bool
    runtime_seconds: float
    errors: tuple[str, ...] = field(default_factory=tuple)


def candidate_plaintexts(
    db_path: Path,
    *,
    min_score: float = 0.0,
    limit: int | None = None,
) -> list[str]:
    """Return rainbow candidate plaintexts scoring at least ``min_score``.

    Highest-scored candidates come first so a truncating ``limit`` keeps the
    most walk-like seeds. Returns an empty list when the database is absent.
    """
    if not db_path.exists():
        return []
    query = "SELECT plaintext FROM candidates WHERE score >= ? ORDER BY score DESC, plaintext"
    params: list[object] = [min_score]
    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)
    with closing(duckdb.connect(str(db_path), read_only=True)) as conn:
        rows = conn.execute(query, params).fetchall()
    return [str(row[0]) for row in rows]


def crack_hashes(
    target_hashes: Mapping[str, str],
    db_path: Path,
    work_dir: Path,
    *,
    algorithm: str = "ntlm",
    hashcat_binary: Path | None = None,
    run_hashcat: Callable[..., HashcatResult] = _default_run_hashcat,
    mutate: bool = True,
    min_score: float = 0.0,
    candidate_limit: int | None = None,
    rules: Sequence[str] = DEFAULT_RULES,
    timeout_seconds: int | None = None,
) -> CrackReport:
    """Crack ``target_hashes`` (id -> hex hash) with hashcat seeded by the rainbow.

    A seed wordlist is drawn from the rainbow candidates, optionally expanded by
    the walk-mutation engine, and paired with a hashcat rule file. When hashcat
    is not installed the report is returned with ``hashcat_invoked=False`` and an
    explanatory error rather than raising.
    """
    start = time.time()
    work_dir.mkdir(parents=True, exist_ok=True)
    unique_hashes = sorted({h.lower() for h in target_hashes.values() if h})

    seeds = candidate_plaintexts(db_path, min_score=min_score, limit=candidate_limit)
    wordlist_path = work_dir / "wordlist.txt"
    wordlist_size = expand_wordlist(seeds, wordlist_path, mutate=mutate)
    rule_path = work_dir / "walk.rule"
    rules_used = write_rule_file(rules, rule_path)

    hash_file = work_dir / "targets.hash"
    hash_file.write_text(
        "\n".join(unique_hashes) + ("\n" if unique_hashes else ""), encoding="utf-8"
    )
    potfile = work_dir / "keywalk.potfile"

    errors: list[str] = []
    try:
        binary = hashcat_binary if hashcat_binary is not None else detect_hashcat()
    except HashcatNotFoundError as exc:
        return CrackReport(
            attempted=len(unique_hashes),
            cracked={},
            accounts_cracked=(),
            wordlist_size=wordlist_size,
            rules_used=rules_used,
            hashcat_invoked=False,
            runtime_seconds=time.time() - start,
            errors=(f"hashcat unavailable: {exc}",),
        )

    cracked: dict[str, str] = {}
    invoked = False
    if unique_hashes and wordlist_size > 0:
        mode = get_algo(algorithm).hashcat_mode
        try:
            result = run_hashcat(
                binary=binary,
                mode=mode,
                hash_file=hash_file,
                wordlist=wordlist_path,
                potfile=potfile,
                extra_args=("-r", str(rule_path)),
                timeout_seconds=timeout_seconds,
            )
            invoked = True
            cracked = dict(result.cracked)
        except (HashcatExecutionError, HashcatVersionError) as exc:
            errors.append(f"hashcat error: {exc}")

    accounts = tuple(
        (account, cracked[h.lower()])
        for account, h in sorted(target_hashes.items())
        if h and h.lower() in cracked
    )
    return CrackReport(
        attempted=len(unique_hashes),
        cracked=cracked,
        accounts_cracked=accounts,
        wordlist_size=wordlist_size,
        rules_used=rules_used,
        hashcat_invoked=invoked,
        runtime_seconds=time.time() - start,
        errors=tuple(errors),
    )
