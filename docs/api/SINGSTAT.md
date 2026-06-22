# SINGSTAT (Singapore Department of Statistics)

Official Singapore government statistics on the residential property market — quarterly supply pipeline, vacancy and availability series. SINGSTAT datasets are not exposed via the v2 collections catalog used by other agencies; they remain accessible through the legacy CKAN `datastore_search` endpoint.

## Discovery

- **Catalog search:** <https://data.gov.sg/datasets?query=&coverage=&agencies=SINGSTAT>
- **Collections endpoint:** `https://api-production.data.gov.sg/v2/public/api/collections?page=N` — **SINGSTAT does not appear in the v2 catalog.** Filter by `managedByAgencyName == "Singapore Department of Statistics"` returns zero results.
- **Counts:** 2 datasets commonly used for residential property analysis (no first-class SINGSTAT collection wrapper in v2)

## Realtime APIs (v1, no auth)

No v1 realtime APIs are exposed by SINGSTAT. All SINGSTAT data is served as scheduled datasets.

## Dataset Download Flow (CKAN)

> **No auth required.** SINGSTAT datasets are served by the legacy CKAN `datastore_search` endpoint and return JSON rows directly. This is the only working access path for SINGSTAT as of 2026.

```bash
DATASET_ID="d_01e3556fb916ca19a7e29fc39520fa78"

# 1. Fetch up to 100 rows (CKAN default)
curl --location \
  "https://data.gov.sg/api/action/datastore_search?resource_id=${DATASET_ID}&limit=100"
```

The response is a JSON envelope with `result.records[]` containing the rows. Columns follow a wide format: a `DataSeries` field (e.g. `"Vacant Private Residential Properties"`, `"Supply Of Private Residential Properties In The Pipeline By Development Status"`) followed by quarterly period columns named `YYYYQN` (e.g. `20261Q`).

For full historical download, paginate with the `offset` parameter (CKAN default page size is 100):

```bash
curl --location \
  "https://data.gov.sg/api/action/datastore_search?resource_id=${DATASET_ID}&limit=100&offset=100"
```

> **Why the v2 flow does not apply.** The `api-open.data.gov.sg` v2 initiate → poll → signed-S3 download pattern used by HDB/URA/CEA does not work for SINGSTAT. The datasets exist on the legacy CKAN endpoint only.

## Legacy CKAN Search (Primary Path for SINGSTAT)

Unlike other agencies, the CKAN `datastore_search` endpoint is the **primary working access path** for SINGSTAT as of 2026, not just a legacy fallback.

```bash
curl --location \
  'https://data.gov.sg/api/action/datastore_search?resource_id=d_01e3556fb916ca19a7e29fc39520fa78&limit=10'

# Response shape (truncated):
# {
#   "help": "https://data.gov.sg/api/3/action/help_show?name=datastore_search",
#   "success": true,
#   "result": {
#     "resource_id": "d_01e3556fb916ca19a7e29fc39520fa78",
#     "fields": [
#       {"id": "_id", "type": "int"},
#       {"id": "DataSeries", "type": "text"},
#       {"id": "20261Q", "type": "numeric"},
#       ...
#     ],
#     "records": [
#       {"_id": 1, "DataSeries": "Vacant Private Residential Properties", "20261Q": 20230, "20254Q": 21820, ...}
#     ]
#   }
# }
```

## Dataset Catalog

SINGSTAT does not expose v2 collections. Datasets are documented directly by resource ID. Each row's data is accessed via the CKAN flow above.

| Dataset ID | Name | Records | Format |
|---|---|---|---|
| `d_01e3556fb916ca19a7e29fc39520fa78` | Available And Vacant Private Residential Properties | 6 series | `DataSeries` + quarterly columns |
| `d_055b6549444dedb341c50805d9682a41` | Supply Of Private Residential Properties In The Pipeline | 10 series | `DataSeries` + quarterly columns |
