"""Tests for sam/autodetect.py."""

from __future__ import annotations

from typing import TYPE_CHECKING

from keywalk_audit.sam.autodetect import detect_format

if TYPE_CHECKING:
    from pathlib import Path


def test_detect_pwdump(tmp_path: Path) -> None:
    p = tmp_path / "users.pwdump"
    p.write_text("user:1:lm:nt:::\n", encoding="utf-8")
    assert detect_format(p) == "pwdump"


def test_detect_hive_by_magic(tmp_path: Path) -> None:
    p = tmp_path / "SAM"
    p.write_bytes(b"regf" + b"\x00" * 100)
    assert detect_format(p) == "hive"


def test_detect_treats_unknown_as_pwdump(tmp_path: Path) -> None:
    p = tmp_path / "weird"
    p.write_bytes(b"\x00\x01\x02\x03more bytes")
    assert detect_format(p) == "pwdump"


def test_detect_empty_file_is_pwdump(tmp_path: Path) -> None:
    p = tmp_path / "empty"
    p.write_bytes(b"")
    assert detect_format(p) == "pwdump"
