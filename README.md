# keywalk_audit

Keyboard-walk password audit tool. It detects "walking" patterns in
passwords across nine layouts — QWERTY US / UK / US-International, German
QWERTZ, French AZERTY, Dvorak, Colemak, the numeric keypad, and the
telephone keypad — scoring each candidate, fingerprinting its physical
path, and clustering variants and near-miss mutations via geometric and
string MinHash locality-sensitive hashing. It builds a persistent rainbow
table of walk candidates with their hashes (optionally seeded with
structural patterns: famous walks, sweeps, zig-zags, number↔letter
interleaves, doublings, and shift-doubled compounds), audits
SAM dumps (PWDUMP or raw hive) for accounts using walk passwords, and can
hand unmatched hashes to hashcat with a walk-aware mutation rule set.

Additional tooling: deep per-candidate analysis (physical travel,
hand/finger dynamics, repeats, automatic layout identification, walk
guessability); a from-scratch MD4 plus ten generic raw hash modes that
build in pure Python; a Cisco IOS Type-7 decoder; and audit reports in
JSON, XLSX, CSV, HTML, Markdown, SARIF, or console form.

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

Run the deep analysis and let the tool pick the layout:

```
keywalk-audit analyze "azerty123" --auto
```

List the layouts and the hash-algorithm registry:

```
keywalk-audit layouts
keywalk-audit algorithms
```

Decode a Cisco IOS Type-7 password:

```
keywalk-audit decode-cisco7 02050D480809
```

Build a small rainbow table:

```
keywalk-audit build-rainbow \
    --rebuild \
    --layouts qwerty_us \
    --lengths 4-12 \
    --algorithms ntlm,lm \
    --max-turns 2 \
    --patterns \
    --db rainbow.duckdb
```

``--patterns`` also materializes the structural patterns (famous walks,
sweeps, zig-zags, number↔letter interleaves, doublings). ``--shift-doublings``
adds the ``(base*k)+(shift(base)*k)`` compound family (e.g.
``1a0k1a0k!A)K!A)K``) and ``--knight`` adds knight-move skip walks; both imply
``--patterns``.

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

Write the report in several formats at once, or render it on the console:

```
keywalk-audit audit users.pwdump --db rainbow.duckdb --output report --format all
keywalk-audit audit users.pwdump --db rainbow.duckdb --format console
```

Generate a walk wordlist, and crack unmatched hashes with hashcat seeded by
the rainbow candidates and the walk-mutation rules:

```
keywalk-audit generate --layout qwerty_us --lengths 4-8 --patterns --output walks.txt
keywalk-audit crack users.pwdump --db rainbow.duckdb --algorithm ntlm --mutate
```

## Commands

| command | purpose |
|---------|---------|
| `score` | calibrated walk score (adjacency + structural sub-scores) for a string |
| `analyze` | deep analysis (physical/finger/repeat metrics, layout ID) |
| `fingerprint` | geometric fingerprint of a walk's physical path |
| `fuzzy` | fuzzy lookup against the saved LSH indexes |
| `layouts` | list registered keyboard layouts |
| `algorithms` | list the hash-algorithm registry |
| `generate` | emit walks (and mutations) as a wordlist |
| `build-rainbow` | build/rebuild the rainbow table |
| `audit` | audit a SAM dump and write a report |
| `crack` | hashcat-crack unmatched hashes, rainbow-seeded |
| `mutations` | inspect mutation rules, masks, and sample expansions |
| `decode-cisco7` / `encode-cisco7` | Cisco IOS Type-7 codec |
| `render` | re-render a saved JSON report into another format |

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
Cisco-type-5 reuse note and the Cisco-type-7 decoder. Further detail lives
in ``docs/LAYOUTS.md`` (the two-layer geometric model and the nine
layouts), ``docs/PATTERNS.md`` (structural walk generators),
``docs/ANALYSIS.md`` (deep analysis and layout identification),
``docs/MUTATIONS.md`` (the mutation engine and audit-time cracking), and
``docs/REPORTING.md`` (the output formats).

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
