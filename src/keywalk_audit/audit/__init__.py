"""Audit pipeline: SAM ingestion, rainbow lookup, and reporting."""

from __future__ import annotations

from keywalk_audit.audit.crack import CrackReport, candidate_plaintexts, crack_hashes
from keywalk_audit.audit.report import write_json, write_xlsx
from keywalk_audit.audit.reporters import (
    render_console,
    write_csv,
    write_html,
    write_markdown,
    write_sarif,
)
from keywalk_audit.audit.runner import AuditFinding, AuditReport, audit, report_from_dict

__all__ = [
    "AuditFinding",
    "AuditReport",
    "CrackReport",
    "audit",
    "candidate_plaintexts",
    "crack_hashes",
    "render_console",
    "report_from_dict",
    "write_csv",
    "write_html",
    "write_json",
    "write_markdown",
    "write_sarif",
    "write_xlsx",
]
