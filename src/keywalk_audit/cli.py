"""Click-based command-line interface for keywalk_audit."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import click

from keywalk_audit import __version__
from keywalk_audit.audit import audit as run_audit
from keywalk_audit.audit import write_json, write_xlsx
from keywalk_audit.layouts import LAYOUTS, get_layout
from keywalk_audit.rainbow.builder import build_rainbow
from keywalk_audit.rainbow.lookup import fuzzy_lookup_geometric, fuzzy_lookup_string
from keywalk_audit.walks.fingerprint import geometric_fingerprint
from keywalk_audit.walks.scorer import score_walk

if TYPE_CHECKING:
    from collections.abc import Sequence

    from keywalk_audit.layouts.base import Layout


def _split_csv(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def _parse_lengths(raw: str) -> range:
    """Parse a range like ``4-32`` or a comma list like ``4,8,12``.

    A comma list is reduced to ``range(min, max + 1)`` because the
    builder wires lengths through a single Python ``range``.
    """
    raw = raw.strip()
    if "-" in raw:
        lo_s, hi_s = raw.split("-", 1)
        lo, hi = int(lo_s), int(hi_s)
    elif "," in raw:
        items = [int(x) for x in _split_csv(raw)]
        lo, hi = min(items), max(items)
    else:
        n = int(raw)
        lo, hi = n, n
    return range(lo, hi + 1)


def _resolve_layouts(raw: str | None) -> list[Layout]:
    names: Sequence[str] = _split_csv(raw) if raw else list(LAYOUTS.keys())
    return [get_layout(name) for name in names]


@click.group(name="keywalk-audit")
@click.version_option(__version__)
@click.option("--verbose", is_flag=True, help="Enable INFO-level logging.")
def main(verbose: bool) -> None:
    """Keyboard-walk password audit tool."""
    logging.basicConfig(
        level=logging.INFO if verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


@main.command("build-rainbow")
@click.option("--rebuild", is_flag=True, help="Drop and recreate the rainbow table.")
@click.option(
    "--layouts",
    "layouts_raw",
    default=None,
    help="Comma-separated layout names. Default: all layouts.",
)
@click.option(
    "--lengths",
    default="4-16",
    show_default=True,
    help="Length range like 4-32 or comma list like 4,8,12.",
)
@click.option(
    "--algorithms",
    default="ntlm,lm",
    show_default=True,
    help="Comma-separated algorithm names.",
)
@click.option("--fast-only", is_flag=True, help="Skip slow hash algorithms.")
@click.option(
    "--db",
    "db_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=Path("rainbow.duckdb"),
    show_default=True,
    help="DuckDB file path.",
)
@click.option(
    "--workers",
    type=int,
    default=None,
    help="Worker process count (reserved for future use).",
)
@click.option(
    "--max-turns",
    type=int,
    default=2,
    show_default=True,
    help="Max direction changes per short walk.",
)
@click.option(
    "--max-segments",
    type=int,
    default=3,
    show_default=True,
    help="Max segments composed for long walks.",
)
@click.option(
    "--long-seed-cap",
    type=int,
    default=256,
    show_default=True,
    help="Cap on short-walk seeds fed to the long-walk composer.",
)
def cli_build_rainbow(
    rebuild: bool,
    layouts_raw: str | None,
    lengths: str,
    algorithms: str,
    fast_only: bool,
    db_path: Path,
    workers: int | None,
    max_turns: int,
    max_segments: int,
    long_seed_cap: int,
) -> None:
    """Build (or rebuild) the rainbow table."""
    layouts = _resolve_layouts(layouts_raw)
    length_range = _parse_lengths(lengths)
    report = build_rainbow(
        layouts=layouts,
        lengths=length_range,
        algorithms=tuple(_split_csv(algorithms)),
        db_path=db_path,
        rebuild=rebuild,
        fast_only=fast_only,
        workers=workers,
        max_turns=max_turns,
        max_segments=max_segments,
        long_seed_cap=long_seed_cap,
    )
    click.echo(
        json.dumps(
            {
                "candidates_inserted": report.candidates_inserted,
                "fingerprints_unique": report.fingerprints_unique,
                "layouts_processed": list(report.layouts_processed),
                "algorithms_processed": list(report.algorithms_processed),
                "runtime_seconds": round(report.runtime_seconds, 4),
                "errors": list(report.errors),
            },
            indent=2,
        )
    )


@main.command("audit")
@click.argument(
    "sam_file",
    type=click.Path(dir_okay=False, exists=True, path_type=Path),
)
@click.option(
    "--db",
    "db_path",
    type=click.Path(dir_okay=False, exists=True, path_type=Path),
    default=Path("rainbow.duckdb"),
    show_default=True,
    help="DuckDB file path.",
)
@click.option(
    "--threshold",
    type=float,
    default=0.7,
    show_default=True,
    help="Minimum walk score for reporting.",
)
@click.option(
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Output file (.json or .xlsx).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "xlsx", "both"]),
    default="json",
    show_default=True,
    help="Output format.",
)
@click.option(
    "--system-hive",
    type=click.Path(dir_okay=False, exists=True, path_type=Path),
    default=None,
    help="SYSTEM hive path (required when SAM_FILE is a hive).",
)
def cli_audit(
    sam_file: Path,
    db_path: Path,
    threshold: float,
    output: Path | None,
    fmt: str,
    system_hive: Path | None,
) -> None:
    """Audit a SAM dump (PWDUMP or raw hive) against the rainbow."""
    report = run_audit(
        sam_path=sam_file,
        db_path=db_path,
        threshold=threshold,
        sam_hive_path=sam_file,
        system_hive_path=system_hive,
    )

    if output is None:
        click.echo(
            json.dumps(
                {
                    "total_accounts": report.total_accounts,
                    "walk_accounts": report.walk_accounts,
                    "threshold": report.threshold,
                    "runtime_seconds": round(report.runtime_seconds, 4),
                    "errors": list(report.errors),
                },
                indent=2,
            )
        )
        return

    if fmt in {"json", "both"}:
        json_path = output if fmt == "json" else output.with_suffix(".json")
        write_json(report, json_path)
        click.echo(f"wrote {json_path}")
    if fmt in {"xlsx", "both"}:
        xlsx_path = output if fmt == "xlsx" else output.with_suffix(".xlsx")
        write_xlsx(report, xlsx_path)
        click.echo(f"wrote {xlsx_path}")


@main.command("score")
@click.argument("text")
@click.option("--layout", "layout_name", default="qwerty_us", show_default=True)
def cli_score(text: str, layout_name: str) -> None:
    """Print the walk score breakdown for `TEXT`."""
    layout = get_layout(layout_name)
    result = score_walk(text, layout)
    click.echo(
        json.dumps(
            {
                "text": text,
                "layout": layout_name,
                "total": round(result.total, 4),
                "adjacency_ratio": round(result.adjacency_ratio, 4),
                "longest_run": result.longest_run,
                "longest_run_normalized": round(result.longest_run_normalized, 4),
                "direction_entropy": round(result.direction_entropy, 4),
                "shift_mirror": result.shift_mirror,
                "reversal": result.reversal,
                "segment_count": result.segment_count,
                "segment_count_normalized": round(result.segment_count_normalized, 4),
            },
            indent=2,
        )
    )


@main.command("fingerprint")
@click.argument("text")
@click.option("--layout", "layout_name", default="qwerty_us", show_default=True)
def cli_fingerprint(text: str, layout_name: str) -> None:
    """Print the geometric fingerprint of `TEXT` on the chosen layout."""
    layout = get_layout(layout_name)
    fp = geometric_fingerprint(text, layout)
    click.echo(fp)


@main.command("fuzzy")
@click.argument("text")
@click.option(
    "--db",
    "db_path",
    type=click.Path(dir_okay=False, exists=True, path_type=Path),
    default=Path("rainbow.duckdb"),
    show_default=True,
    help="DuckDB file path.",
)
@click.option("--layout", "layout_name", default="qwerty_us", show_default=True)
@click.option("--threshold", type=float, default=0.8, show_default=True)
@click.option(
    "--kind",
    type=click.Choice(["geometric", "string", "both"]),
    default="both",
    show_default=True,
)
def cli_fuzzy(
    text: str,
    db_path: Path,
    layout_name: str,
    threshold: float,
    kind: str,
) -> None:
    """Run a fuzzy lookup against the saved LSH indexes."""
    layout = get_layout(layout_name)
    output: dict[str, list[dict[str, str | float]]] = {}
    if kind in {"geometric", "both"}:
        hits = fuzzy_lookup_geometric(db_path, text, layout, threshold=threshold)
        output["geometric"] = [
            {
                "walk_id": c.walk_id,
                "plaintext": c.plaintext,
                "score": c.score,
                "fingerprint": c.fingerprint,
            }
            for c in hits
        ]
    if kind in {"string", "both"}:
        hits = fuzzy_lookup_string(db_path, text, threshold=threshold)
        output["string"] = [
            {
                "walk_id": c.walk_id,
                "plaintext": c.plaintext,
                "score": c.score,
            }
            for c in hits
        ]
    click.echo(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
