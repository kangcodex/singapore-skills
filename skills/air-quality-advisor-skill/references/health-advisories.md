# NEA Health Advisory Bands

The 5-band table the `air-quality-advisor-skill` uses to classify PSI, PM2.5, and UV. Sources: NEA PSI bands (local 24-hour scale), US EPA PM2.5 bands (NEA uses the same), WHO UV index bands.

## PSI 24-hour bands (NEA)

| PSI range | Band            | Advisory                                                        |
| --------- | --------------- | --------------------------------------------------------------- |
| 0-50      | good            | Good for outdoor activities                                     |
| 51-100    | moderate        | Moderate — limit prolonged outdoor exertion                     |
| 101-200   | unhealthy       | Unhealthy — sensitive groups should avoid outdoor activity      |
| 201-300   | very_unhealthy  | Very unhealthy — avoid outdoor activity                         |
| 301+      | hazardous       | Hazardous — avoid all outdoor activity, stay indoors            |

**Source:** NEA PSI banding. See https://www.haze.gov.sg/ for the official description.

## PM2.5 24-hour bands (US EPA / NEA)

| PM2.5 (μg/m³) | Band            | Advisory                                                        |
| ------------- | --------------- | --------------------------------------------------------------- |
| 0-12          | good            | Good for outdoor activities                                     |
| 13-55         | moderate        | Moderate — limit prolonged outdoor exertion                     |
| 56-150        | unhealthy       | Unhealthy — sensitive groups should avoid outdoor activity      |
| 151-250       | very_unhealthy  | Very unhealthy — avoid outdoor activity                         |
| 251+          | hazardous       | Hazardous — avoid all outdoor activity, stay indoors            |

**Source:** US EPA PM2.5 AQI bands. NEA uses the same breakpoints for its PSI sub-index.

## UV index bands (WHO)

| UV index | Band       | Advisory                                            |
| -------- | ---------- | --------------------------------------------------- |
| 0-2      | low        | Low UV — no protection needed                       |
| 3-5      | moderate   | Moderate UV — wear sunscreen                        |
| 6-7      | high       | High UV — protection essential                      |
| 8-10     | very_high  | Very high UV — extra protection                     |
| 11+      | extreme    | Extreme UV — avoid sun exposure, protect skin       |

**Source:** WHO Global Solar UV Index. See https://www.who.int/news-room/questions-and-answers/item/radiation-the-known-health-effects-of-ultraviolet-radiation for the official description.

## Worst-band logic

The `health_advisory` in the output is the advisory of the worst band across all three pollutants. The rank (lowest = safest):

```
rank = {
    "good": 1, "low": 1,
    "moderate": 2,
    "high": 3, "unhealthy": 3,
    "very_high": 4, "very_unhealthy": 4,
    "extreme": 5, "hazardous": 5,
}
```

The `max()` of `(band, rank.get(band, 0))` (key=rank) across `psi_band`, `pm25_band`, `uv_band` determines the worst band. The advisory text comes from the band-to-text map in the script.

## Examples

| PSI | PM2.5 | UV  | Worst band       | health_advisory                                |
| --- | ----- | --- | ---------------- | ----------------------------------------------- |
| 42  | 12    | 5   | moderate         | "Moderate — limit prolonged outdoor exertion"   |
| 42  | 12    | 12  | extreme          | "Extreme UV — avoid sun exposure, protect skin" |
| 180 | 200   | 8   | very_unhealthy   | "Very unhealthy — avoid outdoor activity"        |
| 320 | 200   | 12  | hazardous        | "Hazardous — avoid all outdoor activity, stay indoors" |
| null | 12   | 5   | moderate (UV)    | "Moderate UV — wear sunscreen"                  |

When a value is unavailable, the band is `"unknown"` and the advisory is `"Reading unavailable"`. `unknown` is excluded from the worst-band logic.

## Why the rank ties

- `good` and `low` both rank 1. They're functionally equivalent (both = "fine outside"). The advisory text maps both to "Good for outdoor activities".
- `unhealthy` and `high` both rank 3. PSI's "unhealthy" and UV's "high" are similar in severity (caution for sensitive groups).
- `very_unhealthy` and `very_high` both rank 4.
- `hazardous` and `extreme` both rank 5.

This is intentional: cross-pollutant rank equivalence makes the worst-band math work without inventing a unified severity scale.

## See also

- `references/nea-realtime.md` — the NEA endpoint shapes
- Canonical `docs/api/NEA.md` — the full NEA catalog
