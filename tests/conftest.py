"""Shared pytest fixtures and constants."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from keywalk_audit.layouts import NUMPAD, QWERTY_INTL, QWERTY_UK, QWERTY_US, Layout

if TYPE_CHECKING:
    from collections.abc import Sequence

# Canonical positive examples from the project specification. All eight must
# score at or above 0.7 with the calibrated default weights on QWERTY US.
CANONICAL_WALKS: tuple[str, ...] = (
    "1qazxsw2!QAZXSW@",
    "1qaz2wsx!QAZ@WSX",
    "zaq12wsxZAQ!@WSX",
    "zaq1xsw2ZAQ!XSW@",
    "1qaz2wsx3edc4rfv",
    "4rfv3edc2wsx1qaz",
    "1qazxcde3!QAZXCDE#",
    "3edcxzaq1#EDCXZAQ!",
)

# Pairs that must produce identical geometric fingerprints (shift mirror).
SHIFT_MIRROR_PAIRS: tuple[tuple[str, str], ...] = (
    ("1qazxsw2", "!QAZXSW@"),
    ("1qaz2wsx", "!QAZ@WSX"),
    ("zaq12wsx", "ZAQ!@WSX"),
    ("zaq1xsw2", "ZAQ!XSW@"),
)

# Random-looking passwords that must score below the audit threshold.
RANDOM_PASSWORDS: tuple[str, ...] = (
    "Tx7mP$qz",
    "h9!aB2cD",
    "Zk3@p&Qx",
    "p4ssw0rD",
    "correctH3rs!",
    "f7Lq#m2X",
    "L0okH3re!",
    "8Rt#vNm2",
)


@pytest.fixture(scope="session")
def qwerty_us() -> Layout:
    return QWERTY_US


@pytest.fixture(scope="session")
def qwerty_uk() -> Layout:
    return QWERTY_UK


@pytest.fixture(scope="session")
def qwerty_intl() -> Layout:
    return QWERTY_INTL


@pytest.fixture(scope="session")
def numpad() -> Layout:
    return NUMPAD


@pytest.fixture(scope="session")
def canonical_walks() -> Sequence[str]:
    return CANONICAL_WALKS


@pytest.fixture(scope="session")
def shift_mirror_pairs() -> Sequence[tuple[str, str]]:
    return SHIFT_MIRROR_PAIRS


@pytest.fixture(scope="session")
def random_passwords() -> Sequence[str]:
    return RANDOM_PASSWORDS
