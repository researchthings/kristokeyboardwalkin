"""Additional audit report writers: CSV, Markdown, HTML, SARIF, and console.

This module extends the report formats available beyond the JSON and XLSX
outputs in ``report.py``. Every function accepts a frozen ``AuditReport``
and either writes to a ``Path`` or returns a plain string.

Format overview
---------------
- ``write_csv``      - RFC 4180 CSV via the stdlib ``csv`` module.
- ``write_markdown`` - GitHub-Flavored Markdown with a summary section and
                       findings table.
- ``write_html``     - Self-contained single-file HTML with inline CSS.
- ``write_sarif``    - Minimal valid SARIF 2.1.0 JSON for CI/SAST tooling.
- ``render_console`` - Fixed-width plain-text summary for terminal output.
"""

from __future__ import annotations

import csv
import html
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from keywalk_audit.audit.runner import AuditFinding, AuditReport

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SARIF_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"
_SARIF_VERSION = "2.1.0"
_TOOL_NAME = "keywalk-audit"
_TOOL_URI = "https://github.com/researchthings/kristokeyboardwalkin"
_RULE_ID = "keyboard-walk-password"

_CSV_HEADER: tuple[str, ...] = (
    "username",
    "rid",
    "matched_algorithm",
    "plaintext",
    "walk_score",
    "layout",
    "fingerprint",
    "geom_cluster_size",
    "string_cluster_size",
)

_MD_TABLE_HEADER = "| username | rid | algorithm | plaintext | score | layout |"
_MD_TABLE_SEP = "| --- | --- | --- | --- | --- | --- |"


def _walk_percentage(report: AuditReport) -> float:
    """Return walk percentage, guarding against zero total accounts."""
    if report.total_accounts == 0:
        return 0.0
    return 100.0 * report.walk_accounts / report.total_accounts


def _truncate(value: str, width: int) -> str:
    """Truncate *value* to *width* characters, appending '…' if needed."""
    if len(value) <= width:
        return value
    return value[: width - 1] + "…"


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------


def write_csv(report: AuditReport, path: Path) -> None:
    """Write a CSV of the findings to *path*.

    The header row contains the column names defined in ``_CSV_HEADER``.
    Cluster sizes are the lengths of the respective fuzzy-cluster tuples.
    """
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(_CSV_HEADER)
        for finding in report.findings:
            writer.writerow(
                [
                    finding.username,
                    finding.rid,
                    finding.matched_algorithm,
                    finding.plaintext,
                    finding.walk_score,
                    finding.layout,
                    finding.fingerprint,
                    len(finding.fuzzy_geom_cluster),
                    len(finding.fuzzy_str_cluster),
                ]
            )


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------


def _md_escape_plaintext(value: str) -> str:
    """Escape pipe characters in *value* so they do not break table cells."""
    return value.replace("|", "\\|")


def write_markdown(report: AuditReport, path: Path) -> None:
    """Write a GitHub-Flavored Markdown audit report to *path*.

    The document has a title heading, a summary section, and a findings
    table. Pipe characters inside plaintext values are escaped.
    """
    pct = _walk_percentage(report)
    lines: list[str] = [
        "# keywalk-audit Report",
        "",
        "## Summary",
        "",
        f"- **Total accounts:** {report.total_accounts}",
        f"- **Walk accounts:** {report.walk_accounts}",
        f"- **Walk percentage:** {pct:.2f}%",
        f"- **Threshold:** {report.threshold}",
        f"- **Runtime:** {report.runtime_seconds:.4f} s",
        "",
    ]

    if report.findings:
        lines += [
            "## Findings",
            "",
            _MD_TABLE_HEADER,
            _MD_TABLE_SEP,
        ]
        for f in report.findings:
            safe_pt = _md_escape_plaintext(f.plaintext)
            lines.append(
                f"| {f.username} | {f.rid} | {f.matched_algorithm}"
                f" | {safe_pt} | {f.walk_score:.3f} | {f.layout} |"
            )
        lines.append("")
    else:
        lines += ["## Findings", "", "_No findings._", ""]

    path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

_HTML_STYLE = """\
<style>
  body { font-family: system-ui, sans-serif; margin: 2rem; color: #222; }
  h1 { color: #b00020; }
  h2 { border-bottom: 1px solid #ccc; padding-bottom: 0.25rem; }
  .summary { background: #f8f8f8; border: 1px solid #ddd; border-radius: 4px;
             padding: 1rem 1.5rem; display: inline-block; }
  .summary dt { font-weight: bold; float: left; clear: left; width: 14rem; }
  .summary dd { margin-left: 14rem; }
  table { border-collapse: collapse; width: 100%; margin-top: 1rem; }
  th { background: #b00020; color: #fff; padding: 0.4rem 0.6rem; text-align: left; }
  td { padding: 0.35rem 0.6rem; border-bottom: 1px solid #eee; }
  tr:nth-child(even) td { background: #fafafa; }
</style>"""


def _he(value: str) -> str:
    """HTML-escape *value* using the stdlib ``html`` module."""
    return html.escape(value)


