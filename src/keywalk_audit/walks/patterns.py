"""Structural pattern generators beyond the adjacency-DFS short walks.

The depth-first generator in :mod:`keywalk_audit.walks.generator` enumerates
adjacency walks under a turn budget. Real corpora also contain *structural*
patterns that a turn-bounded DFS does not cleanly surface:

- **Famous walks** -- the classics people actually type (``qwerty``,
  ``qazwsx``, ``1q2w3e4r`` ...), emitted only when every character resolves on
  the target layout so they apply to the layout where they are real walks.
- **Row and column sweeps** -- contiguous runs along a physical row or column.
- **Zig-zags** -- column-interleaved patterns such as ``1q2w3e`` and
  ``qazwsxedc`` derived from adjacent row pairs.
- **Interleaves** -- number<->letter (and other row-pair) interleaves that
  zig-zag across *non-adjacent* rows and along slanted column offsets, such as
  ``1a2s3d4f`` (rows 0 and 2, offset 0) and ``0k9j8h7g`` (rows 0 and 2, offset
  -2, right-to-left). A small curated list also seeds the looser two-pair bases
  (``1a0k``, ``3d9j``, ``2x9n``).
- **Doublings** -- repeated segments such as ``qweqwe`` and ``1qaz1qaz``.
- **Shift-doublings** (opt-in) -- the compound family ``(base * k) +
  (shift_mirror(base) * k)`` (e.g. ``1a0k1a0k!A)K!A)K`` for ``base="1a0k"``,
  ``k=2``) over the structural seed pool, for ``k`` up to a cap.
- **Knight moves** (opt-in) -- skip patterns using (1,2)/(2,1) steps.

All generators yield raw strings; the builder is responsible for scoring,
fingerprinting, and variant expansion.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from keywalk_audit.walks.variants import shift_mirror

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from keywalk_audit.layouts.base import Layout

# Knight-style relative moves used by the opt-in skip-walk generator.
_KNIGHT_STEPS: tuple[tuple[int, int], ...] = (
    (1, 2),
    (1, -2),
    (-1, 2),
    (-1, -2),
    (2, 1),
    (2, -1),
    (-2, 1),
    (-2, -1),
)

# Classic keyboard walks observed across real password corpora. Each is emitted
# only on layouts where every character resolves to a key, so QWERTY classics
# are skipped on numpad/phone and vice versa.
FAMOUS_WALKS: tuple[str, ...] = (
    "qwerty",
    "qwertyui",
    "qwertyuiop",
    "asdfgh",
    "asdfghjkl",
    "zxcvbn",
    "zxcvbnm",
    "qazwsx",
    "qazwsxedc",
    "qweasd",
    "qweasdzxc",
    "qwaszx",
    "1q2w3e",
    "1q2w3e4r",
    "1qaz2wsx",
    "1qaz2wsx3edc",
    "1qaz2wsx3edc4rfv",
    "zaq12wsx",
    "poiuyt",
    "mnbvcxz",
    "lkjhgf",
    "0okm",
    "azerty",
    "azertyui",
    "qsdfgh",
    "wxcvbn",
    "qwertz",
    "147258",
    "159357",
    "123654",
)

# Row pairs interleaved by :func:`generate_interleaves`. The three defaults are
# the number<->letter combinations that a turn-bounded DFS and the adjacent-row
# zig-zags do not surface: (number row, home row), (number row, bottom row), and
# (top letter row, bottom row).
_INTERLEAVE_ROW_PAIRS: tuple[tuple[int, int], ...] = ((0, 2), (0, 3), (1, 3))

# Curated number<->letter interleave bases observed in real corpora. The first
# five are the user-reported seeds; ``1a0k`` / ``3d9j`` / ``2x9n`` mix a
# left-hand same-column pair with a right-hand offset pair and so are looser than
# any single offset sweep, which is why they are pinned here rather than left to
# :func:`generate_interleaves`. Each is emitted only when every character
# resolves on the target layout.
FAMOUS_INTERLEAVES: tuple[str, ...] = (
    "1a0k",
    "3d9j",
    "2x9n",
    "1a2s3d4f",
    "0k9j8h7g",
    "1a2s3d4f5g",
    "0l9k8j7h",
    "1q2w3e4r",
    "1z2x3c4v",
    "6h7j8k9l",
    "5t6y7u8i",
)


def rows(layout: Layout) -> dict[int, str]:
    """Return each row index mapped to its keys ordered left-to-right."""
    by_row: dict[int, list[tuple[int, str]]] = {}
    for key, (row, col) in layout.char_to_pos.items():
        by_row.setdefault(row, []).append((col, key))
    return {row: "".join(k for _, k in sorted(cells)) for row, cells in by_row.items()}


def columns(layout: Layout) -> dict[int, str]:
    """Return each column index mapped to its keys ordered top-to-bottom."""
    by_col: dict[int, list[tuple[int, str]]] = {}
    for key, (row, col) in layout.char_to_pos.items():
        by_col.setdefault(col, []).append((row, key))
    return {col: "".join(k for _, k in sorted(cells)) for col, cells in by_col.items()}


def _contiguous(text: str, min_len: int, max_len: int) -> Iterator[str]:
    """Yield every contiguous substring of ``text`` with length in range."""
    n = len(text)
    for start in range(n):
        for length in range(min_len, min(max_len, n - start) + 1):
            yield text[start : start + length]


def generate_sweeps(layout: Layout, min_len: int, max_len: int) -> Iterator[str]:
    """Yield contiguous row and column runs within the length bounds."""
    for text in (*rows(layout).values(), *columns(layout).values()):
        yield from _contiguous(text, min_len, max_len)


def generate_zigzags(layout: Layout, min_len: int, max_len: int) -> Iterator[str]:
    """Yield row-pair zig-zag walks that interleave two adjacent rows by column.

    For each adjacent row pair the keys are read column by column, alternating
    between the two rows. Rows 0 and 1 of QWERTY give ``1q2w3e4r5t...`` and rows
    1 and 2 give ``qawsedrf...``; both the top-first and bottom-first orders are
    emitted. Results longer than ``max_len`` are truncated to a leading prefix.
    """
    grid: dict[tuple[int, int], str] = {pos: key for key, pos in layout.char_to_pos.items()}
    row_indices = sorted({row for row, _ in grid})
    for top in row_indices:
        bottom = top + 1
        if bottom not in row_indices:
            continue
        cols = sorted({col for (row, col) in grid if row in (top, bottom)})
        for first, second in ((top, bottom), (bottom, top)):
            out: list[str] = []
            for col in cols:
                for row in (first, second):
                    key = grid.get((row, col))
                    if key is not None:
                        out.append(key)
            text = "".join(out)[:max_len]
            if len(text) >= min_len:
                yield text


def generate_interleaves(
    layout: Layout,
    min_len: int,
    max_len: int,
    *,
    row_pairs: Iterable[tuple[int, int]] = _INTERLEAVE_ROW_PAIRS,
    offsets: Iterable[int] = range(-3, 4),
) -> Iterator[str]:
    """Yield number<->letter interleaves across non-adjacent rows and offsets.

    For each ``(top, bottom)`` row pair and column ``offset``, each column ``c``
    contributes ``grid[(top, c)] + grid[(bottom, c + offset)]`` when both keys
    exist. Reading the columns left-to-right and right-to-left yields, for the
    ``(0, 2)`` pair, ``1a2s3d4f...`` at offset 0 and ``...0k9j8h7g...`` at offset
    -2. Every contiguous run within ``[min_len, max_len]`` is emitted, so the
    user-reported bases ``1a2s3d4f`` and ``0k9j8h7g`` appear as substrings.
    Row pairs absent on the layout (e.g. on the keypads) are skipped.
    """
    if min_len < 2 or max_len < min_len:
        return
    grid: dict[tuple[int, int], str] = {pos: key for key, pos in layout.char_to_pos.items()}
    row_indices = {row for row, _ in grid}
    cols = sorted({col for _, col in grid})
    seen: set[str] = set()
    for top, bottom in row_pairs:
        if top not in row_indices or bottom not in row_indices:
            continue
        for offset in offsets:
            for column_order in (cols, list(reversed(cols))):
                out: list[str] = []
                for c in column_order:
                    top_key = grid.get((top, c))
                    bottom_key = grid.get((bottom, c + offset))
                    if top_key is not None and bottom_key is not None:
                        out.append(top_key)
                        out.append(bottom_key)
                for text in _contiguous("".join(out), min_len, max_len):
                    if text not in seen:
                        seen.add(text)
                        yield text


def generate_doublings(seeds: Iterable[str], max_len: int) -> Iterator[str]:
    """Yield 2x and 3x repetitions of each seed within ``max_len``."""
    for seed in seeds:
        if not seed:
            continue
        doubled = seed * 2
        if len(doubled) <= max_len:
            yield doubled
        tripled = seed * 3
        if len(tripled) <= max_len:
            yield tripled


def generate_shift_doublings(
    seeds: Iterable[str],
    layout: Layout,
    max_len: int,
    *,
    max_reps: int = 4,
) -> Iterator[str]:
    """Yield the ``(seed * k) + (shift_mirror(seed) * k)`` compound family.

    For each seed and each repetition count ``k`` in ``1..max_reps``, the base
    is repeated ``k`` times and followed by ``k`` copies of its shift mirror, so
    ``seed="1a0k"`` produces ``1a0k!A)K`` (k=1), ``1a0k1a0k!A)K!A)K`` (k=2), and
    so on, up to ``max_len``. Seeds whose shift mirror equals the seed (no
    shiftable characters) are skipped: their compound is a plain doubling that
    :func:`generate_doublings` already covers. Results are de-duplicated.
    """
    if max_reps < 1:
        return
    seen: set[str] = set()
    for seed in seeds:
        if not seed:
            continue
        mirror = shift_mirror(seed, layout)
        if mirror == seed:
            continue
        for k in range(1, max_reps + 1):
            compound = seed * k + mirror * k
            if len(compound) > max_len:
                break
            if compound not in seen:
                seen.add(compound)
                yield compound


def generate_known(layout: Layout, min_len: int, max_len: int) -> Iterator[str]:
    """Yield the famous walks that fully resolve on ``layout`` and fit length."""
    for walk in FAMOUS_WALKS:
        if min_len <= len(walk) <= max_len and all(layout.has_key(c) for c in walk):
            yield walk


def generate_knight_walks(
    layout: Layout,
    min_len: int,
    max_len: int,
    cap: int = 5000,
) -> Iterator[str]:
    """Yield up to ``cap`` skip-walks that move by knight steps over the grid.

    Knight walks are speculative (low adjacency) and potentially numerous, so
    this generator is opt-in and hard-capped. Single-key revisits are forbidden.
    """
    if min_len < 2 or max_len < min_len or cap <= 0:
        return
    pos_to_key = {pos: key for key, pos in layout.char_to_pos.items()}
    emitted = 0
    starts = sorted(layout.char_to_pos.keys())
    for start in starts:
        stack: list[tuple[list[str], set[str]]] = [([start], {start})]
        while stack:
            if emitted >= cap:
                return
            path, visited = stack.pop()
            if len(path) >= min_len:
                yield "".join(path)
                emitted += 1
                if emitted >= cap:
                    return
            if len(path) >= max_len:
                continue
            row, col = layout.char_to_pos[layout.physical_key(path[-1])]
            for d_row, d_col in _KNIGHT_STEPS:
                nxt = pos_to_key.get((row + d_row, col + d_col))
                if nxt is not None and nxt not in visited:
                    stack.append(([*path, nxt], visited | {nxt}))


def _shift_doubling_seeds(
    layout: Layout,
    interleaves: Iterable[str],
    sweeps: Iterable[str],
    max_len: int,
    *,
    cap: int = 256,
) -> list[str]:
    """Select the seed pool fed to :func:`generate_shift_doublings`.

    Only bases short enough that one copy plus its mirror fits inside
    ``max_len`` (``len <= max_len // 2``) are useful. The curated
    ``FAMOUS_INTERLEAVES`` that resolve on the layout are pinned to the front so
    the canonical examples are always produced; the remaining interleave and
    sweep bases are de-duplicated, sorted shortest-first, and capped.
    """
    cap_len = max(2, max_len // 2)
    curated = [
        w
        for w in FAMOUS_INTERLEAVES
        if all(layout.has_key(c) for c in w) and 2 <= len(w) <= cap_len
    ]
    pool: list[str] = list(curated)
    seen: set[str] = set(curated)
    extra: list[str] = []
    for seed in (*interleaves, *sweeps):
        if 2 <= len(seed) <= cap_len and seed not in seen:
            seen.add(seed)
            extra.append(seed)
    extra.sort(key=len)
    return pool + extra[:cap]


def generate_pattern_walks(
    layout: Layout,
    min_len: int = 4,
    max_len: int = 16,
    *,
    include_knight: bool = False,
    knight_cap: int = 5000,
    include_shift_doublings: bool = False,
    shift_doubling_reps: int = 4,
) -> Iterator[str]:
    """Yield the de-duplicated union of structural patterns for ``layout``.

    Combines famous walks, row/column sweeps, zig-zags, number<->letter
    interleaves, and doublings. When ``include_shift_doublings`` is set the
    structural seed pool is also expanded into the ``(base * k) +
    (shift_mirror(base) * k)`` compound family (``k`` up to
    ``shift_doubling_reps``); when ``include_knight`` is set knight-move skip
    walks are added. Each string is emitted once within ``[min_len, max_len]``.
    """
    if min_len < 2 or max_len < min_len:
        return
    seen: set[str] = set()

    def _emit(text: str) -> Iterator[str]:
        if min_len <= len(text) <= max_len and text not in seen:
            seen.add(text)
            yield text

    sweep_seeds: list[str] = []
    for text in generate_sweeps(layout, min_len, max_len):
        sweep_seeds.append(text)
        yield from _emit(text)
    for text in generate_zigzags(layout, min_len, max_len):
        yield from _emit(text)
    for text in generate_known(layout, min_len, max_len):
        yield from _emit(text)

    # Curated interleaves are tracked as seeds even when shorter than min_len so
    # they can feed the shift-doubling compounds; only those within bounds emit.
    interleave_seeds: list[str] = [
        walk for walk in FAMOUS_INTERLEAVES if all(layout.has_key(c) for c in walk)
    ]
    for walk in interleave_seeds:
        yield from _emit(walk)
    for text in generate_interleaves(layout, min_len, max_len):
        interleave_seeds.append(text)
        yield from _emit(text)

    doubling_seeds = [s for s in sweep_seeds if len(s) <= max_len // 2][:128]
    for text in generate_doublings(doubling_seeds, max_len):
        yield from _emit(text)

    if include_shift_doublings:
        sd_seeds = _shift_doubling_seeds(layout, interleave_seeds, sweep_seeds, max_len)
        for text in generate_shift_doublings(
            sd_seeds, layout, max_len, max_reps=shift_doubling_reps
        ):
            yield from _emit(text)

    if include_knight:
        for text in generate_knight_walks(layout, min_len, max_len, knight_cap):
            yield from _emit(text)
