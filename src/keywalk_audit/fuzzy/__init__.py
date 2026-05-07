"""Fuzzy hashing: geometric MinHash (direction-vector shingles) and string
MinHash (character n-gram shingles) backed by datasketch LSH."""

from __future__ import annotations

from keywalk_audit.fuzzy.geometric_minhash import GeometricMinHashIndex
from keywalk_audit.fuzzy.string_minhash import StringMinHashIndex

__all__ = ["GeometricMinHashIndex", "StringMinHashIndex"]
