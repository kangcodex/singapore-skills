# Risk Scoring (the most important doc)

`dengue-risk-advisor-skill`'s tier math is the only piece of the skill
that is not a thin wrapper over a NEA endpoint. This document is the
authoritative source for the tier table, the decision tree, and the
workbook for the score formula.

## Tier table

| clusters_nearby | above_avg_rain | tier | recommendation |
|-----------------|----------------|------|----------------|
| 0               | False          | **low** | "Low risk. Standard outdoor precautions are sufficient." |
| 0               | True           | **moderate** | "Moderate risk. Apply DEET repellent; check NEA alerts before heading out." |
| 1–4             | True           | **moderate** | same as above |
| 1–4             | False          | **moderate** | same as above |
| 3–4             | True           | **elevated** | "Elevated risk. Postpone outdoor activity; consider an indoor alternative." |
| ≥ 5             | True           | **high** | "High risk. Strongly recommend postponing or moving indoors." |
| ≥ 5             | False          | **high** | same as above |
| any             | `None` (insufficient data) | **unknown** | "Insufficient data to score confidently. Check NEA's dengue page directly." |

**Two key rules:**

1. **High always wins.** `clusters_nearby >= 5` is `high` regardless of rain. A heavy cluster alone is enough to advise postponing.
2. **Elevated requires both cluster pressure AND rain pressure.** ≥3 clusters with normal rainfall is still `moderate` (the A. aegypti mosquito needs standing water to breed; no extra rain means no extra breeding sites).

## Risk score formula

```python
score = clusters_nearby + (3 if above_avg_rain else 0)
```

- `0–2` typically lands in `low` or `moderate`.
- `3–5` typically lands in `moderate` or `elevated`.
- `6+` typically lands in `high`.

The score is **not** the final answer — the tier is. The score is
exposed in the JSON for the agent to log / display but the user sees
only the tier + recommendation text.

## Decision tree (machine-checkable)

```
above_avg_rain is None?          → yes → tier: unknown
clusters_nearby >= 5?            → yes → tier: high
clusters_nearby >= 3 AND above?  → yes → tier: elevated
clusters_nearby >= 1?            → yes → tier: moderate
above_avg_rain is True?          → yes → tier: moderate
otherwise                        →      tier: low
```

This order matters: a `clusters=5, above_avg=False` case is `high`,
not `moderate`. The high check fires before the "≥1 cluster →
moderate" check.

## Worked examples

### Example 1: Dry week, no clusters — `low`

```
clusters_nearby = 0
current_rainfall = 0.0 mm/h         → forecast_7d = 0 mm
historical_24mo mean = 100 mm/mo    → avg_7d = 23.3 mm
historical_24mo stdev = 30 mm/mo   → std_7d = 7.0 mm
above_avg_rain = (0 > 23.3 + 7.0)  → False
tier = low
score = 0 + 0 = 0
recommendation = "Low risk. Standard outdoor precautions are sufficient."
```

### Example 2: Wet week, 3 clusters — `elevated`

```
clusters_nearby = 3
current_rainfall = 4.0 mm/h         → forecast_7d = 28 mm
historical_24mo mean = 80 mm/mo     → avg_7d = 18.7 mm
historical_24mo stdev = 25 mm/mo   → std_7d = 5.8 mm
above_avg_rain = (28 > 18.7 + 5.8) → True
tier = elevated                    (3 clusters AND above_avg_rain)
score = 3 + 3 = 6
recommendation = "Elevated risk. Postpone outdoor activity; consider an indoor alternative."
```

### Example 3: Dry week, 3 clusters — `moderate` (NOT elevated)

```
clusters_nearby = 3
current_rainfall = 0.0 mm/h         → forecast_7d = 0 mm
above_avg_rain = (0 > 18.7 + 5.8)  → False
tier = moderate                    (3 clusters, no rain pressure)
score = 3 + 0 = 3
recommendation = "Moderate risk. Apply DEET repellent; check NEA alerts before heading out."
```

This is the test case that originally had a bug — the `risk_tier`
function had `if 1 <= clusters <= 2 or above_avg` which excluded
`clusters=3, above=False`. **Fixed** — see the test
`test_3_no_rain_is_moderate`.

### Example 4: Heavy cluster density, dry week — `high`

```
clusters_nearby = 5
current_rainfall = 0.0 mm/h         → forecast_7d = 0 mm
above_avg_rain = False
tier = high                        (clusters >= 5, regardless of rain)
score = 5 + 0 = 5
recommendation = "High risk. Strongly recommend postponing or moving indoors."
```

### Example 5: Missing data — `unknown`

```
historical_24mo rows = 6           → < MIN_HISTORY_MONTHS = 12
avg_7d = None
std_7d = None
above_avg_rain = (5 > None)        → None
tier = unknown
recommendation = "Insufficient data to score confidently. Check NEA's dengue page directly."
```

The skill **never** silently downgrades to `low` when the data is
missing. This is a deliberate conservative choice.

## Drift check (for the implementer)

If you change the tier table, run this in a Python REPL:

```python
from dengue_risk_advisor import risk_tier, is_above_average_rain, risk_score

# Full tier matrix (5 cluster values × 3 rain states = 15 cases)
cases = [
    (0, False, "low"),     (0, True, "moderate"),   (0, None, "unknown"),
    (1, False, "moderate"), (1, True, "moderate"),   (1, None, "unknown"),
    (2, False, "moderate"), (2, True, "moderate"),   (2, None, "unknown"),
    (3, False, "moderate"), (3, True, "elevated"),   (3, None, "unknown"),
    (5, False, "high"),     (5, True, "high"),       (5, None, "unknown"),
    (7, True, "high"),      (7, None, "unknown"),
]
for clusters, above, expected in cases:
    actual = risk_tier(clusters, above)
    assert actual == expected, f"clusters={clusters}, above={above}: expected {expected}, got {actual}"
print("all 15 cells match spec")
```

If this script fails, the tier table has drifted from this document.
**Update the document first, then the code.**
