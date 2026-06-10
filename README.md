# keywalk_audit

Keyboard-walk password audit tool. It finds "walking" passwords (sequences
typed along adjacent keys, like `1qaz2wsx` or `qwerty`) across nine keyboard
layouts, scores each candidate, fingerprints its physical path, and clusters
related variants with MinHash locality-sensitive hashing. It builds a
persistent lookup table of walk plaintexts paired with their hashes, audits
SAM or PWDUMP dumps for accounts using walk passwords, and hands anything
unmatched to hashcat with a walk-aware mutation rule set.

Supported layouts: QWERTY US / UK / US-International, German QWERTZ, French
AZERTY, Dvorak, Colemak, the numeric keypad, and the telephone keypad.

License: MIT.

## How it works

1. **Build** a table of keyboard-walk candidate plaintexts (depth-first
   adjacency walks plus optional structural patterns: famous walks,
   row/column sweeps, zig-zags, number-to-letter interleaves, doublings,
   shift-mirrors, shift-doubled compounds, knight moves). For each candidate
   the NTLM and LM hashes (and the other fast hashes) are computed in pure
   Python and stored in DuckDB alongside the plaintext.
2. **Audit** a dump by looking up each account's NT and LM hash in that table.
   A hit recovers the plaintext directly and confirms it is a walk scoring at
   or above the threshold. This is a precomputed lookup (direct hash
   equality), not chained rainbow tables with reduction functions.
3. **Crack** the leftovers (walk derivatives the build did not enumerate, or
   slow hash types) by handing them to hashcat, seeded with the walk
   candidates as a wordlist and expanded through the mutation engine.

It only surfaces walk-shaped passwords. A random strong password is never in
the table and the mutation engine will not reach it.

## Install

```
git clone https://github.com/researchthings/kristokeyboardwalkin
cd kristokeyboardwalkin
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Requires Python 3.11 or newer. Raw SAM hive parsing uses impacket (installed
automatically). Audit-time cracking requires hashcat 6.2.0 or newer on PATH
(optional; the audit lookup path does not need it).

## Commands

| command | purpose |
|---------|---------|
| `score` | calibrated walk score for a string |
| `analyze` | deep analysis (physical, finger, repeat metrics, layout ID) |
| `fingerprint` | geometric fingerprint of a walk's physical path |
| `fuzzy` | fuzzy lookup against the saved LSH indexes |
| `layouts` | list the registered keyboard layouts |
| `algorithms` | list the hash-algorithm registry |
| `generate` | emit walks (and mutations) as a wordlist |
| `build-rainbow` | build or rebuild the lookup table |
| `audit` | audit a SAM dump and write a report |
| `crack` | hashcat-crack unmatched hashes, seeded by the table |
| `mutations` | inspect mutation rules, masks, and sample expansions |
| `decode-cisco7` / `encode-cisco7` | Cisco IOS Type-7 codec |
| `render` | re-render a saved JSON report into another format |

## Examples by scenario

### Inspect a single candidate

```
keywalk-audit score "1qazxsw2!QAZXSW@"
keywalk-audit analyze "azerty123" --auto        # detect the best-fitting layout
keywalk-audit fingerprint "1qaz2wsx"
```

`score` prints the sub-score breakdown. `analyze` adds physical travel, hand
and finger dynamics, repeat structure, and a top-five layout ranking; `--auto`
analyzes against the winning layout.

### List what is registered

```
keywalk-audit layouts
keywalk-audit algorithms
```

### Build the lookup table

```
# Baseline depth-first walks, QWERTY US, NTLM + LM
keywalk-audit build-rainbow --rebuild --layouts qwerty_us --lengths 4-12 \
    --algorithms ntlm,lm --db rainbow.duckdb

# Add structural patterns (famous walks, sweeps, zig-zags, interleaves, doublings)
keywalk-audit build-rainbow --rebuild --layouts qwerty_us --lengths 4-16 --patterns

# Add the shift-doubled compound family, e.g. 1a0k1a0k!A)K!A)K (implies --patterns)
keywalk-audit build-rainbow --rebuild --layouts qwerty_us --lengths 8-32 --shift-doublings

# Add knight-move skip walks (implies --patterns; can be large)
keywalk-audit build-rainbow --rebuild --layouts qwerty_us --knight

