# ADR-005: 8-bit unicode sparkline (no chart library)

## Status
Accepted

## Date
2026-06-22

## Context

`property-advisor-skill` v2 returns a `trend` block per mode: last 8
quarters, qoq delta, yoy delta, and **a visual indicator of direction**.
The user reads the result in an agent transcript — no browser, no
graph widget, no image rendering.

Options for the visual indicator:

1. ASCII art: `^^^vvv^^^` — works everywhere but ugly.
2. SVG / PNG / base64 image: requires an image-rendering agent
   context; not always available.
3. Unicode block characters `▁▂▃▄▅▆▇█` (U+2581–U+2588) — 8
   fixed-height bars, render in any terminal / markdown / chat UI.
4. Chart library (matplotlib, plotly, asciichart) — adds a heavy
   dependency, often with a binary install, contradicts the
   stdlib-only project constraint.

The user explicitly asked for "a small inline trend visualization" in
the design phase. The block characters are well-supported, render in
the same width as a digit, and have a natural 8-bins semantic that
maps to 8 quarters.

## Decision

Use the 8 unicode block characters `▁▂▃▄▅▆▇█` (U+2581 through
U+2588), exposed as `SPARKLINE_BINS = "▁▂▃▄▅▆▇█"` in the canonical
client. The `sparkline(values)` function maps values to bins by
equal-width division of the min-max range:

```python
def sparkline(values):
    if not values:
        return ""
    lo, hi = min(values), max(values)
    if hi == lo:
        return SPARKLINE_BINS[0] * len(values)
    spread = hi - lo
    n = len(SPARKLINE_BINS)
    return "".join(
        SPARKLINE_BINS[min(n - 1, int((v - lo) / spread * n))]
        for v in values
    )
```

The output is always 8 characters (one per quarter) for the
`trend.sparkline` field. A flat series (all values equal) renders as
`████████` (all-low) — the most honest visualisation of "no change".

## Alternatives Considered

### matplotlib / plotly SVG
- Pros: Pretty in a browser.
- Cons: Heavy dependency (matplotlib is ~50 MB installed); the agent
  pipeline can't render images in most contexts; contradicts the
  stdlib-only constraint.
- Rejected.

### asciichart (PyPI)
- Pros: Pure-Python, ASCII output.
- Cons: Adds a dep for what is 10 lines of code; uses `▁▂▃` but
  with different binning; the agent prompt installs might not include
  it.
- Rejected.

### ASCII up/down arrows `↑→↓`
- Pros: Universally supported.
- Cons: Only 3 bins (up / flat / down) — not enough to show 8 quarters
  of shape.
- Rejected: too coarse.

## Consequences

- **Pos:** Zero dependencies. Stdlib only.
- **Pos:** Renders correctly in any modern terminal, any markdown
  viewer, any chat UI that supports unicode.
- **Pos:** 8 bins is a natural fit for 8 quarters of data.
- **Pos:** `flat` case (all values equal) renders as `████████` —
  the most honest visualisation of "no change".
- **Neg:** Older terminals (Windows cmd.exe pre-Win10, some embedded
  serial consoles) may render the block characters as boxes. The
  fallback is unreadable; the rest of the JSON output is still
  valid.
- **Neg:** Equal-width binning hides outliers. A series `[10, 10,
  10, 10, 10, 10, 10, 100]` renders `▁▁▁▁▁▁▁█` — the first 7
  quarters look identical. This is the right call for a 2-year
  sparkline (a single outlier shouldn't dominate the visual).
- **Neg:** Block characters are not screen-reader-friendly. The
  text-based qoq_pct + yoy_pct + last_8_quarters JSON fields carry
  the same information; the sparkline is a redundant visual cue,
  not the only signal.

## Follow-on

- If a future skill needs a 16-bin or 32-bin sparkline (e.g. monthly
  data over 24 months), the function would need to be generalised.
  Documented in the docstring: "for 8 bins, use `SPARKLINE_BINS`;
  for custom bin counts, build a new bins string and call the same
  logic".
