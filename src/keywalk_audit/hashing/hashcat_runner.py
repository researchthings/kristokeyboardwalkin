"""Hashcat orchestration: detect, version-check, run, and parse the potfile.

All subprocess invocations use explicit argument lists. ``shell=True`` is
never used. Hashcat versions older than 6.2.0 are rejected because earlier
releases do not support all the modes registered in ``algorithms.py``.
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = logging.getLogger(__name__)

MIN_HASHCAT_VERSION: tuple[int, int, int] = (6, 2, 0)
_VERSION_RE = re.compile(r"v?(\d+)\.(\d+)\.(\d+)")
_SPEED_RE = re.compile(r"Speed\.\#\d+\.\.\.\.+:\s+(\d+(?:\.\d+)?)\s*([kMG]?)H/s", re.IGNORECASE)


class HashcatNotFoundError(RuntimeError):
    """Raised when hashcat is not installed or not on PATH."""


class HashcatVersionError(RuntimeError):
    """Raised when the installed hashcat is older than `MIN_HASHCAT_VERSION`."""


class HashcatExecutionError(RuntimeError):
    """Raised when hashcat exits with an error and stderr should be surfaced."""


@dataclass(frozen=True)
class HashcatResult:
    """Outcome of a hashcat invocation."""

    cracked: dict[str, str]
    runtime_seconds: float
    speed_hashes_per_sec: float
    exit_code: int


def detect_hashcat() -> Path:
    """Return the path to hashcat or raise HashcatNotFoundError."""
    located = shutil.which("hashcat")
    if located is None:
        raise HashcatNotFoundError("hashcat not found on PATH")
    return Path(located)


def hashcat_version(binary: Path) -> tuple[int, int, int]:
    """Parse hashcat ``--version`` output into ``(major, minor, patch)``."""
    proc = subprocess.run(
        [str(binary), "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    output = (proc.stdout or "") + (proc.stderr or "")
    match = _VERSION_RE.search(output)
    if not match:
        raise HashcatVersionError(f"could not parse hashcat version from: {output!r}")
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def _ensure_supported_version(binary: Path) -> None:
    found = hashcat_version(binary)
    if found < MIN_HASHCAT_VERSION:
        raise HashcatVersionError(
            f"hashcat {found[0]}.{found[1]}.{found[2]} is older than "
            f"{MIN_HASHCAT_VERSION[0]}.{MIN_HASHCAT_VERSION[1]}.{MIN_HASHCAT_VERSION[2]}"
        )


def _parse_speed(stdout: str) -> float:
    match = _SPEED_RE.search(stdout)
    if not match:
        return 0.0
    value = float(match.group(1))
    unit = match.group(2).lower() if match.group(2) else ""
    multipliers = {"": 1.0, "k": 1e3, "m": 1e6, "g": 1e9}
    return value * multipliers.get(unit, 1.0)


def parse_potfile(potfile: Path) -> dict[str, str]:
    """Parse a hashcat potfile (``hash:plaintext`` per line) into a dict.

    Lines without a colon are skipped. The hash is treated as the
    everything-up-to-the-last-colon and the plaintext as everything after.
    Hashcat itself emits the canonical form.
    """
    out: dict[str, str] = {}
    if not potfile.exists():
        return out
    for raw in potfile.read_text(encoding="utf-8", errors="replace").splitlines():
        if not raw or raw.startswith("#"):
            continue
        idx = raw.rfind(":")
        if idx < 0:
            continue
        out[raw[:idx]] = raw[idx + 1 :]
    return out


def run_hashcat(
    binary: Path,
    mode: int,
    hash_file: Path,
    wordlist: Path,
    potfile: Path,
    extra_args: Sequence[str] = (),
    timeout_seconds: int | None = None,
) -> HashcatResult:
    """Invoke hashcat and return cracked results plus runtime stats.

    The caller supplies all paths. ``extra_args`` is appended verbatim to
    the argument list and must not include shell metacharacters.
    """
    _ensure_supported_version(binary)
    cmd: list[str] = [
        str(binary),
        "-m",
        str(mode),
        "-a",
        "0",
        "--quiet",
        "--potfile-path",
        str(potfile),
        str(hash_file),
        str(wordlist),
        *extra_args,
    ]
    logger.info("running hashcat: %s", " ".join(cmd))
    start = time.time()
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout_seconds,
    )
    runtime = time.time() - start

    cracked = parse_potfile(potfile)
    speed = _parse_speed(proc.stdout or "")

    if proc.returncode not in (0, 1):
        raise HashcatExecutionError(
            f"hashcat exited with code {proc.returncode}\nstderr:\n{proc.stderr}"
        )

    return HashcatResult(
        cracked=cracked,
        runtime_seconds=runtime,
        speed_hashes_per_sec=speed,
        exit_code=proc.returncode,
    )
