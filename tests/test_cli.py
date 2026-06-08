"""CLI smoke tests via Click's CliRunner."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from click.testing import CliRunner

from keywalk_audit.cli import main

if TYPE_CHECKING:
    from pathlib import Path


def test_cli_help_lists_all_subcommands() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    for cmd in ("build-rainbow", "audit", "score", "fingerprint", "fuzzy"):
        assert cmd in result.output


def test_cli_version_runs() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0


def test_cli_score_emits_json() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["score", "1qazxsw2!QAZXSW@"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["layout"] == "qwerty_us"
    assert payload["total"] >= 0.7


def test_cli_fingerprint_emits_hex() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["fingerprint", "1qazxsw2"])
    assert result.exit_code == 0
    fp = result.output.strip()
    assert len(fp) == 32
    int(fp, 16)


def test_cli_fingerprint_shift_mirror_match() -> None:
    runner = CliRunner()
    a = runner.invoke(main, ["fingerprint", "1qazxsw2"])
    b = runner.invoke(main, ["fingerprint", "!QAZXSW@"])
    assert a.exit_code == 0
    assert b.exit_code == 0
    assert a.output.strip() == b.output.strip()


def test_cli_score_unknown_layout_errors() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["score", "1qaz", "--layout", "klingon"])
    assert result.exit_code != 0


def test_cli_build_rainbow_smoke(tmp_path: Path) -> None:
    runner = CliRunner()
    db = tmp_path / "rainbow.duckdb"
    result = runner.invoke(
        main,
        [
            "build-rainbow",
            "--rebuild",
            "--layouts",
            "qwerty_us",
            "--lengths",
            "4",
            "--algorithms",
            "ntlm",
            "--max-turns",
            "0",
            "--max-segments",
            "2",
            "--long-seed-cap",
            "8",
            "--db",
            str(db),
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["candidates_inserted"] > 0
    assert payload["layouts_processed"] == ["qwerty_us"]


def test_cli_audit_smoke(tmp_path: Path) -> None:
    """Build a tiny rainbow then audit a synthetic PWDUMP through the CLI."""
    runner = CliRunner()
    db = tmp_path / "rainbow.duckdb"
    runner.invoke(
        main,
        [
            "build-rainbow",
            "--rebuild",
            "--layouts",
            "qwerty_us",
            "--lengths",
            "4",
            "--algorithms",
            "ntlm",
            "--max-turns",
            "0",
            "--max-segments",
            "2",
            "--long-seed-cap",
            "8",
            "--db",
            str(db),
        ],
    )

    pwdump = tmp_path / "users.pwdump"
    pwdump.write_text("alice:1:lm:0123456789abcdef0123456789abcdef:::\n", encoding="utf-8")

    result = runner.invoke(
        main,
        [
            "audit",
            str(pwdump),
            "--db",
            str(db),
            "--threshold",
            "0.7",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["total_accounts"] == 1
