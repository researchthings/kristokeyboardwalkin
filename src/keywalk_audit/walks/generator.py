"""Walk generators: depth-first short walks and composed long walks."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from keywalk_audit.layouts.base import Layout


def generate_walks_short(
    layout: Layout,
    min_len: int = 4,
    max_len: int = 16,
    max_turns: int = 4,
) -> Iterator[str]:
    """Yield raw walk strings via DFS over the adjacency graph.

    Walks start from every key on the layout. Repeats of a single key
    within a walk are forbidden (keeps the search bounded). A "turn" is
    counted whenever the current direction tuple differs from the
    previous one; the search prunes when the cumulative turn count
    exceeds `max_turns`.
    """
    if min_len < 2 or max_len < min_len or max_turns < 0:
        return

    keys = sorted(layout.char_to_pos.keys())
    for start in keys:
        path: list[str] = [start]
        yield from _dfs(layout, path, None, 0, min_len, max_len, max_turns)


def _dfs(
    layout: Layout,
    path: list[str],
    last_direction: tuple[int, int] | None,
    turns: int,
    min_len: int,
    max_len: int,
    max_turns: int,
) -> Iterator[str]:
    length = len(path)
    if length >= min_len:
        yield "".join(path)
    if length >= max_len:
        return

    visited = set(path)
    last_key = path[-1]
    for neighbor in layout.neighbors(last_key):
        if neighbor in visited:
            continue
        direction = layout.direction(last_key, neighbor)
        added_turn = 0 if last_direction is None or direction == last_direction else 1
        new_turns = turns + added_turn
        if new_turns > max_turns:
            continue
        path.append(neighbor)
        yield from _dfs(layout, path, direction, new_turns, min_len, max_len, max_turns)
        path.pop()


def generate_walks_long(
    layout: Layout,  # noqa: ARG001  (kept for API symmetry; future hooks may use)
    short_walks: Iterable[str],
    max_len: int = 32,
    max_segments: int = 3,
) -> Iterator[str]:
    """Yield walks composed by concatenating 2..max_segments short walks.

    The caller is responsible for feeding a tractable `short_walks` list:
    the cross-product grows as ``n ** max_segments``.
    """
    if max_segments < 2:
        return
    shorts = [w for w in short_walks if w]
    if not shorts:
        return

    for w1 in shorts:
        if len(w1) >= max_len:
            continue
        for w2 in shorts:
            combined2 = w1 + w2
            if len(combined2) > max_len:
                continue
            yield combined2
            if max_segments < 3:
                continue
            for w3 in shorts:
                combined3 = combined2 + w3
                if len(combined3) > max_len:
                    continue
                yield combined3
