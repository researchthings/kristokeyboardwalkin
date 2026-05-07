"""SAM input format autodetection.

Hive files start with the magic bytes ``regf``. Anything else is treated
as PWDUMP.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from pathlib import Path

_HIVE_MAGIC = b"regf"


def detect_format(path: Path) -> Literal["pwdump", "hive"]:
    """Return ``"hive"`` if `path` starts with ``regf``, else ``"pwdump"``."""
    with path.open("rb") as fh:
        head = fh.read(4)
    return "hive" if head == _HIVE_MAGIC else "pwdump"
