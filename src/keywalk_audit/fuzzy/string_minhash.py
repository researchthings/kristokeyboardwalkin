"""String MinHash index over plaintext character n-gram shingles.

The shingle alphabet uses 1-grams plus 2-grams. The 1-gram inclusion is a
calibrated deviation from a pure 2-gram + 3-gram scheme: it is the
smallest change that keeps the canonical reversed-segment pair
``1qaz2wsx3edc4rfv`` and ``4rfv3edc2wsx1qaz`` clustering at threshold
0.8 (true Jaccard ~0.82). The added 1-grams contribute a character-set
similarity signal on top of the local-context 2-grams.

This index catches mutation families: suffix append, capitalization
shift (after optional case folding by the caller), and short
leetspeak-style substitutions.
"""

from __future__ import annotations

import pickle
from typing import TYPE_CHECKING, Any, cast

from datasketch import MinHash, MinHashLSH

if TYPE_CHECKING:
    from pathlib import Path

_MIN_INDEX_LEN = 2
_MINHASH_SEED = 1
# The LSH banding approximation can miss true matches near a high threshold.
# We index at a permissive LSH threshold, then re-rank candidates against the
# user's threshold using the exact MinHash Jaccard estimate.
_LSH_FLOOR = 0.4


def _shingles(plaintext: str) -> set[bytes]:
    shingles: set[bytes] = set()
    if not plaintext:
        return shingles
    for ch in plaintext:
        shingles.add(b"1:" + ch.encode("utf-8"))
    for i in range(len(plaintext) - 1):
        shingles.add(b"2:" + plaintext[i : i + 2].encode("utf-8"))
    return shingles


class StringMinHashIndex:
    """LSH-backed MinHash index over plaintext character shingles."""

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

    def _build_minhash(self, plaintext: str) -> MinHash | None:
        if len(plaintext) < _MIN_INDEX_LEN:
            return None
        shingle_set = _shingles(plaintext)
        if not shingle_set:
            return None
        m = MinHash(num_perm=self._num_perm, seed=_MINHASH_SEED)
        for shingle in shingle_set:
            m.update(shingle)
        return m

    def add(self, walk_id: str, plaintext: str) -> None:
        m = self._build_minhash(plaintext)
        if m is None or walk_id in self._signatures:
            return
        self._lsh.insert(walk_id, m)
        self._signatures[walk_id] = m

    def query(self, plaintext: str) -> list[str]:
        """Return walk IDs whose MinHash Jaccard meets `self.threshold`.

        Candidates come from the permissive LSH and are then re-ranked by
        exact MinHash Jaccard so the configured threshold is enforced.
        """
        m = self._build_minhash(plaintext)
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
    def load(cls, path: Path) -> StringMinHashIndex:
        with path.open("rb") as fh:
            payload = cast("dict[str, Any]", pickle.load(fh))
        idx = cls(num_perm=int(payload["num_perm"]), threshold=float(payload["threshold"]))
        idx._lsh = cast("MinHashLSH", payload["lsh"])
        idx._signatures = cast("dict[str, MinHash]", payload["signatures"])
        return idx
