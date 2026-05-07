"""Tests for hashing algorithms registry, Python hash computer, and
hashcat runner (with subprocess stubs)."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from keywalk_audit.hashing.algorithms import HASHCAT_MODES, get_algo
from keywalk_audit.hashing.computer import can_compute, compute_hash
from keywalk_audit.hashing.hashcat_runner import (
    HashcatExecutionError,
    HashcatNotFoundError,
    HashcatVersionError,
    detect_hashcat,
    hashcat_version,
    parse_potfile,
    run_hashcat,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


def test_registry_has_28_algorithms() -> None:
    """The 28 entries match the spec's table verbatim. (Cisco type 5 is
    intentionally omitted because it reuses md5crypt mode 500.)"""
    assert len(HASHCAT_MODES) == 28


def test_registry_all_have_unique_names() -> None:
    names = [a.name for a in HASHCAT_MODES.values()]
    assert len(names) == len(set(names))


def test_registry_ntlm_mode_is_1000() -> None:
    assert HASHCAT_MODES["ntlm"].hashcat_mode == 1000
    assert HASHCAT_MODES["ntlm"].is_fast is True


def test_registry_bcrypt_is_slow() -> None:
    assert HASHCAT_MODES["bcrypt"].is_fast is False


def test_get_algo_unknown_raises() -> None:
    with pytest.raises(KeyError):
        get_algo("md7")


def test_compute_ntlm_known_value() -> None:
    # b'password' -> 8846f7eaee8fb117ad06bdd830b7586c (well-known)
    assert compute_hash("ntlm", "password") == "8846f7eaee8fb117ad06bdd830b7586c"


def test_compute_lm_known_value() -> None:
    # 'PASSWORD' -> e52cac67419a9a224a3b108f3fa6cb6d (well-known LM hash)
    assert compute_hash("lm", "password") == "e52cac67419a9a224a3b108f3fa6cb6d"


def test_compute_raw_md5() -> None:
    assert compute_hash("raw_md5", "") == "d41d8cd98f00b204e9800998ecf8427e"


def test_compute_raw_sha256() -> None:
    expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert compute_hash("raw_sha256", "") == expected


def test_can_compute_known_unknown() -> None:
    assert can_compute("ntlm") is True
    assert can_compute("bcrypt") is False


def test_compute_unknown_raises() -> None:
    with pytest.raises(KeyError):
        compute_hash("md7", "x")


def test_parse_potfile_round_trip(tmp_path: Path) -> None:
    pot = tmp_path / "hashcat.potfile"
    pot.write_text("aabbcc:hello\n# comment\n\nddeeff:world\n", encoding="utf-8")
    assert parse_potfile(pot) == {"aabbcc": "hello", "ddeeff": "world"}


def test_parse_potfile_missing(tmp_path: Path) -> None:
    assert parse_potfile(tmp_path / "missing") == {}


def test_parse_potfile_handles_colon_in_plaintext(tmp_path: Path) -> None:
    """Hashcat splits at the LAST colon; password may contain colons."""
    pot = tmp_path / "p"
    pot.write_text("abc:hello:world\n", encoding="utf-8")
    assert parse_potfile(pot) == {"abc:hello": "world"}


def test_detect_hashcat_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    with pytest.raises(HashcatNotFoundError):
        detect_hashcat()


def _stub_subprocess(
    monkeypatch: pytest.MonkeyPatch,
    stdout: str = "",
    stderr: str = "",
    returncode: int = 0,
) -> None:
    class _Result:
        def __init__(self) -> None:
            self.stdout = stdout
            self.stderr = stderr
            self.returncode = returncode

    def _fake_run(
        cmd: Sequence[str],
        capture_output: bool = False,
        text: bool = False,
        check: bool = False,
        timeout: float | None = None,
    ) -> _Result:
        _ = cmd, capture_output, text, check, timeout
        return _Result()

    monkeypatch.setattr("keywalk_audit.hashing.hashcat_runner.subprocess.run", _fake_run)


def test_hashcat_version_parses_known_format(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_subprocess(monkeypatch, stdout="v6.2.6\n")
    assert hashcat_version(Path("/fake/hashcat")) == (6, 2, 6)


def test_hashcat_version_too_old_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _stub_subprocess(monkeypatch, stdout="v5.1.0\n")
    with pytest.raises(HashcatVersionError):
        run_hashcat(
            binary=Path("/fake/hashcat"),
            mode=1000,
            hash_file=tmp_path / "h",
            wordlist=tmp_path / "w",
            potfile=tmp_path / "p",
        )


def test_run_hashcat_returns_cracked_results(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    pot = tmp_path / "p"
    pot.write_text("8846f7eaee8fb117ad06bdd830b7586c:password\n", encoding="utf-8")
    _stub_subprocess(monkeypatch, stdout="v6.2.6\nSpeed.#1.........: 1.5 MH/s\n")

    result = run_hashcat(
        binary=Path("/fake/hashcat"),
        mode=1000,
        hash_file=tmp_path / "h",
        wordlist=tmp_path / "w",
        potfile=pot,
    )
    assert result.cracked == {"8846f7eaee8fb117ad06bdd830b7586c": "password"}
    assert result.exit_code == 0
    assert result.speed_hashes_per_sec == pytest.approx(1.5e6)


def test_run_hashcat_surfaces_stderr(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _stub_subprocess(monkeypatch, stdout="v6.2.6\n", stderr="bad mode", returncode=2)
    with pytest.raises(HashcatExecutionError, match="bad mode"):
        run_hashcat(
            binary=Path("/fake/hashcat"),
            mode=1000,
            hash_file=tmp_path / "h",
            wordlist=tmp_path / "w",
            potfile=tmp_path / "p",
        )


def test_run_hashcat_returncode_one_is_no_crack(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Hashcat returns 1 when the run completes but no hashes cracked."""
    _stub_subprocess(monkeypatch, stdout="v6.2.6\n", returncode=1)
    result = run_hashcat(
        binary=Path("/fake/hashcat"),
        mode=1000,
        hash_file=tmp_path / "h",
        wordlist=tmp_path / "w",
        potfile=tmp_path / "p",
    )
    assert result.cracked == {}
    assert result.exit_code == 1
