# NEA PSI & UV (real-time air-quality + sun-strength)

`weekend-planner-skill` uses the **v1** NEA endpoints (public, no API key).
v2 endpoints return `Missing Authentication Token` without `DATA_GOV_SG_API_KEY`.

## PSI — `fetch_psi()`

```
GET https://api.data.gov.sg/v1/environment/psi
```

Returns the 5 NEA regions + a national reading, updated hourly.

### Tiers the skill enforces

| psi_24h | tier |
|---------|------|
| 0–50 | good |
| 51–100 | moderate |
| 101–200 | unhealthy |
| 201+ | hazardous |

`None` or missing national reading → `unknown` (no pivot, no panic).

### Truncated real response (`2026-06-21 09:00 SGT`)

```json
{
  "region_metadata": [
    {"name": "west",        "label_location": {"latitude": 1.3573, "longitude": 103.74}},
    {"name": "national",    "label_location": {"latitude": 1.35,   "longitude": 103.82}},
    ...
  ],
  "items": [
    {
      "timestamp": "2026-06-21T08:00:00+08:00",
      "readings": {
        "psi_twenty_four_hourly": {
          "national": 31, "west": 32, "east": 28, "central": 30, "south": 29, "north": 30
        }
      }
    }
  ]
}
```

## UV — `fetch_uv()`

```
GET https://api.data.gov.sg/v1/environment/uv
```

Returns a single 0–11+ integer (whole-number hours, not index). No region breakdown.

### Tiers the skill enforces

| uv | tier |
|----|------|
| 0–2 | low |
| 3–5 | moderate |
| 6–7 | high |
| 8–10 | very-high |
| 11+ | extreme |

### Truncated real response (`2026-06-21 12:00 SGT`)

```json
{
  "items": [
    {
      "timestamp": "2026-06-21T11:00:00+08:00",
      "index": [{"value": 8, "timestamp": "2026-06-21T11:00:00+08:00"}]
    }
  ]
}
```

## Pitfalls

1. **NEA "PSI" name confusion.** v1 returns `psi_twenty_four_hourly` (the
   24h rolling average). PM2.5/PM10 are separate sub-indices; the skill
   uses the 24h PSI only, which is the regulatory headline number.
2. **UV is per-hour, not per-day.** v1 returns a single integer for the
   current hour. There is no "max UV today" forecast in v1. If the user
   asks about "this afternoon" the skill asks the user to re-run later
   (or returns `unknown`).
3. **National reading is sometimes `null`.** During sensor maintenance,
   v1 returns `"national": null` for an hour or two. The skill treats
   `None` as `unknown` and proceeds without pivoting.
4. **Region names are lowercase.** v1's `psi_twenty_fourly` keys are
   `west`, `east`, `central`, `south`, `north`, `national` — all
   lowercase. Capitalising the keys returns `None`.
5. **v2 requires `DATA_GOV_SG_API_KEY`.** If the env var is unset the
   v2 call returns `Missing Authentication Token`. The shared client
   (`try_v2_then_v1`) transparently falls back to v1, which is public.

## What the skill uses vs drops

- Uses: `items[0].readings.psi_twenty_fourly.national` (PSI),
  `items[0].index[0].value` (UV).
- Drops: `region_metadata[*].label_location` (the skill uses
  OneMap geocoding instead), all PM2.5/PM10 sub-indices, all
  historical `items[1..]`.
