# NEA Weather Context (HDB mode only)

HDB mode adds an NEA rainfall classification on top of the v1 cluster
baseline. The other four modes (private / rental / ec / investment) do
not use NEA — they are returns-driven, not amenity-driven.

For the full NEA catalog (109 collections), see the canonical
[`docs/api/NEA.md`](../../../docs/api/NEA.md).

## What HDB mode uses

HDB mode fetches the last 5 years of monthly rainfall from NEA's
historical-rainfall dataset and compares the most recent 24 months to
the 5-year mean. The result classifies the local climate as:

- `above-average` — recent 24mo mean > 5yr mean + 1σ
- `typical` — within ±1σ of the 5yr mean
- `below-average` — recent 24mo mean < 5yr mean − 1σ
- `unknown` — no records (network failure, dataset empty)

The classification feeds into the `verdict()` matrix in `property_advisor.py`.
A premium of > 5% with an `above-average` rainfall classification and
limited URA uplift flips the verdict to `above market` (the assumption
being that the premium is hard to justify for a property with poor
drainage outlook).

## Fetchers used

- `fetch_nea_historical_rainfall(months=60)` — returns the last 60
  months of station-level rainfall records
- The skill picks the first station in the result. Stations are sparse
  (~10 nationwide), so the result is station-level, not neighbourhood-level.
  See [Pitfalls](#pitfalls) below.

## Data shape

Typical columns in the rainfall dataset:

- `station_id` — string
- `total_rainfall_mm` (or `rainfall_mm` / `value`) — string number, coerce
  with `to_float` at the boundary
- `month` — `YYYY-MM` (the v1 fallback chain reads `total_rainfall_mm`
  → `rainfall_mm` → `value`, in that order)

## Pitfalls

- **1σ is a heuristic, not a flood-risk classification.** A `typical`
  verdict does not mean the town is flood-free. URA's flood-risk
  planning layer is a separate (much larger) dataset — not loaded by
  this skill.
- **NEA rainfall is station-level.** Stations are sparse; the script
  uses the first station returned. A future enhancement would let the
  user pick a station explicitly. Until then, the result is the
  national first-station average, not the user's exact neighbourhood.
- **The 5-year window is hard-coded.** 60 months is the
  `RAINFALL_LOOKBACK_5YR` constant. Reducing it skews the mean;
  increasing it is fine but slower.
- **No HDB-mode rainfall → verdict falls back.** When the NEA fetch
  returns `[]`, the classification is `unknown` and the verdict
  function treats it the same as `typical` (no penalty applied).

## Cross-references

- Canonical NEA catalog: [`docs/api/NEA.md`](../../../docs/api/NEA.md)
- Shared client: [`singapore_api.py`](../../../singapore_api.py) (look for
  `fetch_nea_historical_rainfall`)
- Fetcher is smoke-tested in
  [`tests/test_singapore_api.py`](../../../tests/test_singapore_api.py) —
  class `TestDatastoreHelpers`
- HDB mode's rainfall classification is tested in
  [`tests/test_property_advisor.py`](../tests/test_property_advisor.py) —
  class `TestRainfallClassification`
