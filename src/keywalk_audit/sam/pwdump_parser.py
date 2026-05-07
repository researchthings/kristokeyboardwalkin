"""PWDUMP-format parser.

Each line is ``username:rid:lm_hash:nt_hash:::``. Blank lines and
comment lines (starting with ``#``) are skipped. Malformed lines are
skipped with a warning rather than aborting the whole file.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SamEntry:
    """A SAM account row, common to PWDUMP and hive parsers."""

    username: str
    rid: int
    lm_hash: str
    nt_hash: str


def parse_pwdump(path: Path) -> Iterator[SamEntry]:
    """Yield SamEntry rows parsed from a PWDUMP file at `path`."""
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line_no, raw in enumerate(fh, start=1):
            line = raw.rstrip("\r\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split(":")
            if len(parts) < 4:
                logger.warning("pwdump line %d malformed (too few fields): %r", line_no, line)
                continue
            username, rid_str, lm_hash, nt_hash = parts[0], parts[1], parts[2], parts[3]
            try:
                rid = int(rid_str)
            except ValueError:
                logger.warning("pwdump line %d has non-integer RID: %r", line_no, rid_str)
                continue
            yield SamEntry(
                username=username,
                rid=rid,
                lm_hash=lm_hash.lower(),
                nt_hash=nt_hash.lower(),
            )
