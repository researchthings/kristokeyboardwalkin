"""CLI tests for the commands added in v0.2."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from keywalk_audit.cli import main
from keywalk_audit.hashing.computer import compute_hash
from keywalk_audit.layouts import QWERTY_US
from keywalk_audit.rainbow.builder import build_rainbow

if TYPE_CHECKING:
    from pathlib import Path

_LM = "aad3b435b51404eeaad3b435b51404ee"


@pytest.fixture(scope="module")
def rainbow_db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    db = tmp_path_factory.mktemp("cli") / "rainbow.duckdb"
    build_rainbow(
        layouts=[QWERTY_US],
        lengths=range(4, 5),
        algorithms=("ntlm",),
        db_path=db,
        rebuild=True,
        max_turns=0,
        max_segments=2,
        long_seed_cap=8,
    )
    return db


def _pwdump(path: Path) -> Path:
    nt = compute_hash("ntlm", "1qaz")
    path.write_text(f"alice:1000:{_LM}:{nt}:::\n", encoding="utf-8")
    return path


def test_help_lists_new_commands() -> None:
    result = CliRunner().invoke(main, ["--help"])
    assert result.exit_code == 0
    for cmd in ("analyze", "layouts", "algorithms", "generate", "crack", "render"):
        assert cmd in result.output


def test_layouts_command() -> None:
    result = CliRunner().invoke(main, ["layouts"])
    assert result.exit_code == 0
    rows = json.loads(result.output)
    names = {r["name"] for r in rows}
    assert {"qwerty_us", "azerty_fr", "phone_keypad"} <= names
    assert len(rows) == 9


def test_algorithms_command() -> None:
    result = CliRunner().invoke(main, ["algorithms"])
    assert result.exit_code == 0
    rows = json.loads(result.output)
    assert len(rows) == 33
    md4 = next(r for r in rows if r["name"] == "raw_md4")
    assert md4["build_computable"] is True


def test_analyze_auto_detects_layout() -> None:
    result = CliRunner().invoke(main, ["analyze", "azerty", "--auto"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["layout"] == "azerty_fr"
    assert payload["layout_ranking"][0]["layout"] == "azerty_fr"


def test_generate_command_to_file(tmp_path: Path) -> None:
    out = tmp_path / "walks.txt"
    result = CliRunner().invoke(
        main,
        [
            "generate",
            "--layout",
            "qwerty_us",
            "--lengths",
            "4",
            "--max-turns",
            "0",
            "--output",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    words = out.read_text(encoding="utf-8").split()
    assert "1qaz" in words


def test_decode_and_encode_cisco7_roundtrip() -> None:
    runner = CliRunner()
    decoded = runner.invoke(main, ["decode-cisco7", "02050D480809"])
    assert decoded.exit_code == 0
    assert decoded.output.strip() == "cisco"
    encoded = runner.invoke(main, ["encode-cisco7", "1qaz2wsx", "--seed", "7"])
    assert encoded.exit_code == 0
    back = runner.invoke(main, ["decode-cisco7", encoded.output.strip()])
    assert back.output.strip() == "1qaz2wsx"


def test_decode_cisco7_malformed_errors() -> None:
    result = CliRunner().invoke(main, ["decode-cisco7", "04ZZ"])
    assert result.exit_code != 0


def test_mutations_command_variants(tmp_path: Path) -> None:
    runner = CliRunner()
    masks = runner.invoke(main, ["mutations", "--masks"])
    assert masks.exit_code == 0
    assert json.loads(masks.output)
    sample = runner.invoke(main, ["mutations", "--sample", "1qaz2wsx"])
    assert "1qaz2wsx" in json.loads(sample.output)
    rules_out = tmp_path / "walk.rule"
    written = runner.invoke(main, ["mutations", "--rules-out", str(rules_out)])
    assert written.exit_code == 0
    assert rules_out.exists()


def test_audit_console_format(rainbow_db: Path, tmp_path: Path) -> None:
    pwdump = _pwdump(tmp_path / "users.pwdump")
    result = CliRunner().invoke(
        main, ["audit", str(pwdump), "--db", str(rainbow_db), "--format", "console"]
    )
    assert result.exit_code == 0, result.output
    assert "alice" in result.output


def test_audit_all_formats_and_render(rainbow_db: Path, tmp_path: Path) -> None:
    pwdump = _pwdump(tmp_path / "users.pwdump")
    out = tmp_path / "report"
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["audit", str(pwdump), "--db", str(rainbow_db), "--output", str(out), "--format", "all"],
    )
    assert result.exit_code == 0, result.output
    for suffix in (".json", ".xlsx", ".csv", ".html", ".md", ".sarif"):
        assert out.with_suffix(suffix).exists(), f"missing {suffix}"
    # Render the saved JSON report into Markdown.
    rendered = tmp_path / "again.md"
    render = runner.invoke(
        main, ["render", str(out.with_suffix(".json")), "--format", "md", "--output", str(rendered)]
    )
    assert render.exit_code == 0, render.output
    assert rendered.exists()
    assert "alice" in rendered.read_text(encoding="utf-8")


def test_crack_command_graceful_without_hashcat(rainbow_db: Path, tmp_path: Path) -> None:
    pwdump = _pwdump(tmp_path / "users.pwdump")
    result = CliRunner().invoke(
        main,
        ["crack", str(pwdump), "--db", str(rainbow_db), "--work-dir", str(tmp_path / "work")],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["wordlist_size"] > 0
    assert payload["rules_used"] > 0
