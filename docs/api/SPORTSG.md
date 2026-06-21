# SPORT (Sport Singapore)

Sport participation statistics, ActiveSG facilities, school sport facilities, and physical-activity survey data.

## Discovery

- **Catalog search:** <https://data.gov.sg/datasets?query=&coverage=&agencies=SPORT>
- **Collections endpoint:** `https://api-production.data.gov.sg/v2/public/api/collections?page=N` (filter client-side by `managedByAgencyName == "Sport Singapore"`)
- **Counts:** **7 collections, 22 datasets** (see full catalog below)

## Dataset Download Flow

> **Auth required.** The `api-open.data.gov.sg` endpoints require a `DATA_GOV_SG_API_KEY`. Register at <https://data.gov.sg/> to get one. Pass it in the `x-api-key` header.

```bash
DATASET_ID="<dataset_id>"
API_KEY="<your_DATA_GOV_SG_API_KEY>"

# 1. Initiate
curl --location --request POST \
  "https://api-open.data.gov.sg/v1/public/api/datasets/${DATASET_ID}/initiate-download" \
  --header 'Content-Type: application/json' \
  --header "x-api-key: ${API_KEY}" \
  --data '{}'

# 2. Poll for the signed URL
curl --location \
  "https://api-open.data.gov.sg/v1/public/api/datasets/${DATASET_ID}/poll-download" \
  --header "x-api-key: ${API_KEY}"

# 3. Download from the signed S3 URL
curl --location '<signed_url_from_poll_response>'
```

## Common Dataset IDs

| ID | Description | Format |
|---|---|---|
| `d_9b87bab59d036a60fad2a91530e10773` | SportSG Sport Facilities | GeoJSON |
| `d_d1546dda1793d7085d330242b026034f` | SportSG Sport Facilities (companion dataset) | ad-hoc |
| `d_828e36827f339f36811377857bc99f48` | SportSG DUS Sport Facilities | annual |
| `d_19f760bbdbe714e265f38c551742214b` | DUS Schools Sports Facilities | annual |
| `d_2f7c888a00a917c149d6df171556b9f8` | DUS Schools Sports Facilities (companion) | annual |

## Collection Catalog

All 7 SPORT collections, ordered by `collectionId`. Each row maps to one or more child dataset IDs (use the initiate → poll → download flow above to fetch the actual file).

| ID | Name | Frequency | Datasets | Dataset IDs |
|---|---|---|---|---|
| 1627 | Barriers to Participate in Sport / Physical Activity (2022) | annual | 1 | `d_dfe8ada0639b2a892c48e82cf5cb39ae` |
| 1628 | Motivations to Participate in Sport / Physical Activity (2022) | annual | 1 | `d_eb25dc376346bc79afabe9803cfd9891` |
| 1629 | SportSG DUS Sport Facilities | annual | 1 | `d_828e36827f339f36811377857bc99f48` |
| 1630 | DUS Schools Sports Facilities | annual | 2 | `d_19f760bbdbe714e265f38c551742214b`<br>`d_2f7c888a00a917c149d6df171556b9f8` |
| 1631 | SportSG Sport Facilities | ad-hoc | 2 | `d_9b87bab59d036a60fad2a91530e10773`<br>`d_d1546dda1793d7085d330242b026034f` |
| 1632 | Sport Participation Level | annual | 4 | `d_8aa2540e2abb980dabd1207fc6efc046`<br>`d_82b974dc663f13493a8e0e0f51361a67`<br>`d_3997ebe3f0f535e51833f51fe8b9c449`<br>`d_deb78af871053c93b8b147d2e91e27e5` |
| 1633 | Top Sport & Physical Activity by SG Residents - Overall | annual | 11 | `d_b8eca5ac5d02cc48edd5ebb7a3b01b1b`<br>`d_83687c0e602bec2e26e4f2b0faedf526`<br>`d_961bfc0ba42c70a4c2e4586b8b3c4ec0`<br>`d_279af3f41c0b240d3a6f05a0417fd58e`<br>`d_36ff9bbf1221c3d36ba23ca790ae65a5`<br>`d_8963788eef3a91d6dc473396ea7ea929`<br>`d_b33b86dd8e73a5d3951e671803577b71`<br>`d_bb835593706c8bef193e8e964facd6d8`<br>`d_ac3377ce513d130581865f30939e8996`<br>`d_5e78a7c574073ef1aa8cfd5701a556fd`<br>`d_202f96987050d470fbc1dfc51baad647` |
