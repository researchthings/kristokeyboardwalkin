# Scoring

The walk scorer reduces a candidate plaintext `p` of length `n` into a
single value in `[0, 1]`. Six features feed a calibrated weighted sum,
clamped to the unit interval.

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

## Total

$$ T = w_{\\mathrm{adj}} f_{\\mathrm{adj}} + w_{\\mathrm{run}} f_{\\mathrm{run}} + w_{\\mathrm{ent}} f_{\\mathrm{ent}} + w_{\\mathrm{mir}} f_{\\mathrm{mir}} + w_{\\mathrm{rev}} f_{\\mathrm{rev}} + w_{\\mathrm{seg}} f_{\\mathrm{seg}}, $$

clamped to `[0, 1]`. The default weights (calibrated so that all eight
canonical reference walks score `>= 0.7` while typical random passwords
score `< 0.5`) are:

| weight | value |
|--------|-------|
| `w_adj` | 0.35 |
| `w_run` | 0.20 |
| `w_ent` | 0.10 |
| `w_mir` | 0.10 |
| `w_rev` | 0.10 |
| `w_seg` | 0.15 |

Sum: 1.00.

## Calibration evidence

The eight canonical reference walks score, in order:

1. ``1qazxsw2!QAZXSW@`` -> 0.734
2. ``1qaz2wsx!QAZ@WSX`` -> 0.801
3. ``zaq12wsxZAQ!@WSX`` -> 0.734
4. ``zaq1xsw2ZAQ!XSW@`` -> 0.801
5. ``1qaz2wsx3edc4rfv`` -> 0.707
6. ``4rfv3edc2wsx1qaz`` -> 0.707
7. ``1qazxcde3!QAZXCDE#`` -> 0.748
8. ``3edcxzaq1#EDCXZAQ!`` -> 0.748

Random passwords from a representative panel (``Tx7mP$qz``,
``h9!aB2cD``, ``correctH3rs!`` and similar) score below 0.5.
