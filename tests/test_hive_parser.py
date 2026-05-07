"""Tests for sam/hive_parser.py.

A real Windows SAM hive cannot be synthesized cleanly without a Windows
host, so the happy-path test fakes out impacket's ``LocalOperations`` and
``SAMHashes`` to verify our wrapper logic. Error paths are exercised
against a stub ``regf``-prefixed file that fails impacket's deeper parse.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from keywalk_audit.sam.hive_parser import HiveParseError, parse_hive

if TYPE_CHECKING:
    from collections.abc import Iterator


def test_parse_hive_raises_when_sam_missing(tmp_path: Path) -> None:
    sys_hive = tmp_path / "SYSTEM"
    sys_hive.write_bytes(b"regf" + b"\x00" * 100)
    with pytest.raises(HiveParseError, match="SAM hive not found"):
        list(parse_hive(tmp_path / "missing-SAM", sys_hive))


def test_parse_hive_raises_when_system_missing(tmp_path: Path) -> None:
    sam_hive = tmp_path / "SAM"
    sam_hive.write_bytes(b"regf" + b"\x00" * 100)
    with pytest.raises(HiveParseError, match="SYSTEM hive not found"):
        list(parse_hive(sam_hive, tmp_path / "missing-SYSTEM"))


def test_parse_hive_wraps_impacket_failure(tmp_path: Path) -> None:
    """A bare regf-prefixed file fails impacket; the error is wrapped."""
    sam_hive = tmp_path / "SAM"
    sys_hive = tmp_path / "SYSTEM"
    sam_hive.write_bytes(b"regf" + b"\x00" * 4096)
    sys_hive.write_bytes(b"regf" + b"\x00" * 4096)
    with pytest.raises(HiveParseError):
        list(parse_hive(sam_hive, sys_hive))


def test_parse_hive_yields_entries_via_mocked_impacket(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify wrapper orchestration using a fake LocalOperations/SAMHashes
    pair that emit a synthetic pwdump file."""

    sam_hive = tmp_path / "SAM"
    sys_hive = tmp_path / "SYSTEM"
    sam_hive.write_bytes(b"regf" + b"\x00" * 100)
    sys_hive.write_bytes(b"regf" + b"\x00" * 100)

    fake_pwdump = (
        "alice:1001:aad3b435b51404eeaad3b435b51404ee:"
        "8846f7eaee8fb117ad06bdd830b7586c:::\n"
        "bob:1002:aad3b435b51404eeaad3b435b51404ee:"
        "1faedd4d2eaa61b09c8eba38e64f5b8a:::\n"
    )

    class _FakeLocalOps:
        def __init__(self, path: str) -> None:
            self._path = path

        def getBootKey(self) -> bytes:
            return b"\x00" * 16

    captured_export_target: dict[str, str] = {}

    class _FakeSAMHashes:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            _ = args, kwargs

        def dump(self) -> None:
            return None

        def export(self, target: str) -> None:
            captured_export_target["target"] = target
            Path(target + ".pwdump").write_text(fake_pwdump, encoding="utf-8")

    monkeypatch.setattr("keywalk_audit.sam.hive_parser.LocalOperations", _FakeLocalOps)
    monkeypatch.setattr("keywalk_audit.sam.hive_parser.SAMHashes", _FakeSAMHashes)

    entries = list(parse_hive(sam_hive, sys_hive))
    assert "target" in captured_export_target
    assert [e.username for e in entries] == ["alice", "bob"]
    assert entries[0].nt_hash == "8846f7eaee8fb117ad06bdd830b7586c"


def test_parse_hive_handles_export_extensionless(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Some impacket versions emit the file without a .pwdump suffix.
    Confirm the fallback path picks it up."""

    sam_hive = tmp_path / "SAM"
    sys_hive = tmp_path / "SYSTEM"
    sam_hive.write_bytes(b"regf" + b"\x00" * 100)
    sys_hive.write_bytes(b"regf" + b"\x00" * 100)

    class _FakeLocalOps:
        def __init__(self, path: str) -> None:
            _ = path

        def getBootKey(self) -> bytes:
            return b"\x00" * 16

    class _FakeSAMHashes:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            _ = args, kwargs

        def dump(self) -> None:
            return None

        def export(self, target: str) -> None:
            Path(target).write_text(
                "carol:1003:aad3b435b51404eeaad3b435b51404ee:0123456789abcdef0123456789abcdef:::\n",
                encoding="utf-8",
            )

    monkeypatch.setattr("keywalk_audit.sam.hive_parser.LocalOperations", _FakeLocalOps)
    monkeypatch.setattr("keywalk_audit.sam.hive_parser.SAMHashes", _FakeSAMHashes)

    entries = list(parse_hive(sam_hive, sys_hive))
    assert [e.username for e in entries] == ["carol"]


def test_parse_hive_returns_iterator(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sam_hive = tmp_path / "SAM"
    sys_hive = tmp_path / "SYSTEM"
    sam_hive.write_bytes(b"regf" + b"\x00" * 100)
    sys_hive.write_bytes(b"regf" + b"\x00" * 100)

    class _FakeLocalOps:
        def __init__(self, path: str) -> None:
            _ = path

        def getBootKey(self) -> bytes:
            return b"\x00" * 16

    class _FakeSAMHashes:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            _ = args, kwargs

        def dump(self) -> None:
            return None

        def export(self, target: str) -> None:
            Path(target + ".pwdump").write_text("", encoding="utf-8")

    monkeypatch.setattr("keywalk_audit.sam.hive_parser.LocalOperations", _FakeLocalOps)
    monkeypatch.setattr("keywalk_audit.sam.hive_parser.SAMHashes", _FakeSAMHashes)

    result: Iterator[Any] = parse_hive(sam_hive, sys_hive)
    assert iter(result) is result
