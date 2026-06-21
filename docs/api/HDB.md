# HDB (Housing & Development Board)

Source authority on Singapore public housing — resale prices, carpark availability, BTO/ballot statistics, property/branch directory, and household survey data.

## Discovery

- **Catalog search:** <https://data.gov.sg/datasets?query=&coverage=&agencies=HDB>
- **Collections endpoint:** `https://api-production.data.gov.sg/v2/public/api/collections?page=N` (filter client-side by `managedByAgencyName == "Housing & Development Board"`)
- **Counts:** **52 collections, 104 datasets** (see full catalog below)

## Realtime APIs (v1, no auth)

### Carpark Availability

Live HDB carpark lot availability across Singapore (HDB-owned carparks; for URA/private carparks use URA datasets).

```bash
curl --location 'https://api.data.gov.sg/v1/transport/carpark-availability'
```

Response shape (truncated):

```json
{
  "items": [
    {
      "timestamp": "2026-06-20T10:00:00+08:00",
      "carpark_data": [
        {
          "carpark_number": "HE12",
          "total_lots": "676",
          "lots_available": "512",
          "lot_type": "C",
          "update_datetime": "2026-06-20T09:59:06+08:00"
        }
      ]
    }
  ],
  "carpark_info": [
    {
      "carpark_number": "HE12",
      "address": "BLK 633/635 HOUGANG AVENUE 8",
      "x_coord": "31996.7563",
      "y_coord": "35580.0203"
    }
  ]
}
```

`lot_type`: `C` = Car, `H` = Heavy Vehicle, `Y` = Motorcycle, `L` = LHV (Light Heavy Vehicle), `B` = Bus.

To resolve a carpark's coordinates to an address, pipe `x_coord`/`y_coord` (SVY21) through the OneMap `3414to4326` converter, then `revgeocode`.

## Dataset Download Flow

> **Auth required.** The `api-open.data.gov.sg` endpoints require a `DATA_GOV_SG_API_KEY`. Register at <https://data.gov.sg/> to get one. Pass it in the `x-api-key` header.

All HDB dataset downloads follow this 3-step pattern. The download URLs are signed S3 URLs and expire after a short period — always re-initiate before downloading.

```bash
DATASET_ID="d_8b84c4ee58e3cfc0ece0d773c8ca6abc"
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
  'https://data.gov.sg/api/action/datastore_search?resource_id=d_8b84c4ee58e3cfc0ece0d773c8ca6abc&limit=10'
# → 404 Not Found (data.gov.sg no longer serves CKAN)
```

## Collection Catalog

All 52 HDB collections, ordered by `collectionId`. Each row maps to one or more child dataset IDs (use the initiate → poll → download flow above to fetch the actual file).

