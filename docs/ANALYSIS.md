# Walk analysis

`keywalk_audit.walks.analysis.analyze_walk` layers descriptive metrics on
top of the calibrated six-feature score. The calibrated score is left
untouched (so acceptance thresholds stay stable); these metrics are for
triage, reporting, and layout attribution. The `analyze` command emits the
whole `WalkAnalysis` as JSON, plus a layout ranking.

```
keywalk-audit analyze 1qaz2wsx3edc4rfv
keywalk-audit analyze azerty --auto      # detect the best-fitting layout
```

## Physical metrics (stagger-aware)

Using the layout's Euclidean stagger model (`LAYOUTS.md`):

- `physical_travel` -- total finger travel `\sum_i \mathrm{dist}(k_i,
  k_{i+1})` over resolved keys.
- `mean_step_distance` -- travel divided by the number of steps.
- `physical_smoothness` -- the fraction of steps whose distance is at most
  `1.6` key units (a neighbour move). Genuine walks are smooth; the three
  inter-segment jumps in `1qaz2wsx3edc4rfv` drop its smoothness to `0.80`.

## Hand and finger dynamics

From the layout finger map:

- `hands_used` -- the distinct hands touched.
- `hand_alternations` / `hand_alternation_ratio` -- consecutive pairs that
  switch hands.
- `same_finger_repeats` / `same_finger_ratio` -- consecutive pairs pressed
  by the same finger (different keys, same finger).

## Repeat structure

- `max_repeat_run` -- longest run of the identical physical key
  (`aaaa` -> 4).
- `repeat_ratio` -- fraction of consecutive pairs that press the same key.
  A pure repeat is not a walk even though its adjacency ratio is otherwise
  undefined.

## Direction structure

- `turn_count` -- direction changes along the resolved path.
- `unique_directions` -- number of distinct step vectors.

## Layout identification

`rank_layouts(text)` scores `text` against every registered layout and
returns the best fit first (ties broken by name); `best_layout(text)`
returns the single best. This attributes `azerty` to `azerty_fr` and
`qwertz` to `qwertz_de` rather than to the default US layout. The
`analyze` command always includes the top-five ranking, and `--auto`
analyses against the winner.

## Walk guessability

`walk_guess_bits` estimates the attacker search to enumerate this walk on
the layout:

$$ \\mathrm{bits} = \\log_2(\\text{key count}) + \\text{turns} \\times \\log_2 8. $$

The intuition: an attacker walking the keyboard pays for the start key plus
roughly three bits per direction change, since straight continuations are
nearly free. It is a walk-specific guessability proxy -- a near-straight
walk lives in a tiny space -- not a general password-strength score.
