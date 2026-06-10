# Walk patterns

`keywalk_audit.walks.generator` enumerates adjacency walks by depth-first
search under a turn budget. `keywalk_audit.walks.patterns` adds the
**structural** patterns that a turn-bounded DFS does not cleanly surface.
The rainbow builder folds them in when `build-rainbow --patterns` is set;
they are off by default so the baseline build is unchanged.

## Generators

- **Famous walks** (`FAMOUS_WALKS`, `generate_known`) -- the classics
  people actually type: `qwerty`, `asdfgh`, `zxcvbn`, `qazwsx`, `qweasd`,
  `1q2w3e4r`, `azerty`, `qwertz`, `147258`, … Each is emitted only when
  every character resolves on the target layout, so QWERTY classics are
  skipped on the keypads and `azerty` applies to AZERTY.
- **Sweeps** (`generate_sweeps`) -- every contiguous run along a physical
  row or column within the length bounds (`qwer`, `1qaz`, `asdfg`).
- **Zig-zags** (`generate_zigzags`) -- adjacent rows interleaved by
  column. Rows 0/1 of QWERTY give `…1q2w3e4r5t…` and rows 1/2 give
  `qawsedrf…`; both the top-first and bottom-first orders are emitted.
- **Interleaves** (`generate_interleaves`) -- number↔letter interleaves
  across *non-adjacent* rows and slanted column offsets, which the
  adjacent-row zig-zags miss. For each row pair (the defaults are the
  number/home, number/bottom, and top/bottom pairs) and each offset, column
  `c` contributes `grid[(top, c)] + grid[(bottom, c + offset)]`, read both
  left-to-right and right-to-left. Rows 0/2 at offset 0 give `1a2s3d4f…` and
  at offset −2 (right-to-left) give `…0k9j8h7g…`. A curated list
  (`FAMOUS_INTERLEAVES`) also pins the looser two-pair bases `1a0k`, `3d9j`,
  `2x9n` that mix a left-hand same-column pair with a right-hand offset pair.
- **Doublings** (`generate_doublings`) -- 2x and 3x repeats of a seed
  (`qweqwe`, `1qaz1qaz`) that fit under the maximum length.
- **Shift-doublings** (`generate_shift_doublings`) -- opt-in compounds of the
  form `(base * k) + (shift_mirror(base) * k)`. With `base="1a0k"` this gives
  `1a0k!A)K` (k=1), `1a0k1a0k!A)K!A)K` (k=2), and so on up to `max_len`. The
  seed pool is the interleave and sweep bases short enough that one copy plus
  its mirror fits (`_shift_doubling_seeds`), with `FAMOUS_INTERLEAVES` pinned
  first so the canonical examples are always produced. Because both `k` and the
  base length vary, the family spans many lengths (8, 16, 24, 32, …).
- **Knight moves** (`generate_knight_walks`) -- opt-in skip walks that step
  by `(±1, ±2)` / `(±2, ±1)`. These have low adjacency and can be
  numerous, so they are excluded from the default aggregator and hard
  capped (`knight_cap`).

`generate_pattern_walks` returns the de-duplicated union of the famous walks,
sweeps, zig-zags, interleaves, and doublings, each string guaranteed to lie
within `[min_len, max_len]`. Shift-doublings are folded in when
`include_shift_doublings=True` and knight moves when `include_knight=True`;
both are purely additive (the default set is a subset of the expanded one).

## Builder integration

```
keywalk-audit build-rainbow --patterns        --layouts qwerty_us --lengths 6-12
keywalk-audit build-rainbow --knight           --layouts qwerty_us   # implies --patterns
keywalk-audit build-rainbow --shift-doublings  --layouts qwerty_us --lengths 8-32  # implies --patterns
```

Each pattern walk is materialized with the same four canonical variants as
a DFS short walk (itself, its shift mirror, its reversal, and the shift
mirror of its reversal), so the famous walk `qwerty` also stores `QWERTY`,
`ytrewq`, and `YTREWQ`. Pattern seeds are **not** fed into the long-walk
composer, keeping the candidate count bounded.

## Standalone generation

The `generate` command exposes the same machinery as a wordlist source,
independent of the rainbow:

```
keywalk-audit generate --layout qwerty_us --lengths 4-8 --patterns \
    --min-score 0.6 --mutate --output walks.txt

# Emit the shift-doubled compound family (1a0k1a0k!A)K!A)K, …):
keywalk-audit generate --layout qwerty_us --lengths 8-32 --shift-doublings
```

`--min-score` filters by the calibrated walk score, and `--mutate` expands
each survivor through the walk-mutation engine (see `MUTATIONS.md`).
