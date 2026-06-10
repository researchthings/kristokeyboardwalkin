# Scoring

The walk scorer reduces a candidate plaintext `p` of length `n` into a
single value in `[0, 1]`. It recognizes two *kinds* of walk that occupy
different feature subspaces — adjacency walks (`1qaz2wsx…`) and structural
walks (low-adjacency but highly regular, such as the number↔letter compound
`1a0k1a0k!A)K!A)K`) — so it OR-combines two sub-scores:

$$ T = \\mathrm{clamp}\\bigl(\\max(T_{\\mathrm{adj}}, \\; T_{\\mathrm{struct}})\\bigr). $$

`T_adj` is the calibrated six-feature weighted sum below; `T_struct` is a
small structural sub-score (Feature 7). Taking the max means the structural
path can only *raise* a score, never lower one the adjacency model assigned,
so every walk the adjacency model accepts stays accepted.

Let `keys[i]` be the unshifted physical key for `p[i]` on the chosen
layout, and let `pos[i] = (row, col)` be its grid position. Two keys
are *adjacent* when

$$ \\bigl|\\Delta \\mathrm{row}\\bigr| \\le 1 \\;\\land\\; \\bigl|\\Delta \\mathrm{col}\\bigr| \\le 1 \\;\\land\\; \\mathrm{keys differ}. $$

Define the boolean adjacency vector `a` of length `n - 1` by
`a[i] = is_adjacent(p[i], p[i+1])`. Define direction vectors
`d[i] = pos[i+1] - pos[i]` for the same range.

## Feature 1: adjacency ratio

$$ f_{\\mathrm{adj}} = \\frac{1}{n - 1} \\sum_{i=0}^{n-2} \\mathbb{1}[a_i] $$

## Feature 2: longest run (segment-aware)

Let `R` be the longest contiguous run of `True` flags in `a`, expressed
as a character count (a streak of `k` consecutive `True` flags
corresponds to `k + 1` characters). Let `S` be the number of
contiguous adjacency runs of length at least four. The expected
segment length is

$$ \\bar{\\ell} = \\frac{n}{\\max(1, S)}, $$

and the normalized longest-run feature is

$$ f_{\\mathrm{run}} = \\min\\Bigl(1, \\; \\frac{R}{\\max(1, \\bar{\\ell})}\\Bigr). $$

This segment-aware normalization is the calibration linchpin. The
naive ``R / n`` form penalizes composed walks (such as
``1qaz2wsx3edc4rfv``) for their short individual segments. Normalizing
by the expected segment length lifts each canonical reference walk to
or above the 0.7 acceptance threshold.

## Feature 3: direction entropy

Let `c_v` be the count of direction vector `v` in `d`. The Shannon
entropy of the empirical distribution is

$$ H = -\\sum_{v} \\frac{c_v}{n - 1} \\log_2 \\frac{c_v}{n - 1}. $$

Normalize against the maximum entropy across the eight cardinal /
diagonal unit directions plus zero (`log2(9)`):

$$ f_{\\mathrm{ent}} = \\max\\Bigl(0, \\; 1 - \\frac{H}{\\log_2 9}\\Bigr). $$

Lower entropy means a more rigid walk and a higher feature value.

## Feature 4: shift mirror

For even `n`, let `h = n / 2`. The feature is 1 when the second half is
the layout's shift-mirror of the first half:

$$ f_{\\mathrm{mir}} = \\begin{cases} 1 & p[h:] = \\sigma(p[:h]) \\\\ 0 & \\text{otherwise} \\end{cases} $$

where `\\sigma` is the shift-map transform. Odd-length inputs return 0.

## Feature 5: reversal

The feature is 1 when the physical-key sequence is a palindrome:

$$ f_{\\mathrm{rev}} = \\mathbb{1}\\bigl[\\,(\\text{keys})_{0..n-1} = (\\text{keys})_{n-1..0}\\,\\bigr]. $$

## Feature 6: segment count

Let `S` be defined as in Feature 2 and let
`S_{\\max} = \\lfloor n / 4 \\rfloor` be the maximum number of disjoint
length-4 segments that can fit in `n` characters:

$$ f_{\\mathrm{seg}} = \\min\\Bigl(1, \\; \\frac{S}{\\max(1, S_{\\max})}\\Bigr). $$

