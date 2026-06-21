# NEA (National Environment Agency)

Weather, air quality, dengue, hawker centres, waste management, post-death facilities — the most diverse real-time API surface among the four agencies.

## Discovery

- **Catalog search:** <https://data.gov.sg/datasets?query=&coverage=&agencies=NEA>
- **Collections endpoint:** `https://api-production.data.gov.sg/v2/public/api/collections?page=N` (filter client-side by `managedByAgencyName == "National Environment Agency"`)
- **Counts:** **109 collections, 249 datasets** (see full catalog below)

## Realtime APIs (v1, no auth)

All NEA realtime endpoints live at `https://api.data.gov.sg/v1/environment/...`. None require an API key.

### Air Quality

#### Pollutant Standards Index (PSI)

24-hour PSI readings across Singapore regions.

```bash
curl --location 'https://api.data.gov.sg/v1/environment/psi'
```

#### PM2.5 (1-hour readings)

```bash
curl --location 'https://api.data.gov.sg/v1/environment/pm25'
```

#### UV Index

```bash
curl --location 'https://api.data.gov.sg/v1/environment/uv-index'
```

### Weather

#### 2-hour Weather Forecast

```bash
curl --location 'https://api.data.gov.sg/v1/environment/2-hour-weather-forecast'
```

#### 24-hour Weather Forecast

```bash
curl --location 'https://api.data.gov.sg/v1/environment/24-hour-weather-forecast'
```

#### 4-day Weather Forecast

```bash
curl --location 'https://api.data.gov.sg/v1/environment/4-day-weather-forecast'
```

#### Realtime Readings

```bash
# Rainfall
curl --location 'https://api.data.gov.sg/v1/environment/rainfall'

# Wind Speed
curl --location 'https://api.data.gov.sg/v1/environment/wind-speed'

# Air Temperature
curl --location 'https://api.data.gov.sg/v1/environment/air-temperature'

# Relative Humidity
curl --location 'https://api.data.gov.sg/v1/environment/relative-humidity'
```

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
| `d_b16d06b83473fdfcc92ed9d37b66ba58` | Rainfall - Monthly Total | CSV |
| `d_4a086da0a5553be1d89383cd90d07ecd` | Hawker Centres | GeoJSON |
| `d_bda4baa634dd1cc7a6c7cad5f19e2d68` | Dates of Hawker Centres Closure | CSV |
| `d_dbfabf16158d1b0e1c420627c0819168` | Dengue Clusters | GeoJSON |
| `d_8a7850dc3993dc45f1620b9972c58d4d` | Pollutant Standards Index (PSI) | realtime |
| `d_9b2d180c92c4a3c45b5c671937bd1b5d` | PM2.5 | realtime |
| `d_076774d6843cc3369731f5abaef83d30` | Ultra-violet Index (UVI) | realtime |
| `d_3f9e064e25005b0e42969944ccaf2e7a` | Weather Forecast | realtime |
| `d_66b77726bbae1b33f218db60ff5861f0` | Realtime Weather Readings across Singapore | realtime |
| `d_2c13093a9d36377478755716f861ef14` | Dengue (Cases) - South East | daily |
| `d_e34261c5ccace716132b55a5b02ebb1f` | Dengue (Cases) - South West | daily |
| `d_e95e09fb3e54a3249e4bdf32e463effa` | Dengue (Cases) - North East | daily |
| `d_5f90123ce50e3d323bfd0ff3c9a84601` | Dengue (Cases) - Central | daily |

## Legacy CKAN Search

The CKAN `datastore_search` endpoint on `https://data.gov.sg/api/action/`
returns 404 for these datasets as of 2026. Use the v2 flow above (initiate →
poll → fetch signed S3 URL) instead. The URL below is kept for historical
reference only:

```bash
curl --location \
  'https://data.gov.sg/api/action/datastore_search?resource_id=d_b16d06b83473fdfcc92ed9d37b66ba58&limit=10'
# → 404 Not Found (data.gov.sg no longer serves CKAN)
```

## Collection Catalog

All 109 NEA collections, ordered by `collectionId`. Each row maps to one or more child dataset IDs (use the initiate → poll → download flow above to fetch the actual file).

