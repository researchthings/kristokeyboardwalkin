"""Hashing primitives: algorithm registry, hash computation, hashcat
orchestration, walk-aware mutation rules, and the Cisco Type-7 codec."""

from __future__ import annotations

from keywalk_audit.hashing.algorithms import HASHCAT_MODES, HashAlgo, get_algo
from keywalk_audit.hashing.cisco_type7 import CiscoType7Error
from keywalk_audit.hashing.cisco_type7 import decode as cisco7_decode
from keywalk_audit.hashing.cisco_type7 import encode as cisco7_encode
from keywalk_audit.hashing.computer import can_compute, compute_hash
from keywalk_audit.hashing.hashcat_runner import (
    HashcatResult,
    detect_hashcat,
    hashcat_version,
    parse_potfile,
    run_hashcat,
)
from keywalk_audit.hashing.md4 import md4, md4_hex
from keywalk_audit.hashing.mutations import (
    DEFAULT_RULES,
    expand_wordlist,
    python_mutations,
    walk_masks,
    write_rule_file,
)

__all__ = [
    "DEFAULT_RULES",
    "HASHCAT_MODES",
    "CiscoType7Error",
    "HashAlgo",
    "HashcatResult",
    "can_compute",
    "cisco7_decode",
    "cisco7_encode",
    "compute_hash",
    "detect_hashcat",
    "expand_wordlist",
    "get_algo",
    "hashcat_version",
    "md4",
    "md4_hex",
    "parse_potfile",
    "python_mutations",
    "run_hashcat",
    "walk_masks",
    "write_rule_file",
]
