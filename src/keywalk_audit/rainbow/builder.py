"""Rainbow-table builder: streaming walk generation, scoring, and persistence.

Phase 3 populates the ``candidates`` and ``fuzzy_signatures`` tables and
saves geometric / string MinHash LSH indexes alongside the DuckDB file.
The ``hashes`` table is populated in Phase 4 by invoking hashcat against
generated wordlists.
"""

from __future__ import annotations

import logging
import pickle
import time
from collections.abc import Callable
from contextlib import closing
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import duckdb

from keywalk_audit.fuzzy.geometric_minhash import GeometricMinHashIndex
from keywalk_audit.fuzzy.string_minhash import StringMinHashIndex
from keywalk_audit.hashing.algorithms import HASHCAT_MODES
from keywalk_audit.hashing.computer import can_compute, compute_hash
from keywalk_audit.rainbow.schema import drop_schema, init_schema, walk_id_for
from keywalk_audit.walks.fingerprint import geometric_fingerprint
from keywalk_audit.walks.generator import generate_walks_long, generate_walks_short
from keywalk_audit.walks.scorer import score_walk
from keywalk_audit.walks.variants import reversal, shift_mirror

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from keywalk_audit.layouts.base import Layout

logger = logging.getLogger(__name__)

BATCH_SIZE = 1000
DEFAULT_MAX_TURNS = 4
DEFAULT_MAX_SEGMENTS = 3
DEFAULT_LONG_SEED_CAP = 256

HashcatRunner = Callable[..., object]


@dataclass(frozen=True)
class RainbowBuildReport:
    """Summary of a rainbow-table build run."""

    candidates_inserted: int
    fingerprints_unique: int
    layouts_processed: tuple[str, ...]
    algorithms_processed: tuple[str, ...]
    hashcat_runs: int
    runtime_seconds: float
    errors: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class _CandidateRow:
    walk_id: str
    plaintext: str
    layout: str
    length: int
    score: float
    fingerprint: str
    is_shift_mirror: bool
    is_reversal: bool
    is_composed: bool


def geom_lsh_path(db_path: Path) -> Path:
    return db_path.with_suffix(db_path.suffix + ".geom.pkl")


def string_lsh_path(db_path: Path) -> Path:
    return db_path.with_suffix(db_path.suffix + ".str.pkl")


def _stream_candidates(
    layout: Layout,
    lengths: range,
    max_turns: int,
    max_segments: int,
    long_seed_cap: int,
) -> Iterator[_CandidateRow]:
    if not lengths:
        return
    min_len = min(lengths)
    max_len = max(lengths)
    if min_len < 2 or max_len < min_len:
        return

    seen: set[str] = set()

    def _yield(text: str, is_mirror: bool, is_rev: bool, is_composed: bool) -> _CandidateRow | None:
        if text in seen or len(text) not in lengths:
            return None
        seen.add(text)
        score = score_walk(text, layout)
        fp = geometric_fingerprint(text, layout)
        return _CandidateRow(
            walk_id=walk_id_for(layout.name, text),
            plaintext=text,
            layout=layout.name,
            length=len(text),
            score=score.total,
            fingerprint=fp,
            is_shift_mirror=is_mirror,
            is_reversal=is_rev,
            is_composed=is_composed,
        )

    short_seeds: list[str] = []
    for short in generate_walks_short(
        layout, min_len=min_len, max_len=max_len, max_turns=max_turns
    ):
        for text, mirror, rev in (
            (short, False, False),
            (shift_mirror(short, layout), True, False),
            (reversal(short), False, True),
            (shift_mirror(reversal(short), layout), True, True),
        ):
            row = _yield(text, mirror, rev, is_composed=False)
            if row is not None:
                yield row
        short_seeds.append(short)

    if not short_seeds or max_segments < 2:
        return
    sized_seeds = sorted({s for s in short_seeds if len(s) >= min_len}, key=len)[:long_seed_cap]
    for composed in generate_walks_long(
        layout, sized_seeds, max_len=max_len, max_segments=max_segments
    ):
        row = _yield(composed, is_mirror=False, is_rev=False, is_composed=True)
        if row is not None:
            yield row


def _flush_candidates(
    conn: duckdb.DuckDBPyConnection,
    rows: list[_CandidateRow],
    signatures: list[tuple[str, bytes, bytes]],
) -> None:
    if rows:
        conn.executemany(
            """
            INSERT INTO candidates
                (walk_id, plaintext, layout, length, score, fingerprint,
                 is_shift_mirror, is_reversal, is_composed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (walk_id) DO NOTHING;
            """,
            [
                (
                    r.walk_id,
                    r.plaintext,
                    r.layout,
                    r.length,
                    r.score,
                    r.fingerprint,
                    r.is_shift_mirror,
                    r.is_reversal,
                    r.is_composed,
                )
                for r in rows
            ],
        )
    if signatures:
        conn.executemany(
            """
            INSERT INTO fuzzy_signatures (walk_id, geom_signature, str_signature)
            VALUES (?, ?, ?)
            ON CONFLICT (walk_id) DO NOTHING;
            """,
            signatures,
        )


