"""Tests for sam/pwdump_parser.py."""

from __future__ import annotations

from pathlib import Path

from keywalk_audit.sam.pwdump_parser import SamEntry, parse_pwdump

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_pwdump.txt"


def test_parse_pwdump_yields_20_entries() -> None:
    entries = list(parse_pwdump(FIXTURE_PATH))
    assert len(entries) == 20


def test_parse_pwdump_first_entry_walker01() -> None:
    entries = list(parse_pwdump(FIXTURE_PATH))
    assert entries[0] == SamEntry(
        username="walker01",
        rid=1001,
        lm_hash="089238590968dc7b130dfc534e51113e",
        nt_hash="d030916f5b1a9a7a9b719ac09171fcfb",
    )


def test_parse_pwdump_skips_blank_and_comment_lines(tmp_path: Path) -> None:
    text = "# header comment\n\n# blank below\n\nbob:1000:aabb:ccdd:::\n\n"
    p = tmp_path / "tiny.pwdump"
    p.write_text(text, encoding="utf-8")
    entries = list(parse_pwdump(p))
    assert len(entries) == 1
    assert entries[0].username == "bob"


def test_parse_pwdump_skips_malformed_lines(tmp_path: Path) -> None:
    text = "good:1:lm1:nt1:::\nmalformed\nbad_rid:notanumber:lm:nt:::\nalso:2:lm2:nt2:::\n"
    p = tmp_path / "mixed.pwdump"
    p.write_text(text, encoding="utf-8")
    entries = list(parse_pwdump(p))
    assert [e.username for e in entries] == ["good", "also"]


def test_parse_pwdump_lowercases_hex_values(tmp_path: Path) -> None:
    text = "user:1:AABBCCDD:1122EEFF:::\n"
    p = tmp_path / "case.pwdump"
    p.write_text(text, encoding="utf-8")
    entries = list(parse_pwdump(p))
    assert entries[0].lm_hash == "aabbccdd"
    assert entries[0].nt_hash == "1122eeff"
