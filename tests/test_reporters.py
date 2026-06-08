"""Tests for keywalk_audit.audit.reporters."""

from __future__ import annotations

import csv
import json
from typing import TYPE_CHECKING

import pytest

from keywalk_audit.audit.reporters import (
    render_console,
    write_csv,
    write_html,
    write_markdown,
    write_sarif,
)
from keywalk_audit.audit.runner import AuditFinding, AuditReport

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_report() -> AuditReport:
    """Build a small AuditReport with two findings for testing."""
    finding_normal = AuditFinding(
        username="alice",
        rid=1001,
        matched_algorithm="ntlm",
        plaintext="1qazxsw2",
        walk_score=0.92,
        layout="qwerty_us",
        fingerprint="fp_abc123",
        fuzzy_geom_cluster=("wid1", "wid2", "wid3"),
        fuzzy_str_cluster=("wid4",),
    )
    # This finding exercises escape characters: "<", "|", and a space.
    finding_tricky = AuditFinding(
        username="bob",
        rid=1002,
        matched_algorithm="lm",
        plaintext="pass<w|ord 2",
        walk_score=0.85,
        layout="qwerty_uk",
        fingerprint="fp_def456",
        fuzzy_geom_cluster=(),
        fuzzy_str_cluster=("wid5", "wid6"),
    )
    return AuditReport(
        total_accounts=50,
        walk_accounts=2,
        findings=(finding_normal, finding_tricky),
        threshold=0.7,
        runtime_seconds=1.2345,
        errors=(),
    )


@pytest.fixture
def report() -> AuditReport:
    return _make_report()


# ---------------------------------------------------------------------------
# write_csv
# ---------------------------------------------------------------------------


def test_write_csv_file_exists(report: AuditReport, tmp_path: Path) -> None:
    out = tmp_path / "findings.csv"
    write_csv(report, out)
    assert out.exists()


def test_write_csv_header_and_row_count(report: AuditReport, tmp_path: Path) -> None:
    out = tmp_path / "findings.csv"
    write_csv(report, out)
    with out.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    # 1 header + 2 data rows
    assert len(rows) == 3
    assert rows[0] == [
        "username",
        "rid",
        "matched_algorithm",
        "plaintext",
        "walk_score",
        "layout",
        "fingerprint",
        "geom_cluster_size",
        "string_cluster_size",
    ]


def test_write_csv_data_values(report: AuditReport, tmp_path: Path) -> None:
    out = tmp_path / "findings.csv"
    write_csv(report, out)
    with out.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    # Row index 1 is alice's finding
    assert rows[1][0] == "alice"
    assert rows[1][3] == "1qazxsw2"
    # Cluster sizes for alice: geom=3, str=1
    assert rows[1][7] == "3"
    assert rows[1][8] == "1"
    # Row index 2 is the tricky finding (bob)
    assert rows[2][0] == "bob"
    assert rows[2][3] == "pass<w|ord 2"


# ---------------------------------------------------------------------------
# write_markdown
# ---------------------------------------------------------------------------


def test_write_markdown_title(report: AuditReport, tmp_path: Path) -> None:
    out = tmp_path / "report.md"
    write_markdown(report, out)
    content = out.read_text(encoding="utf-8")
    assert "# " in content


def test_write_markdown_summary_numbers(report: AuditReport, tmp_path: Path) -> None:
    out = tmp_path / "report.md"
    write_markdown(report, out)
    content = out.read_text(encoding="utf-8")
    assert "50" in content  # total accounts
    assert "2" in content  # walk accounts
    # Walk percentage: 2/50 * 100 = 4.00%
    assert "4.00" in content


def test_write_markdown_table_row_present(report: AuditReport, tmp_path: Path) -> None:
    out = tmp_path / "report.md"
    write_markdown(report, out)
    content = out.read_text(encoding="utf-8")
    # Table header separator must be present
    assert "| --- |" in content
    # At least alice's finding must appear in a row
    assert "alice" in content


