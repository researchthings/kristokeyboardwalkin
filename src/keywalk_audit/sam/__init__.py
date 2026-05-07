"""SAM ingestion: PWDUMP parsing, raw-hive parsing via impacket, and
format autodetection."""

from __future__ import annotations

from keywalk_audit.sam.autodetect import detect_format
from keywalk_audit.sam.hive_parser import HiveParseError, parse_hive
from keywalk_audit.sam.pwdump_parser import SamEntry, parse_pwdump

__all__ = ["HiveParseError", "SamEntry", "detect_format", "parse_hive", "parse_pwdump"]
