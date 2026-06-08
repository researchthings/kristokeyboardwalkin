"""Keyboard-walk password mutation helpers: hashcat rules, masks, and pure-Python expansion.

This module provides three related capabilities for targeting walk-derivative passwords:

1. ``DEFAULT_RULES`` — a curated tuple of hashcat rule strings covering the most common
   mutations applied by real users (case transforms, digit/symbol appends, year appends,
   capitalization combos, leet substitutions).

2. ``write_rule_file`` / ``expand_wordlist`` — helpers to materialise rules and mutated
   wordlists to disk for use with hashcat or other crackers.

3. ``python_mutations`` — a pure-Python implementation of the same mutation families so
   that callers can enumerate candidates without spawning hashcat (e.g. for unit tests,
   small audits, or pre-filtering).

4. ``walk_masks`` — generate hashcat mask strings that model the structural shapes of
   walk passwords with common suffixes (digits, symbols, years).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

# ---------------------------------------------------------------------------
# Hashcat rule constants
# ---------------------------------------------------------------------------

DEFAULT_RULES: tuple[str, ...] = (
    # --- passthrough ---
    ":",
    # --- case transforms ---
    "l",
    "u",
    "c",
    "t",
    # --- structural transforms ---
    "r",
    "d",
    # --- append single digit 0-9 ---
    "$0",
    "$1",
    "$2",
    "$3",
    "$4",
    "$5",
    "$6",
    "$7",
    "$8",
    "$9",
    # --- append common symbols ---
    "$!",
    "$@",
    "$#",
    "$$",
    "$%",
    # --- append common years (each as a single chained-append rule) ---
    "$1$9$9$8",
    "$1$9$9$9",
    "$2$0$0$0",
    "$2$0$0$1",
    "$2$0$0$2",
    "$2$0$0$3",
    "$2$0$0$4",
    "$2$0$0$5",
    "$2$0$1$0",
    "$2$0$1$1",
    "$2$0$1$2",
    "$2$0$1$3",
    "$2$0$1$4",
    "$2$0$1$5",
    "$2$0$1$6",
    "$2$0$1$7",
    "$2$0$1$8",
    "$2$0$1$9",
    "$2$0$2$0",
    "$2$0$2$1",
    "$2$0$2$2",
    "$2$0$2$3",
    "$2$0$2$4",
    "$2$0$2$5",
    "$1$2$3$4",
    # --- capitalize then append a digit ---
    "c$1",
    "c$2",
    "c$3",
    "c$4",
    "c$5",
    "c$6",
    "c$7",
    "c$8",
    "c$9",
    "c$0",
    # --- capitalize then append a symbol ---
    "c$!",
    "c$@",
    # --- simple leet substitutions ---
    "se3",
    "sa@",
    "so0",
    "si1",
    "ss$",
)

# Verify no accidental duplicates were introduced during authoring.
assert len(DEFAULT_RULES) == len(set(DEFAULT_RULES)), "DEFAULT_RULES contains duplicate entries"

# ---------------------------------------------------------------------------
# Leet mapping used by python_mutations
# ---------------------------------------------------------------------------

_LEET_MAP: dict[str, str] = {
    "e": "3",
    "a": "@",
    "o": "0",
    "i": "1",
    "s": "$",
}


def _apply_leet(text: str) -> str:
    """Apply all substitutions in ``_LEET_MAP`` simultaneously (case-insensitive on keys)."""
    result: list[str] = []
    for ch in text:
        result.append(_LEET_MAP.get(ch.lower(), ch))
    return "".join(result)


# ---------------------------------------------------------------------------
# Pure-Python mutation engine
# ---------------------------------------------------------------------------


def python_mutations(plaintext: str) -> list[str]:
    """Return an order-preserving, de-duplicated list of mutations of *plaintext*.

    The original plaintext is always the first element.  Mutations applied:

    - original (always first)
    - capitalize first letter, lower-case remainder
    - all upper-case
    - all lower-case
    - reversed
    - duplicated (plaintext + plaintext)
    - append each digit 0-9
    - append "!"
    - append years 2018-2025
    - basic leet (e->3, a->@, o->0, i->1, s->$ applied simultaneously)
    """
    seen: set[str] = set()
    ordered: list[str] = []

    def _add(candidate: str) -> None:
        if candidate not in seen:
            seen.add(candidate)
            ordered.append(candidate)

    # 1. original first
    _add(plaintext)

    # 2. case variants
    _add(plaintext.capitalize())
    _add(plaintext.upper())
    _add(plaintext.lower())

    # 3. structural
    _add(plaintext[::-1])
    _add(plaintext + plaintext)

    # 4. append digits 0-9
    for digit in "0123456789":
        _add(plaintext + digit)

    # 5. append common symbol
    _add(plaintext + "!")

    # 6. append years 2018-2025
    for year in range(2018, 2026):
        _add(plaintext + str(year))

    # 7. basic leet substitution
    _add(_apply_leet(plaintext))

    return ordered


# ---------------------------------------------------------------------------
# File I/O helpers
# ---------------------------------------------------------------------------


def write_rule_file(rules: Iterable[str], path: Path) -> int:
    """Write *rules* to *path*, one rule per line (UTF-8).

    Returns the number of rules written.
    """
    rule_list = list(rules)
    path.write_text("\n".join(rule_list) + "\n", encoding="utf-8")
    return len(rule_list)


def expand_wordlist(
    plaintexts: Iterable[str],
    path: Path,
    *,
    mutate: bool = False,
) -> int:
    """Write a newline-delimited wordlist to *path* and return the line count.

    Parameters
    ----------
    plaintexts:
        Source passwords/words to include.
    path:
        Destination file (will be created or overwritten).
    mutate:
        When ``False`` (default), write only the de-duplicated source words.
        When ``True``, write the union of ``python_mutations(p)`` for every
        source word, preserving insertion order and de-duplicating globally.
    """
    seen: set[str] = set()
    ordered: list[str] = []

    for p in plaintexts:
        candidates = python_mutations(p) if mutate else [p]
        for candidate in candidates:
            if candidate not in seen:
                seen.add(candidate)
                ordered.append(candidate)

    path.write_text("\n".join(ordered) + "\n" if ordered else "", encoding="utf-8")
    return len(ordered)


# ---------------------------------------------------------------------------
# Hashcat mask generator
# ---------------------------------------------------------------------------


def walk_masks(min_len: int = 6, max_len: int = 10) -> list[str]:
    """Return a list of hashcat mask strings modelling walk-password shapes.

    Shapes generated (for each total length in [min_len, max_len]):

    - ``?l*N``           - all lowercase (pure walk base)
    - ``?u?l*(N-1)``     - one uppercase prefix + lowercase body (capitalized)
    - ``?l*(N-1)?d``     - lowercase walk + one trailing digit
    - ``?l*(N-2)?d?d``   - lowercase walk + two trailing digits
    - ``?u?l*(N-2)?d``   - capitalized walk + one digit
    - ``?l*(N-1)?s``     - lowercase walk + one trailing symbol
    - ``?u?l*(N-2)?s``   - capitalized walk + one symbol

    Only masks whose total token count falls within [min_len, max_len] are
    emitted.  The list is de-duplicated and ordered by length then shape.
    """
    seen: set[str] = set()
    result: list[str] = []

    def _add_mask(mask: str) -> None:
        token_count = mask.count("?")
        if min_len <= token_count <= max_len and mask not in seen:
            seen.add(mask)
            result.append(mask)

    for total in range(min_len, max_len + 1):
        lower_block = "?l" * total
        # all lowercase
        _add_mask(lower_block)

        # capitalized: ?u + (total-1) ?l
        if total >= 2:
            cap_block = "?u" + "?l" * (total - 1)
            _add_mask(cap_block)

        # lowercase + 1 digit
        if total >= 2:
            walk_part = "?l" * (total - 1)
            _add_mask(walk_part + "?d")

        # lowercase + 2 digits
        if total >= 3:
            walk_part = "?l" * (total - 2)
            _add_mask(walk_part + "?d?d")

        # lowercase + 4 digits (year suffix)
        if total >= 5:
            walk_part = "?l" * (total - 4)
            _add_mask(walk_part + "?d?d?d?d")

        # capitalized + 1 digit
        if total >= 3:
            walk_part = "?u" + "?l" * (total - 2)
            _add_mask(walk_part + "?d")

        # lowercase + 1 symbol
        if total >= 2:
            walk_part = "?l" * (total - 1)
            _add_mask(walk_part + "?s")

        # capitalized + 1 symbol
        if total >= 3:
            walk_part = "?u" + "?l" * (total - 2)
            _add_mask(walk_part + "?s")

    return result
