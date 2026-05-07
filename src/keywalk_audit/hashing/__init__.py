"""Hashing primitives: algorithm registry and hashcat subprocess orchestration."""

from __future__ import annotations

from keywalk_audit.hashing.algorithms import HASHCAT_MODES, HashAlgo, get_algo
from keywalk_audit.hashing.hashcat_runner import (
    HashcatResult,
    detect_hashcat,
    hashcat_version,
    parse_potfile,
    run_hashcat,
)

__all__ = [
    "HASHCAT_MODES",
    "HashAlgo",
    "HashcatResult",
    "detect_hashcat",
    "get_algo",
    "hashcat_version",
    "parse_potfile",
    "run_hashcat",
]