def build_rainbow(
    layouts: Sequence[Layout],
    lengths: range = range(4, 33),
    algorithms: Sequence[str] = ("ntlm", "lm"),
    db_path: Path = Path("rainbow.duckdb"),
    rebuild: bool = False,
    fast_only: bool = False,
    workers: int | None = None,
    hashcat_binary: Path | None = None,
    *,
    run_hashcat: HashcatRunner | None = None,
    geom_threshold: float = 0.8,
    string_threshold: float = 0.8,
    num_perm: int = 128,
    max_turns: int = DEFAULT_MAX_TURNS,
    max_segments: int = DEFAULT_MAX_SEGMENTS,
    long_seed_cap: int = DEFAULT_LONG_SEED_CAP,
) -> RainbowBuildReport:
    """Build (or rebuild) the rainbow table at `db_path`.

    Hash computation for fast, hashcat-aligned algorithms (NTLM, LM, raw
    MD5/SHA1/SHA256/SHA512) runs in pure Python at build time so that
    audit-time exact lookups are immediate. Slow algorithms (bcrypt,
    scrypt, crypt-family) are not materialized in the rainbow table; for
    those, audit-time hashcat invocations against the candidate wordlist
    do the cracking.

    The ``run_hashcat`` and ``hashcat_binary`` parameters are accepted for
    API stability and are unused at build time. They are consumed by the
    audit runner when cracking unknown captured hashes.
    """
    _ = workers, hashcat_binary, run_hashcat
    start = time.time()
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    requested_algos = _select_algorithms(algorithms, fast_only=fast_only)

    geom_idx = GeometricMinHashIndex(num_perm=num_perm, threshold=geom_threshold)
    string_idx = StringMinHashIndex(num_perm=num_perm, threshold=string_threshold)

    candidates_inserted = 0
    fingerprints: set[str] = set()
    layouts_done: list[str] = []
    errors: list[str] = []

    with closing(duckdb.connect(str(db_path))) as conn:
        if rebuild:
            drop_schema(conn)
        init_schema(conn)

        for layout in layouts:
            logger.info("building rainbow for layout %s", layout.name)
            row_buffer: list[_CandidateRow] = []
            sig_buffer: list[tuple[str, bytes, bytes]] = []
            hash_buffer: list[tuple[str, str, str]] = []
            try:
                for row in _stream_candidates(
                    layout=layout,
                    lengths=lengths,
                    max_turns=max_turns,
                    max_segments=max_segments,
                    long_seed_cap=long_seed_cap,
                ):
                    fingerprints.add(row.fingerprint)
                    geom_idx.add(row.walk_id, row.plaintext, layout)
                    string_idx.add(row.walk_id, row.plaintext)
                    geom_sig = pickle.dumps(
                        geom_idx._signatures.get(row.walk_id),
                        protocol=pickle.HIGHEST_PROTOCOL,
                    )
                    str_sig = pickle.dumps(
                        string_idx._signatures.get(row.walk_id),
                        protocol=pickle.HIGHEST_PROTOCOL,
                    )
                    row_buffer.append(row)
                    sig_buffer.append((row.walk_id, geom_sig, str_sig))
                    for algo in requested_algos:
                        hash_buffer.append((row.walk_id, algo, compute_hash(algo, row.plaintext)))
                    if len(row_buffer) >= BATCH_SIZE:
                        _flush_candidates(conn, row_buffer, sig_buffer)
                        _flush_hashes(conn, hash_buffer)
                        candidates_inserted += len(row_buffer)
                        row_buffer.clear()
                        sig_buffer.clear()
                        hash_buffer.clear()
                if row_buffer:
                    _flush_candidates(conn, row_buffer, sig_buffer)
                    _flush_hashes(conn, hash_buffer)
                    candidates_inserted += len(row_buffer)
                layouts_done.append(layout.name)
            except duckdb.Error as exc:
                errors.append(f"{layout.name}: {exc}")
                logger.exception("layout %s failed", layout.name)

    geom_idx.save(geom_lsh_path(db_path))
    string_idx.save(string_lsh_path(db_path))

    runtime = time.time() - start
    return RainbowBuildReport(
        candidates_inserted=candidates_inserted,
        fingerprints_unique=len(fingerprints),
        layouts_processed=tuple(layouts_done),
        algorithms_processed=tuple(requested_algos),
        hashcat_runs=0,
        runtime_seconds=runtime,
        errors=tuple(errors),
    )


def _select_algorithms(algorithms: Sequence[str], *, fast_only: bool) -> list[str]:
    """Return the requested algorithms restricted to ones we can compute.

    Unknown algorithms are silently skipped with a warning. Slow algorithms
    are skipped when ``fast_only`` is True.
    """
    selected: list[str] = []
    for name in algorithms:
        algo = HASHCAT_MODES.get(name)
        if algo is None:
            logger.warning("unknown algorithm %r; skipping", name)
            continue
        if fast_only and not algo.is_fast:
            logger.info("fast_only set; skipping slow algorithm %s", name)
            continue
        if not can_compute(name):
            logger.info(
                "skipping %s at build time; no Python computer "
                "(audit-time hashcat handles this algorithm)",
                name,
            )
            continue
        selected.append(name)
    return selected


def _flush_hashes(
    conn: duckdb.DuckDBPyConnection,
    rows: list[tuple[str, str, str]],
) -> None:
    if not rows:
        return
    conn.executemany(
        """
        INSERT INTO hashes (walk_id, algorithm, hash_value)
        VALUES (?, ?, ?)
        ON CONFLICT (walk_id, algorithm) DO NOTHING;
        """,
        rows,
    )
