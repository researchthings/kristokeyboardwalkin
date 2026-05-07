"""Walk variant transforms: shift mirror, reversal, and the variant set."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from keywalk_audit.layouts.base import Layout


def shift_mirror(plaintext: str, layout: Layout) -> str:
    """Return the shift-mirror of `plaintext`.

    Each character is replaced by the layout's shifted form when an
    unshifted form is given, or by the unshifted form when a shifted
    form is given. Characters not on the layout pass through unchanged.
    """
    out: list[str] = []
    for ch in plaintext:
        if ch in layout.shift_map:
            out.append(layout.shift_map[ch])
        elif ch in layout.inverse_shift_map:
            out.append(layout.inverse_shift_map[ch])
        else:
            out.append(ch)
    return "".join(out)


def reversal(plaintext: str) -> str:
    """Return the character-reversal of `plaintext`."""
    return plaintext[::-1]


def all_variants(plaintext: str, layout: Layout) -> set[str]:
    """Return the set of canonical walk variants for `plaintext`.

    Includes the input itself, its shift mirror, its reversal, and the
    shift mirror of its reversal. Empty strings produce {""}.
    """
    rev = reversal(plaintext)
    return {
        plaintext,
        shift_mirror(plaintext, layout),
        rev,
        shift_mirror(rev, layout),
    }
