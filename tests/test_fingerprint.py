"""Tests for walks/fingerprint.py."""

from __future__ import annotations

from typing import TYPE_CHECKING

from hypothesis import given
from hypothesis import strategies as st

from keywalk_audit.layouts import QWERTY_US
from keywalk_audit.walks.fingerprint import geometric_fingerprint
from keywalk_audit.walks.variants import shift_mirror

if TYPE_CHECKING:
    from collections.abc import Sequence

    from keywalk_audit.layouts.base import Layout


def test_fingerprint_is_hex_blake2b_128(qwerty_us: Layout) -> None:
    fp = geometric_fingerprint("1qaz", qwerty_us)
    assert len(fp) == 32
    int(fp, 16)


def test_fingerprint_deterministic(qwerty_us: Layout) -> None:
    a = geometric_fingerprint("1qazxsw2", qwerty_us)
    b = geometric_fingerprint("1qazxsw2", qwerty_us)
    assert a == b


def test_shift_mirror_pairs_match(
    qwerty_us: Layout, shift_mirror_pairs: Sequence[tuple[str, str]]
) -> None:
    for raw, mirrored in shift_mirror_pairs:
        assert geometric_fingerprint(raw, qwerty_us) == geometric_fingerprint(mirrored, qwerty_us)


def test_different_paths_produce_different_fingerprints(qwerty_us: Layout) -> None:
    a = geometric_fingerprint("1qaz", qwerty_us)
    b = geometric_fingerprint("zaq1", qwerty_us)
    assert a != b


def test_layout_namespace_isolation(qwerty_us: Layout, qwerty_uk: Layout) -> None:
    """The same physical path on two layouts produces distinct fingerprints
    because the layout name is mixed into the digest preimage. This keeps
    cross-layout candidate keys from colliding in the rainbow table.
    """
    assert geometric_fingerprint("1qaz", qwerty_us) != geometric_fingerprint("1qaz", qwerty_uk)


@given(st.text(alphabet="qwertyuiopasdfghjklzxcvbnm1234567890", min_size=2, max_size=12))
def test_fingerprint_invariant_under_shift_mirror(s: str) -> None:
    mirror = shift_mirror(s, QWERTY_US)
    assert geometric_fingerprint(s, QWERTY_US) == geometric_fingerprint(mirror, QWERTY_US)
