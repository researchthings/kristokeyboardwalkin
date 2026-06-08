"""Click-based command-line interface for keywalk_audit."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING

import click

from keywalk_audit import __version__
from keywalk_audit.audit import (
    audit as run_audit,
)
from keywalk_audit.audit import (
    crack_hashes,
    render_console,
    report_from_dict,
    write_csv,
    write_html,
    write_json,
    write_markdown,
    write_sarif,
    write_xlsx,
)
from keywalk_audit.hashing import (
    DEFAULT_RULES,
    CiscoType7Error,
    cisco7_decode,
    cisco7_encode,
    walk_masks,
    write_rule_file,
)
from keywalk_audit.hashing.algorithms import HASHCAT_MODES
from keywalk_audit.hashing.computer import can_compute
from keywalk_audit.hashing.mutations import python_mutations
from keywalk_audit.layouts import LAYOUTS, get_layout
from keywalk_audit.rainbow.builder import build_rainbow
from keywalk_audit.rainbow.lookup import fuzzy_lookup_geometric, fuzzy_lookup_string
from keywalk_audit.sam.autodetect import detect_format
from keywalk_audit.sam.pwdump_parser import parse_pwdump
from keywalk_audit.walks.analysis import analyze_walk, best_layout, rank_layouts
from keywalk_audit.walks.fingerprint import geometric_fingerprint
from keywalk_audit.walks.generator import generate_walks_short
from keywalk_audit.walks.patterns import generate_pattern_walks
from keywalk_audit.walks.scorer import score_walk

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence

    from keywalk_audit.audit.runner import AuditReport
    from keywalk_audit.layouts.base import Layout

# File-format writers keyed by the ``--format`` choice. Each maps to a writer
# and the suffix used when the output path has none.
_FILE_WRITERS: dict[str, tuple[Callable[[AuditReport, Path], None], str]] = {
    "json": (write_json, ".json"),
    "xlsx": (write_xlsx, ".xlsx"),
    "csv": (write_csv, ".csv"),
    "html": (write_html, ".html"),
    "md": (write_markdown, ".md"),
    "sarif": (write_sarif, ".sarif"),
}


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


def _emit_report_files(report: AuditReport, output: Path, fmt: str) -> None:
    """Write ``report`` to one or all file formats under ``output``."""
    if fmt == "all":
        for writer, suffix in _FILE_WRITERS.values():
            path = output.with_suffix(suffix)
            writer(report, path)
            click.echo(f"wrote {path}")
        return
    writer, suffix = _FILE_WRITERS[fmt]
    path = output if output.suffix else output.with_suffix(suffix)
    writer(report, path)
    click.echo(f"wrote {path}")


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
@click.option(
    "--patterns",
    is_flag=True,
    help="Also materialize structural patterns (famous walks, sweeps, zig-zags).",
)
@click.option(
    "--knight",
    is_flag=True,
    help="Include knight-move skip walks (implies --patterns; can be large).",
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
    patterns: bool,
    knight: bool,
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
        include_patterns=patterns or knight,
        pattern_knight=knight,
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
    help="Output file (suffix chosen from --format when absent).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "xlsx", "csv", "html", "md", "sarif", "console", "all"]),
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

    if fmt == "console":
        click.echo(render_console(report))
        return
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
    _emit_report_files(report, output, fmt)


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


@main.command("analyze")
@click.argument("text")
@click.option("--layout", "layout_name", default="qwerty_us", show_default=True)
@click.option("--auto", is_flag=True, help="Detect the best-fitting layout automatically.")
def cli_analyze(text: str, layout_name: str, auto: bool) -> None:
    """Print the deep walk analysis for `TEXT` (physical, finger, and repeat metrics)."""
    name = best_layout(text).layout if auto else layout_name
    layout = get_layout(name)
    analysis = analyze_walk(text, layout)
    payload = asdict(analysis)
    payload["layout_ranking"] = [
        {"layout": m.layout, "score": round(m.score, 4)} for m in rank_layouts(text)[:5]
    ]
    click.echo(json.dumps(payload, indent=2, default=list))


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


@main.command("layouts")
def cli_layouts() -> None:
    """List the registered keyboard layouts."""
    rows = []
    for name, layout in LAYOUTS.items():
        row_count = len({r for r, _ in layout.char_to_pos.values()})
        rows.append(
            {
                "name": name,
                "keys": len(layout.char_to_pos),
                "rows": row_count,
                "has_shift_map": bool(layout.shift_map),
                "has_finger_map": bool(layout.finger_map),
                "has_stagger": bool(layout.row_offsets),
            }
        )
    click.echo(json.dumps(rows, indent=2))


@main.command("algorithms")
def cli_algorithms() -> None:
    """List the hash-algorithm registry and which modes build in pure Python."""
    rows = [
        {
            "name": algo.name,
            "hashcat_mode": algo.hashcat_mode,
            "family": algo.family,
            "is_fast": algo.is_fast,
            "build_computable": can_compute(algo.name),
            "description": algo.description,
        }
        for algo in sorted(HASHCAT_MODES.values(), key=lambda a: (a.family, a.name))
    ]
    click.echo(json.dumps(rows, indent=2))


def _generate_walks(
    layout: Layout,
    lengths: range,
    max_turns: int,
    patterns: bool,
    knight: bool,
) -> Iterable[str]:
    seen: dict[str, None] = {}
    for walk in generate_walks_short(
        layout, min_len=min(lengths), max_len=max(lengths), max_turns=max_turns
    ):
        seen.setdefault(walk, None)
    if patterns or knight:
        for walk in generate_pattern_walks(
            layout, min_len=min(lengths), max_len=max(lengths), include_knight=knight
        ):
            seen.setdefault(walk, None)
    return seen.keys()


@main.command("generate")
@click.option("--layout", "layout_name", default="qwerty_us", show_default=True)
@click.option("--lengths", default="4-8", show_default=True, help="Length range like 4-8.")
@click.option("--max-turns", type=int, default=2, show_default=True)
@click.option("--patterns", is_flag=True, help="Include structural patterns.")
@click.option("--knight", is_flag=True, help="Include knight-move skip walks.")
@click.option("--min-score", type=float, default=0.0, show_default=True, help="Score filter.")
@click.option("--mutate", is_flag=True, help="Expand each walk with mutation derivatives.")
@click.option("--limit", type=int, default=None, help="Cap the number of emitted walks.")
@click.option(
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Write to a file instead of stdout.",
)
def cli_generate(
    layout_name: str,
    lengths: str,
    max_turns: int,
    patterns: bool,
    knight: bool,
    min_score: float,
    mutate: bool,
    limit: int | None,
    output: Path | None,
) -> None:
    """Emit keyboard walks for a layout as a wordlist."""
    layout = get_layout(layout_name)
    length_range = _parse_lengths(lengths)
    result: dict[str, None] = {}
    for walk in _generate_walks(layout, length_range, max_turns, patterns, knight):
        if min_score > 0.0 and score_walk(walk, layout).total < min_score:
            continue
        if mutate:
            for variant in python_mutations(walk):
                result.setdefault(variant, None)
        else:
            result.setdefault(walk, None)
        if limit is not None and len(result) >= limit:
            break
    words = list(result.keys())
    if limit is not None:
        words = words[:limit]
    if output is not None:
        output.write_text("\n".join(words) + "\n", encoding="utf-8")
        click.echo(f"wrote {len(words)} walks to {output}")
    else:
        click.echo("\n".join(words))


@main.command("decode-cisco7")
@click.argument("ciphertext")
def cli_decode_cisco7(ciphertext: str) -> None:
    """Decode a Cisco IOS Type-7 (reversible) password string."""
    try:
        click.echo(cisco7_decode(ciphertext))
    except CiscoType7Error as exc:
        raise click.ClickException(str(exc)) from exc


@main.command("encode-cisco7")
@click.argument("plaintext")
@click.option("--seed", type=int, default=0, show_default=True, help="Type-7 seed index.")
def cli_encode_cisco7(plaintext: str, seed: int) -> None:
    """Encode a plaintext as a Cisco IOS Type-7 password string."""
    try:
        click.echo(cisco7_encode(plaintext, seed))
    except CiscoType7Error as exc:
        raise click.ClickException(str(exc)) from exc


@main.command("mutations")
@click.option(
    "--rules-out",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Write the default hashcat rule set to this file.",
)
@click.option("--masks", is_flag=True, help="Print walk-shaped hashcat masks.")
@click.option("--sample", default=None, help="Print the Python mutations of a sample string.")
def cli_mutations(rules_out: Path | None, masks: bool, sample: str | None) -> None:
    """Inspect the walk-mutation rule set, masks, and sample expansions."""
    if rules_out is not None:
        count = write_rule_file(DEFAULT_RULES, rules_out)
        click.echo(f"wrote {count} rules to {rules_out}")
        return
    if masks:
        click.echo(json.dumps(walk_masks(), indent=2))
        return
    if sample is not None:
        click.echo(json.dumps(python_mutations(sample), indent=2))
        return
    click.echo(json.dumps(list(DEFAULT_RULES), indent=2))


@main.command("crack")
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
    help="DuckDB rainbow path used to seed the wordlist.",
)
@click.option(
    "--algorithm",
    type=click.Choice(["ntlm", "lm"]),
    default="ntlm",
    show_default=True,
    help="Which captured hash to target.",
)
@click.option(
    "--work-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("keywalk-crack"),
    show_default=True,
    help="Scratch directory for the wordlist, rules, and potfile.",
)
@click.option("--mutate/--no-mutate", default=True, show_default=True)
@click.option("--min-score", type=float, default=0.0, show_default=True)
@click.option("--limit", type=int, default=None, help="Cap rainbow seed candidates.")
@click.option("--timeout", type=int, default=None, help="hashcat timeout in seconds.")
def cli_crack(
    sam_file: Path,
    db_path: Path,
    algorithm: str,
    work_dir: Path,
    mutate: bool,
    min_score: float,
    limit: int | None,
    timeout: int | None,
) -> None:
    """Crack unmatched PWDUMP hashes with hashcat seeded by rainbow candidates."""
    if detect_format(sam_file) != "pwdump":
        raise click.ClickException("crack currently supports PWDUMP input only")
    entries = list(parse_pwdump(sam_file))
    if algorithm == "lm":
        targets = {e.username: e.lm_hash for e in entries}
    else:
        targets = {e.username: e.nt_hash for e in entries}
    report = crack_hashes(
        targets,
        db_path,
        work_dir,
        algorithm=algorithm,
        mutate=mutate,
        min_score=min_score,
        candidate_limit=limit,
        timeout_seconds=timeout,
    )
    click.echo(
        json.dumps(
            {
                "attempted": report.attempted,
                "hashcat_invoked": report.hashcat_invoked,
                "wordlist_size": report.wordlist_size,
                "rules_used": report.rules_used,
                "cracked": len(report.cracked),
                "accounts_cracked": [list(pair) for pair in report.accounts_cracked],
                "runtime_seconds": round(report.runtime_seconds, 4),
                "errors": list(report.errors),
            },
            indent=2,
        )
    )


@main.command("render")
@click.argument(
    "report_json",
    type=click.Path(dir_okay=False, exists=True, path_type=Path),
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "xlsx", "csv", "html", "md", "sarif", "console"]),
    default="console",
    show_default=True,
)
@click.option(
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Output file (required for file formats).",
)
def cli_render(report_json: Path, fmt: str, output: Path | None) -> None:
    """Re-render a saved JSON audit report into another format."""
    data = json.loads(report_json.read_text(encoding="utf-8"))
    report = report_from_dict(data)
    if fmt == "console":
        click.echo(render_console(report))
        return
    if output is None:
        raise click.ClickException(f"--output is required for --format {fmt}")
    _emit_report_files(report, output, fmt)


if __name__ == "__main__":
    main()