| ID | Name | Frequency | Datasets | Dataset IDs |
|---|---|---|---|---|
| 141 | Active Cases for Home Office Scheme | annual | 1 | `d_22a8f95ed7ddd81425960815efb0f088` |
| 142 | Active Cases of Renting Out of Flat | annual | 1 | `d_2f2c29c3f821461f36c24c6c1dbbe059` |
| 143 | Applications Received to Finance Purchases or Refinance Existing Mortgage Loans with Bank Loans | annual | 1 | `d_fbb057402a1d4a953a9b46babbdbf1fc` |
| 144 | Bookings for New Flats | annual | 1 | `d_e6079cb5bf0c2450372b1054f37e6e79` |
| 145 | Cumulative Area Reclaimed for Engineering Projects | annual | 1 | `d_55b4740017623c1d5e884e0e06793e87` |
| 146 | Cumulative Number of Sites Under Selective En Bloc Redevelopment Scheme (SERS) | annual | 1 | `d_741b128b977a08537af3350292975127` |
| 147 | Flats Constructed | annual | 1 | `d_f43ed2489fad49824702c2169561a432` |
| 148 | HDB Carpark Information | monthly | 1 | `d_23f946fa557947f93a8043bbef41dd09` |
| 149 | HDB Bond Information | ad-hoc | 1 | `d_83ff203724fe94184ae5c172f26942e0` |
| 150 | HDB Property Information | quarterly | 1 | `d_17f5382f26140b1fdae0ba2ef6239d2f` |
| 151 | HDB Public Housing Building Under-Construction | quarterly | 2 | `d_c78ab4aa29d1024ba92530b303d77605`<br>`d_930e662ac7e141fe3fd2a6efa5216902` |
| 152 | HDB Resale Price Index | quarterly | 1 | `d_14f63e595975691e7c24a27ae4c07c79` |
| 153 | Housing Grants Awarded, by Type of Housing Grant | annual | 1 | `d_a223380e5856cf06f7eac223e5902230` |
| 154 | Demand for Rental and Sold Flats | annual | 1 | `d_4b4ee36346b27fe35c529588900340b2` |
| 155 | Directory of Renovation Contractors | ad-hoc | 1 | `d_9973d2c119ed4dd1560aebf8f0829b86` |
| 156 | Median Rent by Town and Flat Type | quarterly | 1 | `d_23000a00c52996c55106084ed0339566` |
| 157 | Median Resale Prices for Registered Applications by Town and Flat Type | quarterly | 1 | `d_b51323a474ba789fb4cc3db58a3116d4` |
| 158 | Number of Applications for HDB Loan Eligibility Letters | annual | 1 | `d_38ec7e5cd735d597ab85765d2ef1a39b` |
| 159 | Number of Applications Registered for Resale and Rental Flats | annual | 1 | `d_c47771d51ac7d86ac300835b27848ff0` |
| 160 | Number of Approved Applications for Financial Assistance Measures by Financial Year | annual | 1 | `d_c2b211174c4e0f546b4d8e92c6aaf365` |
| 161 | Number of Dwelling Units and Commercial Developments Built | annual | 1 | `d_f97971e730d675ae046cc75690468c02` |
| 162 | Number of Households Billed for Upgrading | annual | 1 | `d_7b03b129f6f89d7bca1fbe50b3b5e18d` |
| 163 | Renting Out of Flat Approvals by Flat Type, Quarterly | quarterly | 1 | `d_dad4567fc02596774010f765567780e3` |
| 164 | Number of Resale Applications Registered by Flat Type, Quarterly | quarterly | 1 | `d_02aa4bb51bc674f3a2d0b9bb6911d934` |
| 165 | Dwelling Units under HDB's Management, by Town and Flat Type | annual | 1 | `d_07b1eeeb22efdf7faf5bd6a13667359d` |
| 166 | Renting Out of Flats 2023 | monthly | 1 | `d_c9f57187485a850908655db0e8cfe651` |
| 167 | Resale Transaction by Flat Type (based on registered cases) | annual | 1 | `d_27af98d638a80103319cb7499c220fe6` |
| 168 | Sample Household Survey: Role and Relationship of HDB Resident Population with Owner or Registered Tenant | other | 1 | `d_307210f9b1557b86752229b499046726` |
| 169 | Sample Household Survey: Economically Active HDB Resident Population, by Ethnic Group and Flat Type | other | 2 | `d_bdc3b0ce289a7f95309b82454cf2c366`<br>`d_c0f741f3d30fcd87af0b4e40d6855bcf` |
| 170 | HDB Branches | ad-hoc | 2 | `d_3535361f967e8005dc44b4ce4d2c5276`<br>`d_d05753e45b0c400aaac1099260b3ef8d` |
| 171 | HDB Cycling Paths Under-Construction | half_year | 2 | `d_9e363d0eb7910dc7f53c44e4fe654586`<br>`d_da0e9b505998cd3d252bba4b55d8b33d` |
| 172 | HDB Lift Upgrading Programme Proposed and Under-Construction (LUP) | quarterly | 2 | `d_2b6ecf82731170304e0c53d2cd7522d7`<br>`d_9b5886a025c8db1192a8fada42bd4330` |
| 173 | HDB Neighbourhood Renewal Programme Proposed and Under-Construction (NRP) | quarterly | 2 | `d_156a38dc024d2b20a6c1d0c0179e797c`<br>`d_e8f374a588f945f57e4390a7db326b47` |
| 174 | Sample Household Survey: HDB Resident Population and Growth Rate | other | 2 | `d_6961d4bc056dadcca47e23127a3ac174`<br>`d_740bc018cfe20d3d6f6c53fe6a69fa6b` |
| 175 | HDB Roads Under Construction | half_year | 2 | `d_18a5c4f91867e6fdca411d9ef0945c29`<br>`d_157d034c579e12a095c967ca2a463d01` |
| 176 | Sample Household Survey: Labour Force Participation Rate for HDB Resident Population, by Ethnic Group and Flat Type | other | 2 | `d_ec0244d088cfe409f328b65f3d74f964`<br>`d_9d46d391dba808d7b171d66204a30aa7` |
| 177 | Price Range of HDB Flats Offered | annual | 2 | `d_6f3c2c819680fb139b66869d7aa4bd6e`<br>`d_2d493bdcc1d9a44828b6e71cb095b88d` |
| 178 | Sample Household Survey: Employed HDB Resident Population Aged 15 Years and Above by Occupation | other | 2 | `d_fcfc5a44d2e3d783b895f4b4016b84d9`<br>`d_9c6271959306ec3d2726f1fc296794e8` |
| 179 | Sample Household Survey: HDB Resident Population by Geographical Distribution | other | 2 | `d_c6edbb9c9c3ed1642a89e7515a6baca7`<br>`d_0a6c6d71f6fa14e2d27e406f1d018439` |
| 180 | Sample Household Survey: Type of Family Nucleus of HDB Households, by Ethnic Group and Flat Type | other | 2 | `d_e31c9070e0b1363584683b81d984bfa7`<br>`d_b553c9286f58ba96ef0ee1088743da52` |
| 181 | Sample Household Survey: HDB Households, by Ethnic Group and Flat Type | other | 3 | `d_6f0b9b4e1a64a09f5b76c8a2c1234d2d`<br>`d_db69c88a1ff684356b8b38dc0e9b432c`<br>`d_666b7f6884acb34320145917e61016aa` |
| 182 | Completion Status of HDB Developments | annual | 3 | `d_9bbcd0c9b0351c7f41c9bfdcdc746668`<br>`d_582672d2f972194786d01efe151892b7`<br>`d_4b69ac0ff084e96f03197ad346248918` |
| 183 | Sample Household Survey: Size of HDB Households, by Ethnic Group and Flat Type | other | 4 | `d_668967b5fce80dc42255a3ac1671f97c`<br>`d_a5095643f088aafc71d5aeae09c1f08f`<br>`d_3b626812cc3ea5cafa20490bb996eb0b`<br>`d_abf82c79fc908b12bb8d631e6853e98f` |
| 184 | Sample Household Survey: Number of Income Earners in HDB Households, by Ethnic Group and Flat Type | other | 4 | `d_6c8c70ffa11110434d3fd6a4e2d67416`<br>`d_1a2ea5e9309802413f650aba1b103166`<br>`d_b794139ebf82ed3e087b22dda685bd84`<br>`d_47d8e6246e296c04d1ab68af5f138d51` |
| 185 | Sample Household Survey: Dependency Ratio of HDB Resident Population, by Ethnic Group and Flat Type | other | 4 | `d_8e83c90e9c5418c4e2f1475c6e8665e2`<br>`d_c99a6b0384bcfc0d7f7a175da170f7ca`<br>`d_dfe5545683f5c4ec6b69a06ffcabe524`<br>`d_3bd6955a00e8d917b11b08f475401060` |
| 186 | Sample Household Survey: Gender Composition of HDB Resident Population, by Ethnic Group and Flat Type | other | 4 | `d_473f502212568e7cd7c55e699a998f1d`<br>`d_6f287a0e35413557148e148e8e32ca31`<br>`d_450e4211e777260f5dcdf8f81987b35a`<br>`d_ec6b85ff143d7a62597fac7817ec3a67` |
| 187 | Sold and Rented HDB Properties and Facilities | annual | 4 | `d_2657c8b576a51b7a944d22187001e8b1`<br>`d_e93c058371800bf3b708000ff47bc048`<br>`d_a32043811ffb2e44c861fa24c4c425d1`<br>`d_67966e5fd5dce14cf9fa5f0bc5164faf` |
| 188 | Cumulative HDB Properties/Facilities Completed Since 1960 | annual | 5 | `d_676bc7fa1d69de0e74c0ceb8897dcb10`<br>`d_5f446ba7edac1ef0e606195606a41a6a`<br>`d_caa8f8f91cb000f4b2c4a52fd22d516c`<br>`d_07561cf169a8608fd97c5a6eb112ba60`<br>`d_007b79018e47094e8cd62bf6f6d9ed8e` |
| 189 | Resale Flat Prices | monthly | 5 | `d_8b84c4ee58e3cfc0ece0d773c8ca6abc`<br>`d_43f493c6c50d54243cc1eab0df142d6a`<br>`d_2d5ff9ea31397b66239f245f57751537`<br>`d_ebc5ab87086db484f88045b47411ebc5`<br>`d_ea9ed51da2787afaf8e51f827c304208` |
| 190 | Sample Household Survey: Age of HDB Resident Population, by Ethnic Group and Flat Type | other | 6 | `d_26bcaadd552d0b77bb13ea9c671bac6b`<br>`d_cb55223f678fb7702181fc95c587e03f`<br>`d_a24664d0ad7d21edfc7245e0195d7503`<br>`d_2f840db99e6aa00de54447a1ed81e597`<br>`d_5232a4da63a47af020617483693d5195`<br>`d_c5f8097e161feac48fd76a8577844fc9` |
| 191 | Sample Household Survey: HDB Elderly and Future Elderly Resident Population | other | 7 | `d_326034ad1aa58165096567150dd8bde9`<br>`d_4180067b350bc9839a4cea487841d5d1`<br>`d_76eb0a0d52db203284c50ccfba84c815`<br>`d_6c678a9e6cf49086c1fea012c40ceafe`<br>`d_1a5bb230195b27f5982682d4bb66bcb0`<br>`d_995d47e4632e72e4f0a589ed5e51bd36`<br>`d_c24f6b8078ee721f7191906ca1b3a367` |
| 2033 | HDB Existing Building | other | 2 | `d_16b157c52ed637edd6ba1232e026258d`<br>`d_60a6c3d88483cf63d2063c93771a6aeb` |
