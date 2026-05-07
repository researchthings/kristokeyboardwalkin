# keywalk_audit

Keyboard-walk password audit tool. Detects "walking" patterns in passwords
across QWERTY US, QWERTY UK, QWERTY US-International, and numeric-keypad
layouts; builds a persistent rainbow table of walk candidates with their
hashes; audits SAM dumps (PWDUMP or raw hive) for accounts using walk
passwords; and clusters walk variants and near-miss mutations via geometric
and string MinHash locality-sensitive hashing.

License: MIT.

## Install

```
git clone https://github.com/researchthings/kristokeyboardwalkin
cd kristokeyboardwalkin
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Quickstart

Score a candidate:

```
keywalk-audit score "1qazxsw2!QAZXSW@"
```

Compute its geometric fingerprint:

```
keywalk-audit fingerprint "1qazxsw2"
```

Build a small rainbow table:

```
keywalk-audit build-rainbow \
    --rebuild \
    --layouts qwerty_us \
    --lengths 4-12 \
    --algorithms ntlm,lm \
    --max-turns 2 \
    --db rainbow.duckdb
```

Audit a PWDUMP file:

```
keywalk-audit audit users.pwdump --db rainbow.duckdb --threshold 0.7 \
    --output report.xlsx --format xlsx
```

The audit detects PWDUMP versus raw hive automatically by sniffing the
``regf`` magic bytes. For a hive, pass the SYSTEM hive separately:

```
keywalk-audit audit SAM --system-hive SYSTEM --db rainbow.duckdb
```

## Architecture

- All walk generation, scoring, fingerprinting, fuzzy hashing, SAM ingestion,
  and reporting is pure Python.
- Build-time hash computation for fast hashcat-aligned algorithms (NTLM, LM,
  raw MD5/SHA1/SHA256/SHA512) runs in pure Python so audit-time exact lookups
  are immediate.
- Audit-time cracking of unknown captured hashes is delegated to hashcat as
  a subprocess. The Python tool generates wordlists and invokes hashcat with
  explicit argument lists; it does not reimplement hash kernels.
- Storage backend is DuckDB. Geometric and string MinHash LSH indexes are
  pickled alongside the DuckDB file. The rainbow table is persistent across
  audit runs and rebuilt only when ``--rebuild`` is passed.

See ``docs/ARCHITECTURE.md`` for module-level detail, ``docs/SCORING.md``
for the scoring formulas (with LaTeX), ``docs/FUZZY_HASHING.md`` for the
MinHash/LSH math and the calibrated 1-gram + 2-gram shingling decision,
and ``docs/HASH_MODES.md`` for the hashcat-mode registry, including the
Cisco-type-5 reuse note and the Cisco-type-7 caveat.

## Acceptance criteria (verified)

1. The eight canonical reference walks all score >= 0.7 with the calibrated
   default weights on QWERTY US.
2. The four shift-mirror pairs produce identical geometric fingerprints.
3. The reversed-segment pair (``1qaz2wsx3edc4rfv`` and ``4rfv3edc2wsx1qaz``)
   clusters together in the string MinHash LSH at threshold 0.8.
4. A synthetic PWDUMP with 10 walk-password accounts and 10 random-password
   accounts produces an audit report identifying exactly the 10 walk
   accounts at threshold 0.7.

Run the test suite:

```
pytest --cov=keywalk_audit --cov-report=term-missing
```

## Threshold tuning notes

The default audit threshold is 0.7. Lowering it admits weaker patterns
(simple straight-line walks like ``qwertyui`` score around 0.72; partial
walks score lower). Raising it surfaces only deliberate walk-style
passwords with multiple segments or shift mirrors. Tune empirically
against a representative corpus rather than guessing.

## License

MIT. See ``LICENSE``.
