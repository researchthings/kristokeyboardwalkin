"""Tests for keywalk_audit.hashing.cisco_type7 encoder/decoder."""

from __future__ import annotations

import pytest

from keywalk_audit.hashing.cisco_type7 import KEY, CiscoType7Error, decode, encode

# ---------------------------------------------------------------------------
# Known published vectors
# ---------------------------------------------------------------------------


def test_decode_vector_044b() -> None:
    # 044B0A151C36435C0D -> "password" (seed 04)
    # Note: this is a well-known Cisco config snippet; the plaintext is "password"
    assert decode("044B0A151C36435C0D") == "password"


def test_decode_vector_02050d() -> None:
    # 02050D480809 -> "cisco" (seed 02)
    assert decode("02050D480809") == "cisco"


def test_decode_vector_070c28() -> None:
    # 070C285F4D06 -> "cisco" (seed 07)
    assert decode("070C285F4D06") == "cisco"


# ---------------------------------------------------------------------------
# Round-trip tests
# ---------------------------------------------------------------------------


def test_roundtrip_password1_seed0() -> None:
    assert decode(encode("Password1", 0)) == "Password1"


def test_roundtrip_password1_seed5() -> None:
    assert decode(encode("Password1", 5)) == "Password1"


def test_roundtrip_password1_seed15() -> None:
    assert decode(encode("Password1", 15)) == "Password1"


def test_roundtrip_1qaz2wsx_seed0() -> None:
    assert decode(encode("1qaz2wsx", 0)) == "1qaz2wsx"


def test_roundtrip_1qaz2wsx_seed5() -> None:
    assert decode(encode("1qaz2wsx", 5)) == "1qaz2wsx"


def test_roundtrip_1qaz2wsx_seed15() -> None:
    assert decode(encode("1qaz2wsx", 15)) == "1qaz2wsx"


def test_roundtrip_admin_seed0() -> None:
    assert decode(encode("admin", 0)) == "admin"


def test_roundtrip_admin_seed5() -> None:
    assert decode(encode("admin", 5)) == "admin"


def test_roundtrip_admin_seed15() -> None:
    assert decode(encode("admin", 15)) == "admin"


# ---------------------------------------------------------------------------
# Encode produces expected prefix and is decodable
# ---------------------------------------------------------------------------


def test_encode_cisco_seed2_starts_with_02() -> None:
    result = encode("cisco", 2)
    assert result.startswith("02")


def test_encode_cisco_seed2_decodes_back() -> None:
    assert decode(encode("cisco", 2)) == "cisco"


def test_encode_cisco_seed2_known_value() -> None:
    # Verified against algorithm: encode("cisco", 2) == "02050D480809"
    assert encode("cisco", 2) == "02050D480809"


# ---------------------------------------------------------------------------
# Malformed-input error cases
# ---------------------------------------------------------------------------


def test_decode_too_short_raises() -> None:
    with pytest.raises(CiscoType7Error):
        decode("0")


def test_decode_non_hex_raises() -> None:
    with pytest.raises(CiscoType7Error):
        decode("04ZZ")


def test_decode_odd_hex_tail_raises() -> None:
    # "040" -> seed "04", hex payload "0" which has odd length
    with pytest.raises(CiscoType7Error):
        decode("040")


def test_decode_seed_out_of_range_raises() -> None:
    # seed 99 >= len(KEY) == 53
    ct = "99" + "0A"
    with pytest.raises(CiscoType7Error):
        decode(ct)


def test_encode_seed_too_large_raises() -> None:
    with pytest.raises(CiscoType7Error):
        encode("x", len(KEY))


def test_encode_seed_negative_raises() -> None:
    with pytest.raises(CiscoType7Error):
        encode("x", -1)


# ---------------------------------------------------------------------------
# Whitespace stripping
# ---------------------------------------------------------------------------


def test_decode_strips_whitespace() -> None:
    assert decode("  02050D480809  ") == "cisco"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_decode_empty_payload_returns_empty_string() -> None:
    # seed "00" with no hex payload -> empty plaintext
    assert decode("00") == ""


def test_encode_empty_plaintext() -> None:
    assert encode("", 0) == "00"
