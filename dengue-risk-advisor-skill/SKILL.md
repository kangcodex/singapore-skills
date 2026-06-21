---
name: dengue-risk-advisor-skill
description: "Assess dengue risk for a planned outdoor activity in Singapore by combining NEA active cluster density, 7-day rainfall forecast vs. 24-month historical mean, and current PSI. Use when the user mentions dengue, mosquito, vector-borne, Aedes, fogging, or asks 'is it safe to [outdoor activity] in [town] this [date]?'."
---

# dengue-risk-advisor

Combine NEA dengue cluster density with rainfall pressure to score outdoor
activity risk for a given town and date.

## Quick Start

```bash
# CLI
python3 scripts/dengue_risk_advisor.py --town "Bedok" --activity "morning jog" --date 2026-06-28

# Programmatic
python3 -c "from dengue_risk_advisor import assess; print(assess('Bedok', 'morning jog', '2026-06-28'))"
```

CLI prints JSON:

```json
{
  "town": "Bedok",
  "activity": "morning jog",
  "date": "2026-06-28",
  "dengue_clusters_nearby": 2,
  "rainfall_forecast_mm_7d": 35.0,
  "rainfall_history_avg_mm_7d": 21.0,
  "psi": {"national": 38, "tier": "good"},
  "risk_score": 4,
  "risk_tier": "moderate",
  "recommendation": "Moderate risk. Apply DEET repellent; check NEA alerts."
}
```

## Installation

1. Drop this folder under any `skills/` directory loaded by your agent.
2. Install the shared client (one-time):
   ```bash
   # Inside the skill folder, scripts/singapore_api.py is a per-skill
   # copy kept in sync with the canonical at the repo root.
   # No extra step needed if the per-skill copy exists.
   ```
3. The skill uses no pip dependencies — stdlib + the bundled `singapore_api.py`.

## Workflow

1. **Resolve the town.** Caller passes `--town`. We trust the town string
   directly (no geocoding needed — clusters are tagged by town).
2. **Pull NEA dengue clusters** within ~1 km of the town centroid via
   `fetch_dengue_clusters()` (CKAN, NEA, public, no auth).
3. **Compute 7-day rainfall forecast** by extrapolating `fetch_rainfall()`
   reading (current) × 7. We don't have a real 7-day forecast API; this
   is a deliberately conservative estimate.
4. **Compute 7-day historical average** from `fetch_nea_historical_rainfall(months=24)`:
   `mean(monthly_mm) * 7 / 30`. σ from the same 24 values × 7 / 30.
5. **"Above-average rain"** = `forecast_7d > avg_7d + σ_7d`.
6. **Pull current PSI** for context (not used in tier math but in the
   recommendation text).
7. **Apply tier matrix** (see `references/risk-scoring.md`).

## Data Sources

| Source | Used as | Fetch helper | Auth |
|--------|---------|--------------|------|
| NEA dengue clusters | nearby cluster count | `fetch_dengue_clusters()` | public |
| NEA historical rainfall | 24-month baseline | `fetch_nea_historical_rainfall()` | public |
| NEA current rainfall | forecast proxy | `fetch_rainfall()` | public |
| NEA PSI | recommendation context | `fetch_psi()` | public |

All four sources work **without `DATA_GOV_SG_API_KEY`**. No v2 fallback
needed.

## Hardening (decision rules)

1. **Town string is case-insensitive.** "BEDOK" / "bedok" / "Bedok"
   all match. The NEA dataset uses Title-case.
2. **"Above-average rain" requires 24 months of data.** If fewer than
   12 months are returned, `rainfall_history_avg_mm_7d = null` and the
   skill uses the **moderate** tier (never silently downgrades to
   "low" just because we have no baseline).
3. **Cluster count is always reported, even if 0.** The user wants
   transparency — "0 clusters within 1 km" is meaningful.
4. **Empty `result.records` is "low clusters" not "unknown clusters".**
   The skill treats empty as a true zero.
5. **Risk score is `clusters + (3 if above_avg_rain else 0)`.** Score
   is **0–6+**; the tier takes priority over the score for the
   recommendation text.
6. **Don't geocode.** The town string is the unit. Geocoding the user
   address and then matching to clusters by lat/lon is more accurate
   but adds 1 API call and is out of scope for a quick check.

## Pitfalls

1. **NEA dengue clusters come and go quickly.** A cluster added today
   might be removed tomorrow if no new cases. Always re-pull on
   each call — never cache for more than 1 hour.
2. **Town boundary ≠ geocoded location.** A "Bedok" address can be
   near the Paya Lebar cluster (in Toa Payoh). The skill reports
   clusters by town, not by lat/lon distance.
3. **The 7-day forecast is an extrapolation.** We have no real 7-day
   forecast API. The skill extrapolates current rainfall reading × 7.
   In dry weeks this is correctly low; in wet weeks it can overshoot
   by 30–40%.
4. **Std deviation can be 0** in unusually stable weather (e.g. 2020
   circuit breaker period). The "above-average" check then uses 0 σ,
   so forecast = avg is treated as "above average". This is fine —
   we want to be slightly conservative.
5. **High UV/PSI doesn't increase dengue risk** — they're mosquito-
   agnostic. The recommendation text mentions PSI as a side note, not
   a risk amplifier.
6. **Allergic reactions to DEET are rare but real.** The skill
   recommends DEET at moderate+ tier but doesn't push it at low tier.
7. **The skill does NOT predict** — it reports **current + forecasted**
   risk. For "should I cancel my Saturday morning jog?" the answer
   is "based on current data, here's the risk score".

## Caching

| Endpoint | TTL |
|----------|-----|
| `fetch_dengue_clusters` | 1 hour (clusters update fast) |
| `fetch_nea_historical_rainfall` | 24 hours (monthly data) |
| `fetch_rainfall` | 30 minutes (current reading) |
| `fetch_psi` | 1 hour (PSI is hourly) |

The shared client (`singapore_api.py`) handles disk caching under
`~/.hermes/cache/<namespace>/<sha1>.json`. The skill does not add
its own cache layer.

## Tests

```bash
python3 -m unittest discover -s tests
```

The test file mocks all four fetchers and covers the full tier matrix
(4 tiers × 2 PSI tiers = 8 cells), the score formula, and the
"insufficient history" fallback.
