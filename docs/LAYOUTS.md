# Keyboard layouts

A `Layout` is a frozen dataclass mapping characters to physical-key
positions, with optional shift, stagger, and finger metadata. The
geometric model has two deliberately separate layers.

## Layer 1: the logical integer grid

`char_to_pos` maps each unshifted key to an integer `(row, col)` where
**columns align across rows**. On QWERTY US the keys `1`, `q`, `a`, `z`
share column 1 so a vertical walk like `1qaz` reads as a straight line.

All of the stable contract runs on this layer:

- `is_adjacent(a, b)` is true when `|Δrow| <= 1` and `|Δcol| <= 1` and the
  keys differ.
- `direction(a, b)` returns the integer step vector `(Δrow, Δcol)`.
- `neighbors(c)` returns the (sorted) eight-neighbourhood.

The scorer, fingerprint, and fuzzy indexes use only this layer, so the
calibrated acceptance thresholds never move when a layout gains physical
metadata.

## Layer 2: the physical stagger model

`row_offsets` shifts each row horizontally by a fractional key unit,
approximating the real row stagger of a physical board. The QWERTY family
uses

| row | keys | offset |
|-----|------|--------|
| 0 | number row | 0.00 |
| 1 | `qwerty…` | 0.50 |
| 2 | `asdf…` (home) | 0.75 |
| 3 | `zxcv…` | 1.25 |

`physical_pos(c)` returns `(row, col + offset)` and `euclidean_distance(a,
b)` is the stagger-aware key distance. These feed
`keywalk_audit.walks.analysis` (physical travel, smoothness) and never the
calibrated score. The offsets are an explicit approximation: what matters
is that the stagger increases monotonically down the board, placing `Q`
about half a unit right of `1` and `Z` about half a unit right of `A`.

## Finger map

`finger_map` assigns each physical key to a touch-typing finger
(`left_pinky` … `right_pinky`, `thumb`). `hand_of(c)` derives the hand
("left"/"right"/"thumb"). Layouts that relocate letters onto the ANSI key
positions (Dvorak, Colemak, QWERTZ, AZERTY) build their finger map from
`fingers_for_positions`, so each key keeps the finger of its **position**:
a left-pinky position is a left-pinky key regardless of which glyph the
layout paints on it.

## Registered layouts

| name | notes |
|------|-------|
| `qwerty_us` | ANSI US, the reference layout |
| `qwerty_uk` | ISO UK; `@` is Shift-`'`, dedicated `#` and `\` keys |
| `qwerty_intl` | US-International; identical physical grid to US |
| `qwertz_de` | German; Y/Z swapped, umlauts `ü ö ä`, `ß` |
| `azerty_fr` | French; `azerty` top row, digits are shifted glyphs |
| `dvorak` | Dvorak Simplified; letters relocated on the ANSI grid |
| `colemak` | Colemak; letters relocated on the ANSI grid |
| `numpad` | computer numeric keypad, `7 8 9` on top, `0` at the bottom |
| `phone_keypad` | telephone keypad, `1 2 3` on top, `0` at the bottom |

### Phone keypad vs. numpad

The phone keypad is the **vertical inverse** of the numeric keypad. This
is not cosmetic: the PIN `1470` is a clean top-to-bottom column walk on a
phone (adjacency 1.0) but a non-walk on a numpad (adjacency 0.67), because
`1` sits at opposite ends of the two devices. Auditing PIN corpora against
the wrong keypad silently misses walks.

## AZERTY number row

On AZERTY the unshifted top row yields `& é " ' ( - è _ ç à`; the digits
`1`-`0` require Shift. The layout encodes the digits in the shift map, so a
numeric walk such as `1234` resolves to the same physical keys a French
user actually presses, and `azerty` itself scores as the clean horizontal
walk it is.

## Adding a layout

1. Create `src/keywalk_audit/layouts/<name>.py` with a `_CHAR_TO_POS`
   integer grid, a `_build_shift_map`, and (optionally) `row_offsets` and a
   finger map. Layouts that share the ANSI key positions can call
   `fingers_for_positions(_CHAR_TO_POS)`.
2. Register the instance in `layouts/__init__.py` (`LAYOUTS` and
   `__all__`).
3. Add coverage in `tests/test_layouts.py`.
