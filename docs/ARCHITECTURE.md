# Architecture

`keywalk_audit` is a Python 3.11+ tool with a layered design. The
top-level package layout mirrors the pipeline: layouts feed walks; walks
feed the scorer, fingerprint, and fuzzy index; the rainbow stores
candidates and hashes; the audit runner crosses captured SAM hashes
against the rainbow.

## Modules

- `keywalk_audit.layouts` defines the `Layout` dataclass and four
  concrete layouts (`qwerty_us`, `qwerty_uk`, `qwerty_intl`, `numpad`).
  Each layout maps characters to a `(row, col)` grid where columns align
  across rows so vertical walks (e.g. `1qaz`) score correctly.
- `keywalk_audit.walks` contains four submodules:
  - `variants.py` derives the shift mirror, character reversal, and the
    full variant set of a plaintext.
  - `scorer.py` computes the six-feature walk score with calibrated
    weights.
  - `fingerprint.py` computes a BLAKE2b-128 hex digest over the unit-
    clipped direction-vector sequence. Shift mirrors and the original
    plaintext share the same physical-key path and therefore the same
    fingerprint.
  - `generator.py` provides a streaming DFS short-walk generator and a
    long-walk composer that concatenates 2..max_segments shorts.
- `keywalk_audit.fuzzy` exposes two MinHash LSH indexes: a geometric
  index over direction-vector shingles and a string index over plaintext
  character n-grams. Both index at a permissive LSH threshold (0.4) and
  re-rank candidates with exact MinHash Jaccard so the configured
  threshold is honoured despite the LSH banding approximation.
- `keywalk_audit.hashing` registers hashcat algorithm modes, computes
  fast hashes in pure Python at build time, and orchestrates hashcat as
  a subprocess for audit-time cracking.
- `keywalk_audit.sam` parses PWDUMP files, wraps impacket's
  `LocalOperations` and `SAMHashes` for raw SAM/SYSTEM hives, and
  autodetects format via the ``regf`` magic bytes.
- `keywalk_audit.rainbow` defines the DuckDB schema, the streaming
  builder, and the lookup helpers. The builder generates short walks,
  emits each variant, composes long walks from a capped seed set,
  computes hashes, and batch-inserts every 1000 rows into DuckDB.
- `keywalk_audit.audit` runs the pipeline end to end: parse SAM, look
  up each entry's NT and LM hashes against the rainbow, decorate
  matched candidates with fuzzy clusters, and produce JSON or XLSX
  reports.

## Data flow

```
SAM source --autodetect--> PWDUMP|hive parser --> SamEntry stream
                                                           |
rainbow (DuckDB) --lookup_hash on (algorithm, hash)--> Candidate
                                                           |
                                                  AuditFinding decoration:
                                                  fuzzy_lookup_geometric
                                                  fuzzy_lookup_string
                                                           |
                                                       AuditReport --> JSON / XLSX
```

## Storage

The DuckDB file holds three tables:

- `candidates(walk_id PK, plaintext, layout, length, score, fingerprint,
  is_shift_mirror, is_reversal, is_composed, created_at)`
- `hashes(walk_id, algorithm, hash_value, PRIMARY KEY (walk_id,
  algorithm))`
- `fuzzy_signatures(walk_id PK, geom_signature BLOB, str_signature BLOB)`

Two pickle files live alongside the DuckDB file:
``<db>.geom.pkl`` and ``<db>.str.pkl``. They hold serialized
`MinHashLSH` indexes that are loaded for fuzzy queries.

`walk_id` is BLAKE2b-12 hex over ``layout_name + ":" + plaintext`` for
stability across runs.

## Concurrency

Walk generation is CPU-bound. The builder accepts a `workers` parameter
that is reserved for `concurrent.futures.ProcessPoolExecutor` shards;
the present implementation is single-process for clarity and is
sufficient for typical lengths up to 16 with bounded `max_turns`. Long
walk composition is intentionally cap-controlled by `long_seed_cap`
because the cross product grows as `n ** max_segments`.

## Subprocess discipline

Hashcat invocations build an explicit `list[str]` argv and pass it to
`subprocess.run` with `shell=False` (the default). Hashcat versions
older than 6.2.0 are rejected. Non-zero exit codes other than 1 (which
hashcat uses for "no crack") raise `HashcatExecutionError` with stderr
embedded in the message.