def write_html(report: AuditReport, path: Path) -> None:
    """Write a self-contained HTML audit report to *path*.

    All dynamic values are HTML-escaped. No external assets are required.
    """
    pct = _walk_percentage(report)

    rows_html: list[str] = []
    for f in report.findings:
        rows_html.append(
            "  <tr>"
            f"<td>{_he(f.username)}</td>"
            f"<td>{f.rid}</td>"
            f"<td>{_he(f.matched_algorithm)}</td>"
            f"<td>{_he(f.plaintext)}</td>"
            f"<td>{f.walk_score:.3f}</td>"
            f"<td>{_he(f.layout)}</td>"
            f"<td>{len(f.fuzzy_geom_cluster)}</td>"
            f"<td>{len(f.fuzzy_str_cluster)}</td>"
            "</tr>"
        )

    findings_body = (
        "\n".join(rows_html) if rows_html else '  <tr><td colspan="8">No findings.</td></tr>'
    )

    content = f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>keywalk-audit Report</title>
{_HTML_STYLE}
</head>
<body>
<h1>keywalk-audit Report</h1>
<h2>Summary</h2>
<dl class="summary">
  <dt>Total accounts</dt><dd>{report.total_accounts}</dd>
  <dt>Walk accounts</dt><dd>{report.walk_accounts}</dd>
  <dt>Walk percentage</dt><dd>{pct:.2f}%</dd>
  <dt>Threshold</dt><dd>{report.threshold}</dd>
  <dt>Runtime</dt><dd>{report.runtime_seconds:.4f} s</dd>
</dl>
<h2>Findings</h2>
<table>
<thead>
  <tr>
    <th>username</th><th>rid</th><th>algorithm</th><th>plaintext</th>
    <th>score</th><th>layout</th><th>geom_cluster</th><th>str_cluster</th>
  </tr>
</thead>
<tbody>
{findings_body}
</tbody>
</table>
</body>
</html>
"""
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# SARIF
# ---------------------------------------------------------------------------


def _sarif_result(finding: AuditFinding) -> dict[str, object]:
    """Build a single SARIF result dict for *finding*."""
    message = (
        f"Keyboard-walk password detected for user '{finding.username}': "
        f"plaintext '{finding.plaintext}' matched on layout '{finding.layout}' "
        f"with walk score {finding.walk_score:.3f}."
    )
    return {
        "ruleId": _RULE_ID,
        "level": "warning",
        "message": {"text": message},
        "locations": [],
        "properties": {
            "rid": finding.rid,
            "walk_score": finding.walk_score,
            "layout": finding.layout,
            "matched_algorithm": finding.matched_algorithm,
        },
    }


def write_sarif(report: AuditReport, path: Path) -> None:
    """Write a minimal valid SARIF 2.1.0 log to *path*.

    The log contains a single run with one rule (``keyboard-walk-password``)
    and one result per finding. No physical file locations are included
    because these are credential findings, not source-code issues.
    """
    sarif_doc: dict[str, object] = {
        "version": _SARIF_VERSION,
        "$schema": _SARIF_SCHEMA,
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": _TOOL_NAME,
                        "informationUri": _TOOL_URI,
                        "rules": [
                            {
                                "id": _RULE_ID,
                                "name": "KeyboardWalkPassword",
                                "shortDescription": {
                                    "text": "Password matches a keyboard-walk pattern."
                                },
                            }
                        ],
                    }
                },
                "results": [_sarif_result(f) for f in report.findings],
            }
        ],
    }
    with path.open("w", encoding="utf-8") as fh:
        json.dump(sarif_doc, fh, indent=2)


# ---------------------------------------------------------------------------
# Console renderer
# ---------------------------------------------------------------------------

_COL_USER = 18
_COL_RID = 6
_COL_ALGO = 10
_COL_PT = 20
_COL_SCORE = 7
_COL_LAYOUT = 12


def render_console(report: AuditReport) -> str:
    """Return a fixed-width plain-text summary and findings table.

    Long values are truncated with a trailing ellipsis character. Nothing is
    printed; the caller is responsible for outputting the returned string.
    """
    pct = _walk_percentage(report)
    header_lines = [
        "=" * 80,
        "  keywalk-audit  |  Audit Report",
        "=" * 80,
        f"  Total accounts : {report.total_accounts}",
        f"  Walk accounts  : {report.walk_accounts}",
        f"  Walk percentage: {pct:.2f}%",
        f"  Threshold      : {report.threshold}",
        f"  Runtime        : {report.runtime_seconds:.4f} s",
        "=" * 80,
    ]

    if not report.findings:
        return "\n".join([*header_lines, "  No findings.", "=" * 80, ""])

    col_header = (
        f"  {'username':<{_COL_USER}}  {'rid':>{_COL_RID}}  "
        f"{'algorithm':<{_COL_ALGO}}  {'plaintext':<{_COL_PT}}  "
        f"{'score':>{_COL_SCORE}}  {'layout':<{_COL_LAYOUT}}"
    )
    separator = "  " + "-" * (
        _COL_USER + _COL_RID + _COL_ALGO + _COL_PT + _COL_SCORE + _COL_LAYOUT + 10
    )
    finding_lines: list[str] = [col_header, separator]
    for f in report.findings:
        u = _truncate(f.username, _COL_USER)
        pt = _truncate(f.plaintext, _COL_PT)
        algo = _truncate(f.matched_algorithm, _COL_ALGO)
        layout = _truncate(f.layout, _COL_LAYOUT)
        finding_lines.append(
            f"  {u:<{_COL_USER}}  {f.rid:>{_COL_RID}}  "
            f"{algo:<{_COL_ALGO}}  {pt:<{_COL_PT}}  "
            f"{f.walk_score:>{_COL_SCORE}.3f}  {layout:<{_COL_LAYOUT}}"
        )

    return "\n".join(header_lines + finding_lines + ["=" * 80, ""])
