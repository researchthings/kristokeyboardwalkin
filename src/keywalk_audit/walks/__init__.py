"""Walk generation, scoring, fingerprinting, analysis, and variant expansion."""

from __future__ import annotations

from keywalk_audit.walks.analysis import (
    LayoutMatch,
    WalkAnalysis,
    analyze_walk,
    best_layout,
    rank_layouts,
)
from keywalk_audit.walks.fingerprint import geometric_fingerprint
from keywalk_audit.walks.generator import generate_walks_long, generate_walks_short
from keywalk_audit.walks.patterns import (
    FAMOUS_WALKS,
    generate_knight_walks,
    generate_pattern_walks,
)
from keywalk_audit.walks.scorer import ScoreWeights, WalkScore, score_walk
from keywalk_audit.walks.variants import all_variants, reversal, shift_mirror

__all__ = [
    "FAMOUS_WALKS",
    "LayoutMatch",
    "ScoreWeights",
    "WalkAnalysis",
    "WalkScore",
    "all_variants",
    "analyze_walk",
    "best_layout",
    "generate_knight_walks",
    "generate_pattern_walks",
    "generate_walks_long",
    "generate_walks_short",
    "geometric_fingerprint",
    "rank_layouts",
    "reversal",
    "score_walk",
    "shift_mirror",
]