def test_write_markdown_pipe_escaped_in_plaintext(report: AuditReport, tmp_path: Path) -> None:
    out = tmp_path / "report.md"
    write_markdown(report, out)
    content = out.read_text(encoding="utf-8")
    # The "|" in "pass<w|ord 2" must be escaped as "\|"
    assert "\\|" in content
    # And the raw unescaped pipe should NOT appear inside plaintext cells
    # (it will appear in table-separator lines and structural cell dividers,
    # but the plaintext "\|" escape must be present).
    assert "pass<w\\|ord 2" in content


# ---------------------------------------------------------------------------
# write_html
# ---------------------------------------------------------------------------


def test_write_html_structure(report: AuditReport, tmp_path: Path) -> None:
    out = tmp_path / "report.html"
    write_html(report, out)
    content = out.read_text(encoding="utf-8")
    assert "<html" in content
    assert "</html>" in content
    assert "<table" in content
    assert "<style" in content


def test_write_html_lt_escaped(report: AuditReport, tmp_path: Path) -> None:
    out = tmp_path / "report.html"
    write_html(report, out)
    content = out.read_text(encoding="utf-8")
    # The "<" in "pass<w|ord 2" must appear as &lt; not raw <
    assert "&lt;" in content
    # Raw "<" inside the plaintext cell must not appear
    # (we look for the specific plaintext string with a raw <)
    assert "pass<w" not in content


def test_write_html_both_usernames(report: AuditReport, tmp_path: Path) -> None:
    out = tmp_path / "report.html"
    write_html(report, out)
    content = out.read_text(encoding="utf-8")
    assert "alice" in content
    assert "bob" in content


# ---------------------------------------------------------------------------
# write_sarif
# ---------------------------------------------------------------------------


def test_write_sarif_loads_and_version(report: AuditReport, tmp_path: Path) -> None:
    out = tmp_path / "findings.sarif"
    write_sarif(report, out)
    with out.open(encoding="utf-8") as fh:
        doc = json.load(fh)
    assert doc["version"] == "2.1.0"


def test_write_sarif_tool_driver_name(report: AuditReport, tmp_path: Path) -> None:
    out = tmp_path / "findings.sarif"
    write_sarif(report, out)
    with out.open(encoding="utf-8") as fh:
        doc = json.load(fh)
    driver = doc["runs"][0]["tool"]["driver"]
    assert driver["name"] == "keywalk-audit"


def test_write_sarif_result_count(report: AuditReport, tmp_path: Path) -> None:
    out = tmp_path / "findings.sarif"
    write_sarif(report, out)
    with out.open(encoding="utf-8") as fh:
        doc = json.load(fh)
    results = doc["runs"][0]["results"]
    assert len(results) == len(report.findings)


def test_write_sarif_rule_id(report: AuditReport, tmp_path: Path) -> None:
    out = tmp_path / "findings.sarif"
    write_sarif(report, out)
    with out.open(encoding="utf-8") as fh:
        doc = json.load(fh)
    assert doc["runs"][0]["results"][0]["ruleId"] == "keyboard-walk-password"


# ---------------------------------------------------------------------------
# render_console
# ---------------------------------------------------------------------------


def test_render_console_returns_str(report: AuditReport) -> None:
    result = render_console(report)
    assert isinstance(result, str)


def test_render_console_contains_usernames(report: AuditReport) -> None:
    result = render_console(report)
    assert "alice" in result
    assert "bob" in result


def test_render_console_contains_total(report: AuditReport) -> None:
    result = render_console(report)
    assert "50" in result


def test_render_console_empty_findings() -> None:
    empty_report = AuditReport(
        total_accounts=10,
        walk_accounts=0,
        findings=(),
        threshold=0.7,
        runtime_seconds=0.01,
        errors=(),
    )
    result = render_console(empty_report)
    assert isinstance(result, str)
    assert "10" in result
    assert "No findings" in result
