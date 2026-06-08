"""Cisco IOS Type-7 password encoder and decoder.

Type-7 is reversible obfuscation (a Vigenère-style XOR against a fixed key),
NOT a one-way hash.  This module provides ``encode`` and ``decode`` so that
audit pipelines can recover or reproduce Type-7 ciphertexts without hashcat.

Algorithm
---------
The 53-byte key ``KEY`` is XOR'd against the plaintext bytes, cycling via
modular arithmetic.  A ciphertext is: a 2-digit decimal seed index (0-52)
followed by the per-byte XOR outputs hex-encoded uppercase, two digits each.

Round-trip guarantee: ``decode(encode(p, s)) == p`` for any ASCII ``p`` and
any seed ``s`` in ``range(len(KEY))``.
"""

from __future__ import annotations

#: Fixed XOR key used by Cisco IOS Type-7 obfuscation (53 bytes, well-known).
KEY: bytes = b"dsfd;kfoA,.iyewrkldJKDHSUBsgvca69834ncxv9873254k;fg87"

_KEY_LEN: int = len(KEY)  # 53


class CiscoType7Error(ValueError):
    """Raised when a Type-7 ciphertext is malformed or a seed is out of range."""


def decode(ciphertext: str) -> str:
    """Decode a Cisco IOS Type-7 ciphertext and return the plaintext.

    Args:
        ciphertext: A Type-7 string, e.g. ``"02050D480809"``.  Leading and
            trailing whitespace is stripped before parsing.

    Returns:
        The recovered plaintext as a ``str``.

    Raises:
        CiscoType7Error: If the ciphertext is shorter than 2 characters, the
            leading seed field is not decimal digits, the seed is out of range
            (``0 <= seed < len(KEY)``), the hex payload contains non-hex
            characters, or the hex payload has an odd number of nibbles.
    """
    ciphertext = ciphertext.strip()

    if len(ciphertext) < 2:
        raise CiscoType7Error(
            f"ciphertext too short (need at least 2 digits for the seed): {ciphertext!r}"
        )

    seed_str = ciphertext[:2]
    if not seed_str.isdigit():
        raise CiscoType7Error(f"seed field {seed_str!r} is not two decimal digits")

    seed = int(seed_str)
    if not (0 <= seed < _KEY_LEN):
        raise CiscoType7Error(f"seed {seed} is out of range (must be 0 <= seed < {_KEY_LEN})")

    hex_payload = ciphertext[2:]
    if len(hex_payload) % 2 != 0:
        raise CiscoType7Error(
            f"hex payload has odd length ({len(hex_payload)} nibbles): {hex_payload!r}"
        )

    try:
        raw_bytes = bytes.fromhex(hex_payload)
    except ValueError as exc:
        raise CiscoType7Error(f"hex payload contains non-hex characters: {hex_payload!r}") from exc

    return "".join(chr(byte ^ KEY[(seed + i) % _KEY_LEN]) for i, byte in enumerate(raw_bytes))


def encode(plaintext: str, seed: int = 0) -> str:
    """Encode *plaintext* as a Cisco IOS Type-7 ciphertext.

    Args:
        plaintext: The password to obfuscate.
        seed: The starting index into ``KEY`` (0-52 inclusive).  Defaults to 0.

    Returns:
        A Type-7 string with a 2-digit zero-padded seed prefix followed by
        uppercase hex byte pairs, e.g. ``"02050D480809"``.

    Raises:
        CiscoType7Error: If ``seed`` is outside ``range(len(KEY))``.
    """
    if not (0 <= seed < _KEY_LEN):
        raise CiscoType7Error(f"seed {seed} is out of range (must be 0 <= seed < {_KEY_LEN})")

    hex_parts = "".join(
        f"{ord(ch) ^ KEY[(seed + i) % _KEY_LEN]:02X}" for i, ch in enumerate(plaintext)
    )
    return f"{seed:02d}{hex_parts}"
