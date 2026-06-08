"""pytest tests for the pure-Python MD4 implementation (RFC 1320).

Covers all six official RFC 1320 known-answer test vectors, a basic
type/length check on the raw-bytes API, and the well-known NTLM NT-hash
of "password" as an end-to-end cross-validation.
"""

from __future__ import annotations

import pytest

from keywalk_audit.hashing.md4 import md4, md4_hex

# ---------------------------------------------------------------------------
# RFC 1320 §A.5 known-answer test vectors
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("data", "expected_hex"),
    [
        (b"", "31d6cfe0d16ae931b73c59d7e0c089c0"),
        (b"a", "bde52cb31de33e46245e05fbdbd6fb24"),
        (b"abc", "a448017aaf21d8525fc10ae87aa6729d"),
        (b"message digest", "d9130a8164549fe818874806e1c7014b"),
        (b"abcdefghijklmnopqrstuvwxyz", "d79e1c308aa5bbcdeea8ed63df412da9"),
        (
            b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
            "043f8582f241db351ce627e153e7f0e4",
        ),
    ],
)
def test_md4_hex_rfc1320_vectors(data: bytes, expected_hex: str) -> None:
    """md4_hex must match all RFC 1320 §A.5 known-answer test vectors."""
    assert md4_hex(data) == expected_hex


# ---------------------------------------------------------------------------
# Raw-bytes API sanity checks
# ---------------------------------------------------------------------------


def test_md4_empty_returns_bytes() -> None:
    """md4(b'') must return a bytes object."""
    result = md4(b"")
    assert isinstance(result, bytes)


def test_md4_empty_digest_length_is_16() -> None:
    """MD4 digest is always 128 bits (16 bytes)."""
    assert len(md4(b"")) == 16


# ---------------------------------------------------------------------------
# NTLM NT-hash cross-validation
# The NT hash of a password is MD4(password.encode("utf-16le")).
# "password" -> 8846f7eaee8fb117ad06bdd830b7586c is a well-known value
# used throughout the Windows security literature and supported by
# multiple independent implementations (impacket, Samba, hashcat mode 1000).
# ---------------------------------------------------------------------------


def test_md4_ntlm_nt_hash_of_password() -> None:
    """md4 of 'password' in UTF-16LE must equal the well-known NTLM NT hash."""
    nt_hash = md4("password".encode("utf-16le")).hex()
    assert nt_hash == "8846f7eaee8fb117ad06bdd830b7586c"
