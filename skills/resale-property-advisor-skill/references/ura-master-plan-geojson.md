# URA Master Plan (data.gov.sg v2 dataset flow)

The Urban Redevelopment Authority publishes the Master Plan as a GeoJSON
FeatureCollection (one Feature per land-use polygon). Each feature's
`properties` carries `lu_desc` and `mpro_use`, with the geometry in SVY21
(easting/northing) when the v2 dataset preserves it.

The skill uses the dataset for "future amenities within 1 km of the cluster
centroid" — schools, healthcare, MRT, business hubs, industrial. It scans all
features and categorises by `lu_desc` regex match.

## Endpoints

```
POST https://api-open.data.gov.sg/v1/public/api/datasets/{DATASET_ID}/initiate-download
GET  https://api-open.data.gov.sg/v1/public/api/datasets/{DATASET_ID}/poll-download
GET  <signed S3 URL from poll response>            # the GeoJSON body
```

`DATASET_ID` is `d_90d86daa5bfaa371668b84fa5f01424f` (canonical: see
`URA_MASTER_PLAN_DATASET_ID` in `singapore_api.py`). Headers: `User-Agent:
singapore-skills/0.1` is mandatory; `x-api-key: <DATA_GOV_SG_API_KEY>` is
included when the env var is set.

The dataset page on data.gov.sg: https://data.gov.sg/datasets/d_90d86daa5bfaa371668b84fa5f01424f/view

## Real (truncated) response

`fetch_dataset_geojson()` returns a `FeatureCollection` dict:

```python
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {"type": "Polygon", "coordinates": [[[30012.3, 38987.5], ...]]},
      "properties": {
        "lu_desc": "PRIMARY SCHOOL",
        "mpro_use": "EDUCATION",
        "planning_area": "BISHAN"
      }
    },
    {
      "type": "Feature",
      "geometry": {"type": "Polygon", "coordinates": [[[30144.6, 39120.8], ...]]},
      "properties": {
        "lu_desc": "HOSPITAL",
        "mpro_use": "HEALTHCARE",
        "planning_area": "BISHAN"
      }
    }
  ]
}
```

Date stamp: 2026-06-20 (URA Master Plan 2019 edition, refreshed quarterly).

## What the skill reads vs drops

The skill reads (from each feature's `properties`):
- `lu_desc` (e.g. "PRIMARY SCHOOL", "HOSPITAL", "MRT STATION")
- `mpro_use` (fallback for categorisation when `lu_desc` is empty)
- `geometry` (SVY21 polygon, used for the 1 km radius scan)

The skill drops:
- `planning_area` (used for sanity check; URA scan is geography-based, not planning-area-based)

## Categorisation (regex on `lu_desc`)

| Category | Regex (case-insensitive) | Example `lu_desc` |
|---|---|---|
| `primary_school` | `\b(school\|primary\|secondary\|junior college)\b` | "PRIMARY SCHOOL", "SECONDARY SCHOOL" |
| `healthcare` | `\b(hospital\|clinic\|polyclinic\|healthcare\|nursing home)\b` | "HOSPITAL", "POLYCLINIC" |
| `MRT` | `\b(mrt\|station\|metro\|rapid transit)\b` | "MRT STATION" |
| `business_hub` | `\b(business\|office\|commercial hub\|cbd)\b` | "BUSINESS PARK" |
| `industrial` | `\b(industrial\|factory\|warehouse)\b` | "INDUSTRIAL" |

If `lu_desc` matches multiple categories (e.g. "MRT STATION AT HOSPITAL"),
the first regex match wins. Most records match exactly one.

If `lu_desc` is empty, the skill tries `mpro_use` instead (e.g. "HEALTHCARE" → `healthcare`).

## Pitfalls

1. **Geometry is SVY21 (easting/northing in metres), not WGS84.** Convert with `svy21_to_wgs84()` before computing haversine distances. The v2 dataset ships SVY21 coordinates.
2. **The Master Plan is forward-looking, not ground truth.** A school marked "proposed" in the 2019 Master Plan may be a car park in 2026. Use the data as a "future amenity" signal, not a current amenity.
3. **`lu_desc` is verbose English, not a controlled vocabulary.** "Primary School" and "Primary" and "SCHOOL (PRIMARY)" all appear. The regex is permissive (`\b(school\|primary)\b`) to catch them.
4. **One fetch, no pagination.** The v2 flow delivers the full FeatureCollection in a single signed-S3 download (~5 MB). Cached after first fetch; refreshed on upstream `Last-Modified` change.
5. **URA scan is 1 km radius from the cluster centroid.** Town centres are 600–800 m wide; a 1 km scan catches nearby amenity but not adjacent-town amenities. Tunable via `AMENITY_RADIUS_M` constant.
6. **`mpro_use` is a coarser categorisation than `lu_desc`.** When `lu_desc` is missing or empty, `mpro_use` is the fallback. Its vocabulary is limited to ~50 values (RESIDENTIAL, COMMERCIAL, INDUSTRIAL, etc.).
7. **Empty result is not an error.** If no URA features match the 1 km scan, `future_amenities: []` is the documented response. The verdict then becomes `above market` (no uplift).

## Related endpoints

- URA Master Plan ArcGIS REST service (not used by the skill — too verbose)
- OneMap REST Planning Area API (geocoding only, not land-use)

## Cache

Cache namespace: `dataset-geojson:d_90d86daa5bfaa371668b84fa5f01424f`. Cache
writes to
`~/.hermes/cache/dataset-geojson:d_90d86daa5bfaa371668b84fa5f01424f/<sha1>.json`.
Refreshed when the upstream `Last-Modified` changes (typically every 1–2 years
for URA).
