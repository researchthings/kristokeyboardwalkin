"""Geometric MinHash index over direction-vector shingles.

Each walk's physical-key direction sequence is shingled into bigrams and
trigrams. The resulting MinHash signature is added to a `MinHashLSH`
keyed by `walk_id`. Walks that trace similar physical paths cluster
together, regardless of shift state, because shift mirrors share the
same direction sequence.
"""

from __future__ import annotations

import pickle
from typing import TYPE_CHECKING, Any, cast

from datasketch import MinHash, MinHashLSH

if TYPE_CHECKING:
    from pathlib import Path

    from keywalk_audit.layouts.base import Layout

_MIN_INDEX_LEN = 4
_MINHASH_SEED = 1
# The LSH banding approximation can miss true matches near a high threshold.
# We index at a permissive LSH threshold, then re-rank candidates against the
# user's threshold using the exact MinHash Jaccard estimate.
_LSH_FLOOR = 0.4


def _direction_sequence(plaintext: str, layout: Layout) -> list[tuple[int, int]]:
    keys = [layout.physical_key(c) for c in plaintext]
    out: list[tuple[int, int]] = []
    for i in range(len(keys) - 1):
        a, b = keys[i], keys[i + 1]
        if a not in layout.char_to_pos or b not in layout.char_to_pos:
            continue
        out.append(layout.direction(a, b))
    return out


def _shingles(directions: list[tuple[int, int]]) -> set[bytes]:
    shingles: set[bytes] = set()
    for size in (2, 3):
        if len(directions) < size:
            continue
        for i in range(len(directions) - size + 1):
            window = directions[i : i + size]
            shingles.add(repr(window).encode("ascii"))
    return shingles


class GeometricMinHashIndex:
    """LSH-backed MinHash index over direction-vector shingles."""

    def __init__(self, num_perm: int = 128, threshold: float = 0.8) -> None:
        self._num_perm = num_perm
        self._threshold = threshold
        lsh_threshold = min(threshold, _LSH_FLOOR)
        self._lsh: MinHashLSH = MinHashLSH(threshold=lsh_threshold, num_perm=num_perm)
        self._signatures: dict[str, MinHash] = {}

    @property
    def num_perm(self) -> int:
        return self._num_perm

    @property
    def threshold(self) -> float:
        return self._threshold

    def __contains__(self, walk_id: str) -> bool:
        return walk_id in self._signatures

    def __len__(self) -> int:
        return len(self._signatures)

    def _build_minhash(self, plaintext: str, layout: Layout) -> MinHash | None:
        if len(plaintext) < _MIN_INDEX_LEN:
            return None
        directions = _direction_sequence(plaintext, layout)
        shingle_set = _shingles(directions)
        if not shingle_set:
            return None
        m = MinHash(num_perm=self._num_perm, seed=_MINHASH_SEED)
        for shingle in shingle_set:
            m.update(shingle)
        return m

    def add(self, walk_id: str, plaintext: str, layout: Layout) -> None:
        """Insert `walk_id` keyed by the geometric signature of `plaintext`.

        Inputs shorter than the minimum (4 chars) are silently skipped.
        Re-adding an existing `walk_id` is rejected by the underlying LSH.
        """
        m = self._build_minhash(plaintext, layout)
        if m is None or walk_id in self._signatures:
            return
        self._lsh.insert(walk_id, m)
        self._signatures[walk_id] = m

    def query(self, plaintext: str, layout: Layout) -> list[str]:
        """Return walk IDs whose MinHash Jaccard meets `self.threshold`.

        Candidates are gathered from the LSH (which uses a permissive
        internal threshold) and then re-ranked by the exact MinHash
        Jaccard estimate so the configured threshold is enforced.
        """
        m = self._build_minhash(plaintext, layout)
        if m is None:
            return []
        candidates = cast("list[str]", self._lsh.query(m))
        result: list[str] = []
        for walk_id in candidates:
            sig = self._signatures.get(walk_id)
            if sig is None:
                continue
            if float(m.jaccard(sig)) >= self._threshold:
                result.append(walk_id)
        result.sort()
        return result

    def save(self, path: Path) -> None:
        payload: dict[str, Any] = {
            "num_perm": self._num_perm,
            "threshold": self._threshold,
            "lsh": self._lsh,
            "signatures": self._signatures,
        }
        with path.open("wb") as fh:
            pickle.dump(payload, fh, protocol=pickle.HIGHEST_PROTOCOL)

    @classmethod
    def load(cls, path: Path) -> GeometricMinHashIndex:
        with path.open("rb") as fh:
            payload = cast("dict[str, Any]", pickle.load(fh))
        idx = cls(num_perm=int(payload["num_perm"]), threshold=float(payload["threshold"]))
        idx._lsh = cast("MinHashLSH", payload["lsh"])
        idx._signatures = cast("dict[str, MinHash]", payload["signatures"])
        return idx
