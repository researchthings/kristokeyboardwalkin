"""SAM and SYSTEM hive parser, wrapping impacket's secretsdump helpers.

The parser produces the same ``SamEntry`` shape as the PWDUMP parser so
audit code can treat both sources uniformly.

Implementation note: impacket's ``SAMHashes.dump`` writes pwdump-style
lines to its ``__output`` file or stdout. To capture them we register a
``perSecretCallback`` that receives each fully-formatted secret string,
which we then parse with our own pwdump parser.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

from impacket.examples.secretsdump import LocalOperations, SAMHashes

from keywalk_audit.sam.pwdump_parser import SamEntry, parse_pwdump

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger(__name__)


class HiveParseError(RuntimeError):
    """Raised when SAM/SYSTEM hive parsing fails before yielding any entries."""


def parse_hive(sam_path: Path, system_path: Path) -> Iterator[SamEntry]:
    """Yield SamEntry rows parsed from a SAM hive (with its SYSTEM hive)."""
    if not sam_path.exists():
        raise HiveParseError(f"SAM hive not found: {sam_path}")
    if not system_path.exists():
        raise HiveParseError(f"SYSTEM hive not found: {system_path}")

    try:
        local_ops: Any = LocalOperations(str(system_path))
        boot_key: bytes = local_ops.getBootKey()
    except Exception as exc:
        raise HiveParseError(f"failed to extract boot key from SYSTEM: {exc}") from exc

    with tempfile.TemporaryDirectory() as tmp:
        out_path = Path(tmp) / "samhashes.pwdump"
        try:
            sam: Any = SAMHashes(str(sam_path), boot_key, isRemote=False, perSecretCallback=None)
            sam.dump()
            sam.export(str(out_path).removesuffix(".pwdump"))
        except Exception as exc:
            raise HiveParseError(f"failed to dump SAM hashes: {exc}") from exc

        if out_path.exists():
            yield from parse_pwdump(out_path)
            return

        # Some impacket versions name the output without a trailing extension.
        for candidate in Path(tmp).iterdir():
            if candidate.is_file():
                yield from parse_pwdump(candidate)
                return

    raise HiveParseError("SAMHashes.export produced no output file")
