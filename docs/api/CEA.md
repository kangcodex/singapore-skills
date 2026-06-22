# CEA (Council for Estate Agencies)

Regulatory data on Singapore's real estate salespersons — active registrations and residential property transactions closed by registered salespersons (HDB resale, HDB rentals, private rentals, private sales).

## Discovery

- **Catalog search:** <https://data.gov.sg/datasets?query=&coverage=&agencies=CEA>
- **Collections endpoint:** `https://api-production.data.gov.sg/v2/public/api/collections?page=N` (filter client-side by `managedByAgencyName == "Council For Estate Agencies"`)
- **Counts:** **2 collections, 2 datasets** (see full catalog below)

## Realtime APIs (v1, no auth)

No v1 realtime APIs are exposed by CEA. All CEA data is served as static/scheduled datasets via the v2 collection flow.

## Dataset Download Flow

> **Auth required.** The `api-open.data.gov.sg` endpoints require a `DATA_GOV_SG_API_KEY`. Register at <https://data.gov.sg/> to get one. Pass it in the `x-api-key` header.

All CEA dataset downloads follow this 3-step pattern. The download URLs are signed S3 URLs and expire after a short period — always re-initiate before downloading.

```bash
DATASET_ID="d_ee7e46d3c57f7865790704632b0aef71"
API_KEY="<your_DATA_GOV_SG_API_KEY>"

# 1. Initiate
curl --location --request POST \
  "https://api-open.data.gov.sg/v1/public/api/datasets/${DATASET_ID}/initiate-download" \
  --header 'Content-Type: application/json' \
  --header "x-api-key: ${API_KEY}" \
  --data '{}'

# 2. Poll for the signed URL (repeat until status is "Up")
curl --location \
  "https://api-open.data.gov.sg/v1/public/api/datasets/${DATASET_ID}/poll-download" \
  --header "x-api-key: ${API_KEY}"

# 3. Download the actual file from the signed S3 URL
curl --location '<signed_url_from_poll_response>'
```

## Legacy CKAN Search

The CKAN `datastore_search` endpoint on `https://data.gov.sg/api/action/`
returns 404 for these datasets as of 2026. Use the v2 flow above (initiate →
poll → fetch signed S3 URL) instead. The URL below is kept for historical
reference only:

```bash
curl --location \
  'https://data.gov.sg/api/action/datastore_search?resource_id=d_ee7e46d3c57f7865790704632b0aef71&limit=10'
# → 404 Not Found (data.gov.sg no longer serves CKAN)
```

## Collection Catalog

All 2 CEA collections, ordered by `collectionId`. Each row maps to one or more child dataset IDs (use the initiate → poll → download flow above to fetch the actual file).

| ID | Name | Frequency | Datasets | Dataset IDs |
|---|---|---|---|---|
| 54 | CEA Salesperson Information | other | 1 | `d_07c63be0f37e6e59c07a4ddc2fd87fcb` |
| 55 | CEA Salespersons' Property Transaction Records (residential) | monthly | 1 | `d_ee7e46d3c57f7865790704632b0aef71` |
