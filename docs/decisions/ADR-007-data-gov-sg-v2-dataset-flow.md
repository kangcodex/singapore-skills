# ADR-007: data.gov.sg v2 dataset flow (`initiate → poll → signed S3 CSV`)

## Status
Accepted

## Date
2026-06-22 (originally documented in S00, confirmed in S08)

## Context

Singapore's data.gov.sg exposes two data APIs:

- **Legacy CKAN** (`https://data.gov.sg/api/action/datastore_search?resource_id=...`)
  — returns a paginated JSON envelope with up to ~100 records per call.
  - Path: `https://data.gov.sg/dataset/<slug>/resource/<id>` (browser view)
  - Limit: paginated; ~100 records per page
  - Auth: none required for most datasets
  - **SINGSTAT still uses this path** (see ADR-004)

- **v2 Dataset API** (`https://api-production.data.gov.sg/v2/public/api/...`)
  — three-step flow:
  1. `POST /datasets/<id>/initiate-download` → returns a `submission_id`
  2. `GET /datasets/<id>/poll-download/<submission_id>` → polls until
     the dataset is packaged, returns a `url` to a signed S3 bucket
  3. `GET <signed_s3_url>` → returns the full CSV / GeoJSON

  - Path: `https://data.gov.sg/dataset/<slug>` (v2 metadata)
  - Limit: full dataset (no pagination for the typical CSV)
  - Auth: optional `x-api-key: $DATA_GOV_SG_API_KEY` header (raises
    rate limit from anonymous to ~10 req/s)
  - **URA, CEA, HDB, NEA realtime, OneMap all use this path** (mostly)

The legacy CKAN flow is fine for small datasets but **breaks for
URA Master Plan** (10k+ features), **SINGSTAT** (wide-format quirk),
and any large CSV. v2 returns the whole file in one signed-URL
download.

The v2 collection metadata API
(`GET /v2/public/api/collections?page=N`) returns 10 collections per
page, totaling 1,370 across 62 agencies (as of 2026-06). This is the
source of truth for what's available.

## Decision

All new fetchers in `singapore_api.py` go through the **v2 dataset
flow** via `fetch_dataset_rows(dataset_id)` and
`fetch_dataset_geojson(dataset_id)`. The pattern is:

```python
def fetch_dataset_rows(dataset_id, filters=None):
    """Initiate → poll → signed S3 CSV → parse → return rows.

    Sends `x-api-key` header if DATA_GOV_SG_API_KEY is set in the
    env. Falls back to anonymous on 4xx (per data.gov.sg's own
    recommendation: "anonymous works, just slower").
    """
    body = initiate_download(dataset_id)
    sub_id = body["data"]["submissionId"]
    s3_url = poll_until_ready(dataset_id, sub_id)
    csv_text = request_text(s3_url)  # the signed S3 URL
    return list(csv.DictReader(io.StringIO(csv_text)))
```

`request_json()` handles gzip, cache, retry, and timeout. The
`_V1_TO_V2` routing map and `_flatten_v1_*` envelope normalisers
keep backwards-compat for the few datasets that still ship on v1.

For SINGSTAT specifically, `_fetch_singstat_ckan()` exists as a
narrow exception that uses the legacy CKAN endpoint + the
wide-to-long pivot (ADR-004).

## Alternatives Considered

### Stay on legacy CKAN for everything
- Pros: One path, well-understood.
- Cons: Pagination; doesn't scale to large datasets; URA's
  Master Plan alone is 10k+ features, fetching all of it via
  paginated CKAN would be 100+ requests.
- Rejected.

### Use the v2 collection metadata API exclusively
- Pros: One path, modern.
- Cons: SINGSTAT has not migrated; some legacy HDB datasets still
  serve v1 only. A blanket v2-only would break these.
- Rejected: need the narrow CKAN exception for SINGSTAT.

### Third-party SDKs (e.g. `datagovsg`)
- Pros: Less boilerplate.
- Cons: Adds a dependency, the SDKs lag behind data.gov.sg's own
  API changes, and the 3-step flow is simple enough to implement
  in 30 lines.
- Rejected.

## Consequences

- **Pos:** One pattern for 95% of the data fetches. SINGSTAT's
  legacy CKAN is a clearly-marked exception.
- **Pos:** The v2 signed S3 URL is cacheable, so second-call latency
  drops to <50ms (disk read of `~/.hermes/cache/...`).
- **Pos:** The `x-api-key` env var is read at call time — no
  restart needed when the user gets a new key. Falls back to
  anonymous if the env var is unset.
- **Pos:** `request_json()` handles gzip transparently (URA
  responses are gzipped by default).
- **Neg:** The 3-step flow means a single call can take 1-3 seconds
  for the packaging step. The poll loop has a max 30s wait; on
  timeout, raises a `TimeoutError`. The user is expected to retry.
- **Neg:** If `DATA_GOV_SG_API_KEY` is set but invalid, the
  `initiate-download` call returns 401; the function raises a
  `PermissionError` with the API's error message. The
  `TestRequestJsonAuth` test pins this contract.
- **Neg:** `fetch_dataset_rows()` and `fetch_dataset_geojson()` are
  the only public surface; the inner 3-step helpers
  (`initiate_download`, `poll_until_ready`, `request_text`) are
  private. A future skill that needs a different shape (e.g.
  streaming JSON for a 100MB file) would need a new public
  function.

## Conventions

- All dataset IDs are public `d_<32 hex>` strings. They live as
  module-level constants at the top of `singapore_api.py`:
  `HDB_RESALE_DATASET_ID`, `URA_RENTALS_DATASET_ID`, etc.
- All v2 collection IDs (the `collectionId` field) are documented
  in the per-skill reference docs (`docs/api/URA.md`,
  `docs/api/CEA.md`, etc.).
- The SINGSTAT CKAN exception is documented in
  `references/singstat.md` (per-skill) and the test
  `TestS08PropertyFetchers` pins the contract for the two affected
  fetchers.

## Follow-on

- A future v3 (if data.gov.sg ships one) would be a drop-in
  replacement of the 3 inner helpers; the public `fetch_dataset_rows`
  and `fetch_dataset_geojson` signatures would not change.