# Several layouts, fast hashes only
keywalk-audit build-rainbow --rebuild --layouts qwerty_us,azerty_fr,numpad \
    --lengths 4-12 --patterns --fast-only
```

`--max-turns` bounds direction changes per short walk, `--max-segments` bounds
composed long walks, and `--long-seed-cap` caps the seeds fed to the long-walk
composer. The table persists across runs and is rebuilt only with `--rebuild`.

### Audit a PWDUMP file

```
keywalk-audit audit users.pwdump --db rainbow.duckdb --threshold 0.7 \
    --output report --format all
```

The format is auto-detected as PWDUMP versus raw hive by sniffing the `regf`
magic bytes.

### Audit a local SAM hive

Pass the SYSTEM hive alongside the SAM hive:

```
keywalk-audit audit SAM --system-hive SYSTEM --db rainbow.duckdb --format console
```

### Audit Active Directory hashes

The tool reads PWDUMP and local SAM, not `NTDS.dit` directly. Stage the domain
hashes to a pwdump-format file first with impacket's secretsdump, then audit
that file:

```
# DCSync against a domain controller
secretsdump.py -just-dc-ntlm DOMAIN/user@dc-host -outputfile domain

# or offline from a captured NTDS.dit + SYSTEM hive
secretsdump.py -ntds NTDS.dit -system SYSTEM LOCAL -outputfile domain

keywalk-audit audit domain.ntds --db rainbow.duckdb --threshold 0.7 \
    --output report --format xlsx
```

### Audit PINs (numpad vs phone keypad)

The phone keypad is the vertical inverse of the numeric keypad, so a PIN like
`1470` walks cleanly on a phone but not on a numpad. Audit against the device
the PINs came from, or build both tables:

```
keywalk-audit build-rainbow --rebuild --layouts phone_keypad --lengths 4-8 --patterns
keywalk-audit build-rainbow --layouts numpad --lengths 4-8 --patterns
```

### Audit non-US keyboards

```
keywalk-audit build-rainbow --rebuild --layouts azerty_fr,qwertz_de --lengths 4-12 --patterns
keywalk-audit score "azerty" --layout azerty_fr
keywalk-audit score "qwertz" --layout qwertz_de
```

### Choose an output format

```
keywalk-audit audit users.pwdump --db rainbow.duckdb --format json      # canonical record
keywalk-audit audit users.pwdump --db rainbow.duckdb --format console    # terminal table
keywalk-audit audit users.pwdump --db rainbow.duckdb --output report --format all
```

`all` writes JSON, XLSX, CSV, HTML, Markdown, and SARIF under one stem. With no
`--output`, `json` prints a compact summary and `console` prints the table.

### Generate a walk wordlist

```
keywalk-audit generate --layout qwerty_us --lengths 4-8 --patterns \
    --min-score 0.6 --mutate --output walks.txt

# the shift-doubled compound family on its own
keywalk-audit generate --layout qwerty_us --lengths 8-32 --shift-doublings
```

`--min-score` filters by the calibrated walk score, `--mutate` expands each
survivor through the mutation engine, and `--limit` caps the count.

### Crack unmatched hashes with hashcat

```
keywalk-audit crack users.pwdump --db rainbow.duckdb --algorithm ntlm \
    --mutate --min-score 0.6 --work-dir ./crack --timeout 600