| ID | Name | Frequency | Datasets | Dataset IDs |
|---|---|---|---|---|
| 1363 | 2nd Hand Goods Collection Points | annual | 2 | `d_7e4af775c0e24083461e9117415c8b0d`<br>`d_455844a90d985206b684851d2a8648d6` |
| 1364 | Air Pollutant - Lead | annual | 1 | `d_f71b15a17a8ce278d3d3d55383f86687` |
| 1365 | Air Pollutant - Carbon Monoxide  (Maximum 8-Hour Mean) | annual | 1 | `d_fdf8b7d640136ddd3bf461abf33d9b40` |
| 1366 | Air Pollutant - Nitrogen Dioxide | annual | 1 | `d_88dcbdd26f7adbb5a469491378abfedc` |
| 1367 | Air Pollutant – Ozone (Maximum 8-hour Mean) | annual | 1 | `d_12e90ff1178704ebd56dc2fff04eef56` |
| 1368 | Air Pollutant - Particulate Matter PM10 (24-hr Mean -99th Percentile) | annual | 1 | `d_dc29ecdc06f1f2b42c3dd06dd1ab8e6b` |
| 1369 | Air Pollutant - Particulate Matter PM2.5 | annual | 1 | `d_397fe8de643aea9927bdee32e49307ff` |
| 1370 | Air Pollutant - Sulphur Dioxide (Maximum 24-hour Mean) | annual | 1 | `d_ec484d9610a22c57fa873b14f9baa57a` |
| 1371 | Surface Air Temperature - Monthly Absolute Extreme Maximum | monthly | 1 | `d_72a4d7402d4014f1999a009864f64a11` |
| 1372 | Climate Change and Energy - Carbon Dioxide Emissions (From Combustion of Fossil Fuels) | annual | 1 | `d_4ab7c63c152147042394397f2b61b96a` |
| 1373 | Climate Change and Energy - Carbon Intensity of Electricity Generation | annual | 1 | `d_bc140b67a8708ba19c39d69182893f31` |
| 1374 | Climate Change and Energy - Energy Consumption Per Dollar GDP (% Improvement From 2005 Levels) | annual | 1 | `d_0a6e94f474ada55c3e81d088463cf321` |
| 1375 | Climate Change and Energy - Green Vehicles | annual | 1 | `d_5e5c2fa3ec41618eb7c17fc14b2be70b` |
| 1376 | Dates of Hawker Centres Closure | ad-hoc | 1 | `d_bda4baa634dd1cc7a6c7cad5f19e2d68` |
| 1378 | Listing of General Waste Collectors | annual | 1 | `d_26afdd562f28b4acecb400c10b70f013` |
| 1379 | Historical 1-hr PM2.5 | other | 1 | `d_6c0d5fc34838b12472475fdb73c0af29` |
| 1380 | Historical 24-hr PSI | other | 1 | `d_b4cf557f8750260d229c49fd768e11ed` |
| 1381 | Historical Daily Weather | ad-hoc | 1 | `d_03bb2eb67ad645d0188342fa74ad7066` |
| 1382 | Licensed Food Establishments - Food Shops | annual | 1 | `d_0d25efc0c39f97d8e260086162867718` |
| 1383 | Licensed Food Establishments - Supermarkets | annual | 1 | `d_34ba4c6d34d95f6bc06244917f62a0d8` |
| 1384 | List of Cleaning Contractors and Location of Work | ad-hoc | 1 | `d_8383572bdfd37d3586933c3ff5ec1922` |
| 1385 | List of Government Markets Hawker Centres | annual | 1 | `d_68a42f09f350881996d83f9cd73ab02f` |
| 1386 | List of NEA Licensed Eating Establishments with Grades, Demerit Points and Suspension History | quarterly | 1 | `d_227473e811b09731e64725f140b77697` |
| 1387 | List of Radiation Licences | other | 1 | `d_876921464cb577cb979e5bd75cd7d1c4` |
| 1388 | List of Supermarket Licences | quarterly | 1 | `d_11edd0117280c5776651d7891114c88c` |
| 1389 | NEA Market and Food Centre | other | 2 | `d_b5f8a5a4584b6e537c0ab81a48ca3497`<br>`d_a57a245b3cf3ec76ad36d55393a16e97` |
| 1390 | Number of Hawker Stalls Under Government Market and Hawker Centres, Annual | annual | 1 | `d_894e84243d69d55c13b357dbad4e6350` |
| 1391 | Number of Licensed Hawkers Under Government Market and Hawker Centres, Annual | annual | 1 | `d_874cb8683b003051794caaa0c2423ed5` |
| 1392 | Number of Radiation Licenses Issued by Type, Annual | annual | 1 | `d_b5dfc383eb8e97e940ac555a226d7196` |
| 1393 | Pesticides/Repellent Registered with NEA | monthly | 1 | `d_9e879860c62144c6f44011ad4bb04b82` |
| 1394 | PM2.5 | realtime | 1 | `d_9b2d180c92c4a3c45b5c671937bd1b5d` |
| 1395 | Pollution Control - Number Of Hazardous Substances Licences and Permits Issued, Annual | annual | 1 | `d_345313948f038e5aabc66ba33f4ea178` |
| 1396 | Pollutant Standards Index (PSI) | realtime | 1 | `d_8a7850dc3993dc45f1620b9972c58d4d` |
| 1397 | Rainfall - Monthly Maximum Daily Total | monthly | 1 | `d_53ffdaa97e48ce934cf92799d381f3b1` |
| 1398 | Rainfall - Monthly Number of Rain Days | monthly | 1 | `d_134857f63c76d227b6fa045f31ce59c1` |
| 1399 | Rainfall - Monthly Total | monthly | 1 | `d_b16d06b83473fdfcc92ed9d37b66ba58` |
| 1400 | Registered Environmental Control Officer (ECO) | monthly | 1 | `d_2a0bee4473e1d1d8635b4e63e2279eb9` |
| 1401 | Registered Vector Control Operator (VCO) | monthly | 1 | `d_0921c2daa08b8bd846d2405c934da8c6` |
| 1402 | Relative Humidity - Annual Means | annual | 1 | `d_31dbf162e94f76065e1e4c60a80a4264` |
| 1403 | Relative Humidity - Monthly Absolute Extreme Minimum | monthly | 1 | `d_54445baa32ffe4d46f5bef168c4e0538` |
| 1404 | Relative Humidity - Monthly Mean | monthly | 1 | `d_e3b1111a26b2aefef4f386c068d4ca5d` |
| 1405 | Resource Conservation - Recycling Rate By Waste Type | annual | 1 | `d_9740df787da2b59a0b5bd76a6c33453d` |
| 1406 | Solid Waste Management - Energy Produced From Incineration, Annual | annual | 1 | `d_90bdd35c5c5b4a34b3508eb613424a9a` |
| 1407 | Solid Waste Management - Lifespan of Semakau Landfill, Annual | annual | 1 | `d_a2d2c21343d4bfff47d151e4ab74d138` |
| 1408 | Solid Waste Management - Population With Access to Waste Collection Services, Annual | annual | 1 | `d_5692f13ebc022be89c8cc817d30798f8` |
| 1409 | Solid Waste Management - Total Domestic Waste Disposed | annual | 1 | `d_aea2e18e0f8fdf9b4c51b0c441ffc625` |
| 1410 | Solid Waste Management - Total Domestic Waste Disposed Per Capita | annual | 1 | `d_836d960a43625b78cfde04d5225befce` |
| 1411 | Solid Waste Management - Total Non Domestic Waste Disposed of, Annual | annual | 1 | `d_11b93f866c718775be0d859bf2f3d34c` |
| 1412 | Solid Waste Management - Total Non-Domestic Waste Disposed of Per S$Billion GDP, Annual | annual | 1 | `d_b2cb55562b85d36462e9687a076f20e9` |
| 1413 | Solid Waste Management - Total Waste Generated | annual | 1 | `d_316f1b0ac752001277c24cd12c3df205` |
| 1414 | Solid Waste Management - Total Waste Incinerated, Annual | annual | 1 | `d_0fefa8455a070b420aed1cb671f379b8` |
| 1415 | Solid Waste Management - Total Waste Landfilled, Annual | annual | 1 | `d_f0ad4d1fb8c2a9089981fd2f3fe07111` |
| 1416 | Solid Waste Management - Total Waste Recycled | annual | 1 | `d_8d95dc5ffcc9a18e049fc86d4513563c` |
| 1417 | Sunshine Duration- Monthly Mean Daily Duration | monthly | 1 | `d_9a80d732aa5de0a68be0557fc9437ad0` |
| 1418 | Surface Air Temperature - Monthly Absolute Extreme Minimum | monthly | 1 | `d_3b4b0418948847eaca93546f7574e365` |
| 1419 | Surface Air Temperature - Monthly Mean | monthly | 1 | `d_755290a24afe70c8f9e8bcbf9f251573` |
| 1420 | Ultra-violet Index (UVI) | realtime | 1 | `d_076774d6843cc3369731f5abaef83d30` |
| 1421 | Vector Control Data - Dengue Outbreak Statistics | annual | 1 | `d_8763ae810003718ad638e719ec9118df` |
| 1422 | Waste Disposed Of And Recycled, Annual | annual | 1 | `d_96d95bfc9867daa138a451950dc7cc4e` |
| 1423 | Wet Bulb Temperature, Hourly | monthly | 1 | `d_f222c70a7c00c5a5a9d4ec432d67f6e8` |
| 1424 | Active Cemeteries | ad-hoc | 2 | `d_4a9b83ee745c10c3aa5829fb80e09d9c`<br>`d_3d173430fafd11a4816a3fed64ac755a` |
| 1425 | Aedes Mosquito Breeding Habitats - Central | daily | 2 | `d_68d66612ee0b79bb49bf63730134aa68`<br>`d_22894a6996cb7ae7b9c090fe8b22b522` |
| 1426 | Aedes Mosquito Breeding Habitats - North East | daily | 2 | `d_b60aeb8e1566464459f57aabd4bb51cd`<br>`d_3d931c21e0c4af5f977a85c16f00169f` |
| 1427 | Aedes Mosquito Breeding Habitats - North West | daily | 2 | `d_3db9f0c0bf6fd3fae19faf0e1832461e`<br>`d_55eb08f9b3290eb2603820445cfa31e0` |
| 1428 | Aedes Mosquito Breeding Habitats - South East | daily | 2 | `d_944dd361659cec20260ced43b7251417`<br>`d_7dc311f941cb3eed2b1b413a44905a5b` |
| 1429 | Aedes Mosquito Breeding Habitats - South West | daily | 2 | `d_f02aa5a38a87dbead9ae1bedec247030`<br>`d_225c539853b0d4d9b8b03ad0c3a13363` |
| 1430 | After Death Facilities | ad-hoc | 3 | `d_d441f537d46bc60b684b60110c73ce92`<br>`d_3e301125130f97b1a811c3fbdfca14e6`<br>`d_8057b4f4c7eca22c3c51c4ac05440f21` |
| 1431 | Areas with High Aedes Population | monthly | 2 | `d_5d060d8b7838a15e8906fb22c50dbf51`<br>`d_4f0dab25f43b35057d2cb444ab96f969` |
| 1432 | Cash For Trash | half_year | 2 | `d_51995b625307f3953f7ba344722acd79`<br>`d_c23ec3724271b9d05436d1f61fe53749` |
| 1434 | Cleaning Sectors | ad-hoc | 2 | `d_d0d92d11b9d8b8cca6f9627d0cd23268`<br>`d_557c7709c7546893c4a2fe7947e60834` |
| 1435 | Crematoria | ad-hoc | 2 | `d_7c7c57950ceda95e8efa6cec46029b5d`<br>`d_eb99b8eb780aca3242f9a6742e3c4632` |
| 1436 | Dedicated Columbaria | ad-hoc | 2 | `d_9b0752e9d3f1f9d957d5d8be2b58dfff`<br>`d_d2424d92100adb7ecb8e3164c9fe4edb` |
| 1437 | Dengue (Cases) - Central | daily | 2 | `d_5f90123ce50e3d323bfd0ff3c9a84601`<br>`d_028e12ad6f4a0574bd110f5c90bb53eb` |
| 1438 | Dengue (Cases) - North East | daily | 2 | `d_e95e09fb3e54a3249e4bdf32e463effa`<br>`d_1baf53ac8e8d766bd3ad8766222448b3` |
| 1439 | Dengue (Cases) - South East | daily | 2 | `d_2c13093a9d36377478755716f861ef14`<br>`d_e4d0220150f630f79ca3c1ec46f49fb4` |
| 1440 | Dengue (Cases) - South West | daily | 2 | `d_e34261c5ccace716132b55a5b02ebb1f`<br>`d_f2d4a22e47e4387f4571433c92ba4e8e` |
| 1441 | Dengue Clusters | daily | 2 | `d_dbfabf16158d1b0e1c420627c0819168`<br>`d_c00cbf056265738b684e63e890a113d2` |
| 1442 | Designated Smoking Areas | ad-hoc | 2 | `d_d0fa8f07ef80ab23feaa3b870323bf27`<br>`d_822c052c06f9631d83887f65da1290c4` |
| 1443 | E-waste Recycling | annual | 2 | `d_db40d004afeb5a7f0f555fdcc34934cc`<br>`d_243a551f32af0c176251b26952d66a0c` |
| 1444 | Funeral Parlours | ad-hoc | 2 | `d_054b67adc211306beaf5c005be8f5381`<br>`d_ead1c8eb7897f00efb7636d9e738ea62` |
| 1445 | Hawker Centres | annual | 2 | `d_4a086da0a5553be1d89383cd90d07ecd`<br>`d_ccca3606c337a5c386b9c88dc0dd08b6` |
| 1446 | Inland Ash Scattering Gardens | ad-hoc | 2 | `d_8dc64019ee16bda33f7758bc4e9d2223`<br>`d_2543b3ec142fb7a5c96d40f3de5a3f76` |
| 1447 | Licensed Food Establishments by Category, Annual | annual | 2 | `d_dbf37846568f6a5595b4f16f110b4619`<br>`d_6188a67536a7a12751ee690e96b506fa` |
| 1448 | Lighting Waste Collection Points | annual | 2 | `d_6226f69998ed0cb62151af37706508cd`<br>`d_34a762d1639e15a6a31cbebb63054bfb` |
| 1449 | NEA Offices | ad-hoc | 2 | `d_5ff6c8be30ee24f83975ffae670c6246`<br>`d_f423c3f072f1b20d0724e5dccf659559` |
| 1450 | Recycling Bins | annual | 3 | `d_887343ecf94757d33c8db2ea1a349e15`<br>`d_8bf367d977da5a9310dc19ba159bb363`<br>`d_4dde14826642f49eefff48b7832b90db` |
| 1452 | Surface Air Temperature - Mean Daily Maximum | monthly | 2 | `d_b0fb69de67054d6d741bea78274ecc2a`<br>`d_8e72ca09d5000b490126e3cd492f942b` |
| 1453 | Surface Air Temperature - Mean Daily Minimum | monthly | 2 | `d_c92edf841336f03ab51c6693ac8d33ad`<br>`d_be96fc5a86b96f228efd7addaf7e61a8` |
| 1454 | Waste Treatment | half_year | 2 | `d_b494a1190d9968608705f4fdd66a7fbf`<br>`d_7490acdafe26728158cfc25c6f806b5a` |
| 1455 | Zika Cluster | ad-hoc | 2 | `d_a3c783f11d79ff7feb8856f762ccf2c5`<br>`d_7cfe3e06507c81d8d8ab7a699c566a8b` |
| 1456 | Weather Forecast | realtime | 3 | `d_3f9e064e25005b0e42969944ccaf2e7a`<br>`d_ce2eb1e307bda31993c533285834ef2b`<br>`d_f131f6e343bf8168e4057a04c4326a0a` |
| 1457 | Dengue Cases | daily | 5 | `d_d9b090680ff7ca1c87e6dc9fe97f809a`<br>`d_c9fa3b7cd11bb07b881275fdffe6ade7`<br>`d_49b7a0c6c4d18b1cab823505f4e8a494`<br>`d_9f5b11a819dc09a380319c748b56e0ad`<br>`d_b13cf6c5d82bfd0d11104311f470febf` |
| 1458 | Dengue Mosquito Breeding Habitats | daily | 5 | `d_02f2c940b20d5626b529cba593aedea4`<br>`d_2852a3f7dcb2ee914771965c9af9760e`<br>`d_dda66ec4908b469f3e6ed24cb7127e69`<br>`d_3be69ba3eb41e03172b19902d724928b`<br>`d_61c2b8ecf5403b60d720b7788271ef20` |
| 1459 | Realtime Weather Readings across Singapore | realtime | 5 | `d_66b77726bbae1b33f218db60ff5861f0`<br>`d_6580738cdd7db79374ed3152159fbd69`<br>`d_2d3b0c4da128a9a59efca806441e1429`<br>`d_534cf203023b51f51f879145ccc56ff9`<br>`d_7677738484067741bf3b56ab5d69c7e9` |
| 2026 | E-waste Recycling_NEW | annual | 2 | `d_e8c94e00d7e1dca4ae3248d0a8e39959`<br>`d_b709b4cda8fad1c65c0fd4d42e06fa2b` |
| 2028 | Dengue (Cases) - North West | daily | 2 | `d_ce8cf1e3f4f5ff1a68393a7cb101eb9c`<br>`d_fa61f803082097cf7fd64de754ce1c47` |
| 2053 | No Smoking Zones | ad-hoc | 2 | `d_491641889c8add4c7835721bd72aa84a`<br>`d_41b611bb3333d6c708f3326c8c1e78b5` |
| 2066 | Channels for Donation, Resale and Repair | half_year | 2 | `d_7e1f0da76a744c85e3d3ecc76642dcb5`<br>`d_e3f4732c652e083852f5abf31a973f34` |
| 2179 | Historical 2-hour Weather Forecast | ? | 9 | `d_5dd6ab3b31e347194898104c5736c312`<br>`d_e3f482e88e6d8e1f11b242de27bbf9f6`<br>`d_1d9a9b53a8820ac0460f99d633ed674c`<br>`d_47e150685fc9f82c953a16844fd50323`<br>`d_83ab03de31ec08093a68a9a43d0e0e42`<br>`d_fcd42c883fb2e1019554cab0da275e25`<br>`d_59d5e3d1879b5f08d332ee31077f37e6`<br>`d_b0e005c4891382d829c81bbd8d0f4354`<br>`d_d3e4808d740fc2b838f88b2e46e02d93` |
| 2212 | Historical 4-day Weather Forecast | ? | 9 | `d_0d39850b4a481c503732cdf249cc5cf8`<br>`d_4661b60198b4461f7c44e45782b02c55`<br>`d_6c707b1f1b77aaa658781e90e159a488`<br>`d_5328fdcc05a38080c1f22003a802a372`<br>`d_34aa6a6efde48a73712b03c89a3db52d`<br>`d_344c275fe9f29c13f4e042cc9d0faa66`<br>`d_5cba9b9d8a66ac6e8b9c455749813bab`<br>`d_31127b110fc2166d2d5b0aee992b4a80`<br>`d_af1198af467beb61bc3d354da1dc44dd` |
| 2213 | Historical 24-hour Weather Forecast | ? | 9 | `d_6352cbce0ea1603e28a01186ba47ce62`<br>`d_7544c0783fbbbef03053ca337a01f54d`<br>`d_eeed97e7051e92f1e0ffae31e914d4b9`<br>`d_d60871bc3b7e3889672ed0f1d53e7fc0`<br>`d_c62c61c8644483eee5781c6f79e0ae7f`<br>`d_a0f230b841da4a997eec8fad4a706c86`<br>`d_ef95e630ddb1c620bea75d50986ec028`<br>`d_36358e7cc2878156cf1e152d5b468a89`<br>`d_0e3254694f5c7eaf77478e5fbd580f64` |
| 2214 | Historical Ultraviolet Index (UVI) | ? | 9 | `d_5ab069fa3b9dfd7ac73cc6519effa8bf`<br>`d_fe460588d9e31b8cc0f26e7d25964c1d`<br>`d_86150260d40c7dfd06b8bf41bf234e81`<br>`d_826d2ce0ea17c5ce6f20b054dfa51159`<br>`d_844a1bf0c989ea9d6fbbd44f65ecb180`<br>`d_2f7d5650139b37b9c4fcdd65a01346f7`<br>`d_3cbf725aaaec9da91011675e5b45385c`<br>`d_a1820599c020a49fd640497a0fbfeec0`<br>`d_6dc276435e6da601b1945553b8669f09` |
| 2215 | Historical Pollutant Standards Index (PSI) | ? | 9 | `d_ad4fd39ae771a7194d9aee2b99ce04af`<br>`d_9213cd2e4631f7148ab5932a10df9958`<br>`d_05b35c51664e1bb6f4dcd78478ae1abe`<br>`d_d3fb32451d63dc48dc425146ec014516`<br>`d_10501b71361f97dbbbab82095406c9c5`<br>`d_36ed5dfd3b3b6e69324fa03f4068bb13`<br>`d_1d7c9dbe3f747492579793d72fbbab1c`<br>`d_f4f9c7c443fd60987dbd020b7076e65b`<br>`d_3f0f79298b18c4ec2aa1615dc9f0acd6` |
| 2216 | Historical PM2.5 | ? | 9 | `d_6050827810cdbd55678911dd7c85542d`<br>`d_e7fbefdd306e3f99cbd5886abf7cb0e8`<br>`d_8827a507ba23160cf2d51148c71364f8`<br>`d_618cfa58d1de9b3e157671b15f637bb2`<br>`d_e114821c74bec16c18484afd57de619f`<br>`d_bbee3a73644138d487d5acd0b1c40ff8`<br>`d_7ed60bd5f903ab2d09bf4078e6210a10`<br>`d_2e5049336e1a6e44b4c236a73e6c7e48`<br>`d_468a8a5ff6ab9b781068bd9aaf8792f8` |
| 2246 | Historical Air Temperature across Singapore | ? | 9 | `d_2b359912668f5f55fde28254e9c9092d`<br>`d_320fc57e7871bd0cd7a713f0f6f2f89e`<br>`d_ef585339f3f57862d6cf13edd5a628c1`<br>`d_6a384c5f4d719f33619563b27091b8fb`<br>`d_10d453bc02d1a41daf6373b96b1929e4`<br>`d_557fbb859f12a8af29ef4e1375288165`<br>`d_6fd47a46bd59c5cb70d9561b404d0a64`<br>`d_370bbfc65de96ad93eaefa182135d1c0`<br>`d_910c81fce47f38574015b3882ac59254` |
| 2278 | Historical Relative Humidity across Singapore | ? | 9 | `d_7419c1b8020cbba124cc5de3120debad`<br>`d_0e0e47c0657e4fe3fddae3b9e516ba74`<br>`d_dda4e2961282fe15a2a03209f8c60466`<br>`d_df0a643cabbe0ad9420ce8e2cf0e7ec2`<br>`d_15f4385609fa3aa8f5812872586cbb80`<br>`d_b30e532f095592dfa8fef924c2325b38`<br>`d_6ecc4ed07e7dcc024c22e548aa1e86f6`<br>`d_d6fb7c8f42cacf73af76d17518c39f24`<br>`d_7916c4c0cbe0dfaadaeac4b56d732a2a` |
| 2279 | Historical Rainfall across Singapore | ? | 9 | `d_79a6f0fb898996d415b207bb26ed0fa6`<br>`d_1990a5a1aeaf3dd243cf4dae294a61c4`<br>`d_024fb501ce7092b71bb713eaf54fa7eb`<br>`d_61995f092320e7155b7528050880b502`<br>`d_9e7de44094f876f6804b8b5bcee45c81`<br>`d_3b41598f74f1f11fc3430348fea51af5`<br>`d_42d64cc6c176ace1c52fbb40b9ede302`<br>`d_f864cc30d58b467db83659ad17c737bf`<br>`d_a0b69d3e02576a1fd0ab673e71f83507` |
| 2280 | Historical Wind Speed across Singapore | ? | 9 | `d_8f5b395a1750c915082cc60767a161b8`<br>`d_bd8da65d5c75138c02ee26a93b944c19`<br>`d_fc178195f22643b2bcb387e242466c7f`<br>`d_e35b3c9f4f191e4735767972f7c7b3cb`<br>`d_139acceccddabe1ffcda1d5a59a5b0b8`<br>`d_50a5a13a8dc7cb8e3816f30433012f1f`<br>`d_9ef0ce25fbeba52d3e5e23487d3f40fc`<br>`d_de9a32cc338823ee9d58c3b7576fa267`<br>`d_33f6c1091f73c1451c3aedc4f0061c9c` |
| 2281 | Historical Wind Direction across Singapore | ? | 9 | `d_e09956bd042643535dab477e71644626`<br>`d_4bd9b57adc22a7d604ce46cead6dece4`<br>`d_e395e01b91907832fecf78dc4a8039d2`<br>`d_8cf41a4413991a19ce9bcb4d6f5aa121`<br>`d_2d6e5c7e8d3c9c8c55771b1514a463ce`<br>`d_48db0c70697f48307ab5df8b5c413f92`<br>`d_2fe3393d6ac6859b16f77c4aafcba55d`<br>`d_c9a10c59294e89a8233562435f81b221`<br>`d_c2083cf3e40ddf633b1421ad719067ff` |
