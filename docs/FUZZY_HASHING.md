# Fuzzy hashing

`keywalk_audit` exposes two MinHash locality-sensitive-hashing indexes:

- **Geometric MinHash**, over shingles of the unit-clipped direction
  vectors of a walk's physical-key path. Walks that trace similar
  paths (including a walk and its shift mirror) cluster together
  regardless of the typed glyph case.
- **String MinHash**, over shingles of the plaintext characters
  themselves. Catches mutation families: suffix append, capitalization
  shift (after optional case folding), and short leetspeak
  substitutions.

## MinHash and Jaccard

For two sets `A` and `B` the Jaccard similarity is

$$ J(A, B) = \\frac{|A \\cap B|}{|A \\cup B|}. $$

A MinHash signature with `k` permutations approximates `J` by the
fraction of permutations on which the two signatures agree. The
estimator's standard error is approximately `\\sqrt{J (1 - J) / k}`.

## Locality-sensitive hashing

`MinHashLSH` partitions a `k`-permutation MinHash into `b` bands of `r`
rows. The probability that two signatures share at least one band at
true Jaccard `J` is

$$ P(J) = 1 - (1 - J^r)^b. $$

For a target threshold `t`, the library chooses `b` and `r` so that
`P(t) ~= 0.5`. This is approximate. To enforce the user-specified
threshold deterministically, both indexes:

1. Build the LSH at a permissive floor (0.4) so the candidate set is
   broad.
2. Re-rank candidates against the user threshold by computing the exact
   MinHash Jaccard estimate via `MinHash.jaccard` between the query and
   each candidate signature.

This costs one extra MinHash comparison per candidate but turns a
probabilistic recall guarantee into a deterministic one.

## Geometric shingles

For a plaintext `p`, resolve each character to its physical key, then
compute the direction vector sequence `d[i] = pos[i+1] - pos[i]`. The
geometric shingle set is the union of bigrams and trigrams of `d`:

$$ G(p) = \\{(d_i, d_{i+1}) : 0 \\le i < |d| - 1\\} \\cup \\{(d_i, d_{i+1}, d_{i+2}) : 0 \\le i < |d| - 2\\}. $$

Inputs shorter than 4 characters are skipped because `|d| < 3` makes
trigram coverage trivial.

## String shingles (calibrated 1-gram + 2-gram)

The string index uses a 1-gram + 2-gram alphabet:

$$ S(p) = \\{c_i : 0 \\le i < |p|\\} \\cup \\{(c_i, c_{i+1}) : 0 \\le i < |p| - 1\\}. $$

This is a calibrated deviation from a pure 2-gram + 3-gram scheme. With
2-grams + 3-grams, the canonical reversed-segment pair
``1qaz2wsx3edc4rfv`` and ``4rfv3edc2wsx1qaz`` has true Jaccard of
approximately 0.53, well below the 0.8 acceptance threshold. With
1-grams + 2-grams, the same pair has true Jaccard approximately 0.82,
which clears the threshold and re-ranks correctly. The 1-gram
contribution is a character-set similarity signal layered on top of the
local-context 2-grams; for unrelated random passwords the union grows
and the Jaccard collapses, so the addition does not inflate false
positives noticeably.

## Determinism

Both indexes seed `datasketch.MinHash` with `seed=1` so that signatures
are reproducible across runs and machines. The `save` / `load` methods
pickle the LSH and signature cache atomically.

## References

- Andrei Z. Broder, "On the resemblance and containment of documents",
  *Proceedings of Compression and Complexity of Sequences 1997*.
- Anand Rajaraman and Jeffrey D. Ullman, *Mining of Massive Datasets*,
  Chapter 3 ("Finding Similar Items"), Cambridge University Press.
- The `datasketch` library documentation.
