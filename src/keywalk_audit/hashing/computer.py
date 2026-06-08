"""Pure-Python hash computation for the build-time wordlist hashing step.

The audit pipeline must produce ``(algorithm, hash_value)`` pairs for every
candidate plaintext so that exact lookups against captured SAM hashes work
without invoking hashcat. Hashcat is reserved for audit-time cracking of
hashes that miss the rainbow table.

Only fast algorithms are implemented in this module. Slow algorithms
(bcrypt, scrypt, crypt-family) are out of scope for the rainbow table:
they are too expensive to materialize across the full candidate set, and
audits against them go through hashcat directly.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable

from impacket.ntlm import compute_lmhash, compute_nthash

from keywalk_audit.hashing.md4 import md4_hex

HashFn = Callable[[str], str]


def _ntlm(plaintext: str) -> str:
    raw = compute_nthash(plaintext)
    assert isinstance(raw, bytes)
    return raw.hex()


def _lm(plaintext: str) -> str:
    raw = compute_lmhash(plaintext)
    assert isinstance(raw, bytes)
    return raw.hex()


def _md4(plaintext: str) -> str:
    # OpenSSL 3 drops MD4 from hashlib, so the pure-Python implementation is
    # used. NTLM is MD4 over UTF-16LE; raw MD4 hashes the UTF-8 bytes directly.
    return md4_hex(plaintext.encode("utf-8"))


def _raw(name: str) -> HashFn:
    def _fn(plaintext: str) -> str:
        return hashlib.new(name, plaintext.encode("utf-8")).hexdigest()

    _fn.__name__ = f"_{name}"
    return _fn


SUPPORTED: dict[str, HashFn] = {
    "ntlm": _ntlm,
    "lm": _lm,
    "raw_md4": _md4,
    "raw_md5": _raw("md5"),
    "raw_sha1": _raw("sha1"),
    "raw_sha224": _raw("sha224"),
    "raw_sha256": _raw("sha256"),
    "raw_sha384": _raw("sha384"),
    "raw_sha512": _raw("sha512"),
    "raw_sha3_256": _raw("sha3_256"),
    "raw_sha3_512": _raw("sha3_512"),
    "raw_blake2b": _raw("blake2b"),
}


def can_compute(algorithm: str) -> bool:
    return algorithm in SUPPORTED


def compute_hash(algorithm: str, plaintext: str) -> str:
    """Compute the hex-encoded hash of `plaintext` under `algorithm`.

    Raises KeyError when the algorithm has no Python implementation.
    """
    try:
        fn = SUPPORTED[algorithm]
    except KeyError as exc:
        known = ", ".join(sorted(SUPPORTED))
        raise KeyError(f"no Python hash computer for {algorithm!r}. Supported: {known}") from exc
    return fn(plaintext)
