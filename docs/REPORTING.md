# Reporting

The audit pipeline produces an `AuditReport`. It can be rendered to many
formats, chosen with `audit --format`:

| format | writer | notes |
|--------|--------|-------|
| `json` | `write_json` | full report, `sort_keys`; the canonical record |
| `xlsx` | `write_xlsx` | Summary, Findings, Fuzzy_Clusters, Score_Distribution sheets |
| `csv` | `write_csv` | one row per finding (RFC 4180, `newline=""`) |
| `html` | `write_html` | self-contained single file, every value HTML-escaped |
| `md` | `write_markdown` | GitHub-flavored summary + findings table |
| `sarif` | `write_sarif` | SARIF 2.1.0 for CI ingestion |
| `console` | `render_console` | aligned plain-text table to stdout |
| `all` | — | writes every file format under one stem |

```
keywalk-audit audit users.pwdump --db rainbow.duckdb --output report --format all
keywalk-audit audit users.pwdump --db rainbow.duckdb --format console
```

With no `--output`, `json` prints a compact summary and `console` prints
the table; the file formats require `--output`.

## SARIF

`write_sarif` emits a minimal valid SARIF 2.1.0 log: one run, one rule
(`keyboard-walk-password`), and one `warning`-level result per finding. The
message names the account, plaintext, layout, and score; `properties`
carry the RID, walk score, layout, and matched algorithm. Because these are
credential findings rather than source locations, each result carries an
empty `locations` array. This drops straight into a code-scanning / SARIF
upload step.

## Escaping

Usernames and recovered plaintexts are attacker-influenced and may contain
`<`, `>`, `&`, `|`, or newlines. The HTML writer routes every dynamic value
through `html.escape`; the Markdown writer escapes `|`; the CSV writer uses
the `csv` module's quoting. Treat reports as untrusted input when feeding
them to other tools.

## Re-rendering

A saved JSON report can be reloaded with `report_from_dict` (the inverse of
the JSON writer) and re-rendered without re-running the audit:

```
keywalk-audit render report.json --format html --output report.html
keywalk-audit render report.json --format console
```