```

This seeds hashcat with the table's candidates, expands them with the mutation
rules, and runs `hashcat -a 0 -r walk.rule`. It targets NTLM or LM and accepts
PWDUMP input only. When hashcat is absent the report returns with
`hashcat_invoked=false` and an explanatory error rather than failing.

### Inspect the mutation engine

```
keywalk-audit mutations --sample 1qaz2wsx     # show the Python expansions
keywalk-audit mutations --masks               # walk-shaped hashcat masks
keywalk-audit mutations --rules-out walk.rule # write the hashcat rule file
```

### Decode or encode Cisco Type-7

Type-7 is reversible obfuscation, not a one-way hash, so it is recovered by
direct decoding:

```
keywalk-audit decode-cisco7 02050D480809        # -> cisco
keywalk-audit encode-cisco7 secret --seed 7
```

### Re-render a saved report

```
keywalk-audit render report.json --format html --output report.html
keywalk-audit render report.json --format console
```

### Fuzzy lookup against the saved indexes

```
keywalk-audit fuzzy "1qaz2wsx3edc4rfv" --db rainbow.duckdb --kind both --threshold 0.8
```

`--kind` selects the geometric index (physical-path similarity, which also
clusters shift mirrors), the string index (character n-gram similarity, which
catches suffix and leet variants), or both.

## Output

Each audit finding records the username, RID, matched algorithm (`ntlm` or
`lm`), recovered plaintext, walk score, matched layout, geometric fingerprint,
and the sizes of its geometric and string fuzzy clusters. The report also
carries summary totals: account count, walk-account count and percentage,
threshold, and runtime.

| format | notes |
|--------|-------|
| `json` | full report, the canonical record |
| `xlsx` | Summary, Findings, Fuzzy_Clusters, Score_Distribution sheets |
| `csv` | one row per finding (RFC 4180) |
| `html` | self-contained single file, every value escaped |
| `md` | GitHub-flavored summary and findings table |
| `sarif` | SARIF 2.1.0 for code-scanning ingestion |
| `console` | aligned plain-text table to stdout |
| `all` | every file format under one stem |

## Layouts

`qwerty_us`, `qwerty_uk`, `qwerty_intl`, `qwertz_de`, `azerty_fr`, `dvorak`,
`colemak`, `numpad`, `phone_keypad`. Each maps characters to a grid where
columns align across rows so vertical walks like `1qaz` score correctly.
Layouts optionally carry a physical row-stagger model and a touch-typing finger
map used by `analyze`.

## Hash algorithms

The registry holds 33 hashcat-supported modes. Twelve build in pure Python at
table-build time for immediate exact lookups: NTLM, LM, and the raw modes (MD4,
MD5, SHA-1, SHA-224/256/384/512, SHA3-256/512, BLAKE2b). MD4 is implemented
from scratch because OpenSSL 3 drops it from `hashlib`. Slow modes (bcrypt,
scrypt, the crypt family, the Kerberos AES variants, PBKDF2) are not
materialized; audits against those go through hashcat at audit time. Cisco
Type-5 reuses the md5crypt mode, and Cisco Type-7 is handled by the decoder
rather than hashcat.

## Architecture and storage

All walk generation, scoring, fingerprinting, fuzzy hashing, SAM ingestion, and
reporting is pure Python, as is build-time hashing for the fast modes.
Audit-time cracking of unknown captured hashes is delegated to hashcat as a
subprocess with explicit argument lists (never a shell). Storage is a DuckDB
file holding `candidates`, `hashes`, and `fuzzy_signatures` tables, with the
geometric and string MinHash LSH indexes pickled alongside as `<db>.geom.pkl`
and `<db>.str.pkl`.

Module-level detail is in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). See also
[docs/SCORING.md](docs/SCORING.md) (scoring formulas),
[docs/FUZZY_HASHING.md](docs/FUZZY_HASHING.md) (MinHash and LSH math),
[docs/HASH_MODES.md](docs/HASH_MODES.md) (the mode registry and Cisco notes),
[docs/LAYOUTS.md](docs/LAYOUTS.md) (the geometric model and the nine layouts),
[docs/PATTERNS.md](docs/PATTERNS.md) (structural generators),
[docs/ANALYSIS.md](docs/ANALYSIS.md) (deep analysis),
[docs/MUTATIONS.md](docs/MUTATIONS.md) (the mutation engine), and
[docs/REPORTING.md](docs/REPORTING.md) (output formats).

## Acceptance criteria (verified)

1. The eight canonical reference walks all score at or above 0.7 with the
   calibrated default weights on QWERTY US.
2. The four shift-mirror pairs produce identical geometric fingerprints.
3. The reversed-segment pair (`1qaz2wsx3edc4rfv` and `4rfv3edc2wsx1qaz`)
   clusters in the string MinHash LSH at threshold 0.8.
4. A synthetic PWDUMP with 10 walk-password accounts and 10 random-password
   accounts produces a report identifying exactly the 10 walk accounts at
   threshold 0.7.

Run the test suite:

```
pytest --cov=keywalk_audit --cov-report=term-missing
```

## Threshold tuning

The default audit threshold is 0.7. Lowering it admits weaker patterns (a plain
straight-line walk like `qwertyui` scores around 0.72, partial walks score
lower). Raising it surfaces only deliberate walks with multiple segments or
shift mirrors. Tune against a representative corpus rather than guessing.

## License

MIT. See [LICENSE](LICENSE).