## Feature 7: periodicity (structural)

Let `q` be the smallest period (`1 <= q <= n // 2`) for which the
physical-key sequence repeats — that is, `keys[i] = keys[i - q]` for all
`i >= q`. The feature is the fraction of the string explained by repetition:

$$ f_{\\mathrm{per}} = \\begin{cases} \\dfrac{n - q}{n} & q \\text{ exists} \\\\ 0 & \\text{otherwise} \\end{cases} $$

A walk built as `base * k` (any `k >= 2`) is fully periodic and scores high;
an aperiodic string scores 0. Operating on *physical* keys means a shift
mirror such as `1a0k!A)K` (keys `1a0k1a0k`) is recognized as periodic.

## Adjacency sub-score

$$ T_{\\mathrm{adj}} = w_{\\mathrm{adj}} f_{\\mathrm{adj}} + w_{\\mathrm{run}} f_{\\mathrm{run}} + w_{\\mathrm{ent}} f_{\\mathrm{ent}} + w_{\\mathrm{mir}} f_{\\mathrm{mir}} + w_{\\mathrm{rev}} f_{\\mathrm{rev}} + w_{\\mathrm{seg}} f_{\\mathrm{seg}}. $$

The default weights (calibrated so that all eight canonical reference walks
score `>= 0.7` while typical random passwords score `< 0.5`) are:

| weight | value |
|--------|-------|
| `w_adj` | 0.35 |
| `w_run` | 0.20 |
| `w_ent` | 0.10 |
| `w_mir` | 0.10 |
| `w_rev` | 0.10 |
| `w_seg` | 0.15 |

Sum: 1.00.

## Structural sub-score

$$ T_{\\mathrm{struct}} = \\mathrm{clamp}\\bigl(w'_{\\mathrm{per}} f_{\\mathrm{per}} + w'_{\\mathrm{mir}} f_{\\mathrm{mir}} + w'_{\\mathrm{ent}} f_{\\mathrm{ent}}\\bigr). $$

These weights are intentionally separate from the adjacency weights: the
sub-scores are OR-combined (`T = clamp(max(T_adj, T_struct))`), so they do not
share a unit-sum budget and `T_struct` is clamped to `[0, 1]` on its own.
`w'_mir` carries the largest weight because the shift-mirror feature is `1.0`
for the whole `(base * k) + (shift_mirror(base) * k)` family by construction,
which gives the tightest member (`k = 1` with a short base, where periodicity
is only 0.5) margin above 0.7. Random passwords carry no shift mirror and no
periodicity, so `T_struct` collapses to the small `direction_entropy` term.

| weight | value |
|--------|-------|
| `w'_per` | 0.40 |
| `w'_mir` | 0.50 |
| `w'_ent` | 0.15 |

## Total

$$ T = \\mathrm{clamp}\\bigl(\\max(T_{\\mathrm{adj}}, \\; T_{\\mathrm{struct}})\\bigr), $$

clamped to `[0, 1]`.

## Calibration evidence

The eight canonical reference walks score, in order (each is also a shift
mirror, so the structural path lifts a few slightly above their adjacency
value, but the max never drops below 0.7):

1. ``1qazxsw2!QAZXSW@`` -> 0.769
2. ``1qaz2wsx!QAZ@WSX`` -> 0.807
3. ``zaq12wsxZAQ!@WSX`` -> 0.769
4. ``zaq1xsw2ZAQ!XSW@`` -> 0.807
5. ``1qaz2wsx3edc4rfv`` -> 0.707
6. ``4rfv3edc2wsx1qaz`` -> 0.707
7. ``1qazxcde3!QAZXCDE#`` -> 0.765
8. ``3edcxzaq1#EDCXZAQ!`` -> 0.765

The shift-doubled compound family is flagged via the structural sub-score
despite near-zero key adjacency:

- ``1a0k1a0k!A)K!A)K`` -> 0.856
- ``1a2s3d4f!A@S#D$F`` -> 0.790
- ``0k9j8h7g)K(J*H&G`` -> 0.790
- ``1a0k!A)K`` (k=1, the tightest case) -> 0.758

Random passwords from a representative panel (``Tx7mP$qz``,
``h9!aB2cD``, ``correctH3rs!`` and similar) score below 0.5, with structural
sub-scores at or below ~0.03.
