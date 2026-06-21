# URA (Urban Redevelopment Authority)

Master Plan 2019, private property price/rental index, carpark info, and all URA planning/SDCP geographic layers. The largest of the four agencies by collection count (273 collections, 509 datasets) because of the heavily segmented Master Plan layers.

## Discovery

- **Catalog search:** <https://data.gov.sg/datasets?query=&coverage=&agencies=URA>
- **Collections endpoint:** `https://api-production.data.gov.sg/v2/public/api/collections?page=N` (filter client-side by `managedByAgencyName == "Urban Redevelopment Authority"`)
- **Counts:** **273 collections, 509 datasets** (see full catalog below)

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
| `d_90d86daa5bfaa371668b84fa5f01424f` | Master Plan 2019 Land Use layer | GeoJSON |
| `d_cc2f9c99c2a7cb55a54ad0f522016011` | Master Plan 2019 Planning Area Boundary | GeoJSON |
| `d_222bfc84eb86c7c11994d02f8939da8d` | Master Plan 2019 Rail Line layer | GeoJSON |
| `d_d3f41348bf6d6be82371249de564d057` | Master Plan 2019 Road layer | GeoJSON |
| `d_55b414e81d30722cce1963c47497d99e` | URA Carpark Information by Type of Lot | ad-hoc |
| `d_c1429fe02d1a488efbba71fc1bfc60bb` | URA Season Parking | ad-hoc |
| `d_82424908e6b72d8735337c811cc5122e` | Master Plan 2019 Building layer | GeoJSON |
| `d_f65e490a8ad430f60a9a3d9df2bff2a0` | Private Property Price Index of Non-landed Residential Properties | quarterly |
| `d_a283de8cb3b4e80a228bf5f5e0bc4449` | Completed Private Residential Units Sold in the Quarter | quarterly |

## Collection Catalog

All 273 URA collections, ordered by `collectionId`. Each row maps to one or more child dataset IDs (use the initiate → poll → download flow above to fetch the actual file).

| ID | Name | Frequency | Datasets | Dataset IDs |
|---|---|---|---|---|
| 1639 | Completed Private Residential Units Sold in the Quarter, Quarterly | quarterly | 1 | `d_a283de8cb3b4e80a228bf5f5e0bc4449` |
| 1640 | Conservation Sites Sold By URA | ad-hoc | 1 | `d_1eefe4d027b4d59437321f25e00be9e7` |
| 1641 | Development Charge Sector Map | ad-hoc | 2 | `d_9d4c638d3329227be1b4ff16168c0b75`<br>`d_9b76a25cbbec977b10830c2ee7cdbb4d` |
| 1642 | Development Register Map | half_year | 2 | `d_6b6b8381c580720a40ca8234f2917e30`<br>`d_5fea232c6e60ea4a896e355e3c05141c` |
| 1643 | Executive Condominium Units Launched and Sold, Quarterly | quarterly | 1 | `d_19c79027c2e6be3c39d637151bd2188d` |
| 1644 | Master Plan 2003 Conservation Area Boundary Line | other | 2 | `d_3d81bb6c098e5b17e4a8649d467fb558`<br>`d_652d15b0d1de390fe3a0c37971a7fc5b` |
| 1645 | Master Plan 2019 Building layer | other | 2 | `d_82424908e6b72d8735337c811cc5122e`<br>`d_e8e3249d4433845bdd8034ae44329d9e` |
| 1646 | Master Plan 2019 Land Use layer | other | 1 | `d_90d86daa5bfaa371668b84fa5f01424f` |
| 1647 | Master Plan 2019 Planning Area Boundary | ad-hoc | 1 | `d_cc2f9c99c2a7cb55a54ad0f522016011` |
| 1648 | Master Plan 2019 Rail Line layer | other | 1 | `d_222bfc84eb86c7c11994d02f8939da8d` |
| 1649 | Master Plan 2019 Road Graphic layer | other | 2 | `d_40a1c9a071eef21dfe46da9570e72f5a`<br>`d_95a29fbb10cf94a3c263d33861d7b6c6` |
| 1650 | Master Plan 2019 SDCP Park and Open Space layer | ad-hoc | 2 | `d_26027c1602ba699b9074cea8d772d937`<br>`d_9ec9fe2ff2c6c520dd8679933a4a059a` |
| 1651 | Master Plan 2019 Symbol Text layer | other | 1 | `d_dc4918b82cb79cbb706c8f35bc412242` |
| 1652 | Median Rentals and Vacancy of Office Space by Category, Quarterly | quarterly | 0 | _(none)_ |
| 1653 | Median Rentals and Vacancy of Retail Space by Locality, Quarterly | quarterly | 0 | _(none)_ |
| 1654 | Private Property Price Index of Non-landed Residential Properties by Locality, Quarterly | quarterly | 1 | `d_f65e490a8ad430f60a9a3d9df2bff2a0` |
| 1655 | Private Residential Property Transactions in Core Central Region, Quarterly | quarterly | 1 | `d_c287c8be114bfa7d055b27ab2c87de83` |
| 1656 | Private Residential Property Transactions in Outside Central Region, Quarterly | quarterly | 1 | `d_1a7823f3d31e7db4b426833833762bab` |
| 1657 | Private Residential Property Transactions in Rest of Central Region, Quarterly | quarterly | 1 | `d_5785799d63a9da091f4e0b456291eeb8` |
| 1658 | Private Residential Property Transactions in the Whole of Singapore, Quarterly | quarterly | 1 | `d_7c69c943d5f0d89d6a9a773d2b51f337` |
| 1659 | Uncompleted Private Residential Units Sold in the Quarter by Market Segment, Quarterly | quarterly | 1 | `d_e1c5b0df62729e69c82716355ef295ba` |
| 1660 | Rentals of Non-Landed Residential Buildings, Quarterly | quarterly | 1 | `d_149ac00a2734bb0a03867bbe2ec0e7b0` |
| 1661 | Sale Position of Executive Condominiums with Pre-Requisites for Sale, Quarterly | quarterly | 1 | `d_8b71bc3e1386261039d7ad95efdc3328` |
| 1662 | Uncompleted Private Residential Units Launched in the Quarter by Market Segment, Quarterly | quarterly | 1 | `d_70824d34defde87d88faccc5d5b1c6ea` |
| 1663 | Unsold Private Residential Units with Planning Approvals by Market Segment, Quarterly | quarterly | 0 | _(none)_ |
| 1664 | URA Carpark Information by Type of Lot | ad-hoc | 1 | `d_55b414e81d30722cce1963c47497d99e` |
| 1665 | URA No of Dwelling Units | annual | 2 | `d_f7e3eadb926c778a932176283f53365c`<br>`d_be71daeab5930f96b90ad2857454d876` |
| 1666 | URA Project (PUBLIC) | other | 0 | _(none)_ |
| 1667 | URA Season Parking | ad-hoc | 1 | `d_c1429fe02d1a488efbba71fc1bfc60bb` |
| 1668 | URA Site With Conserved Building | other | 2 | `d_bb9f31e0d98c6e1633b4b642f15ec3a6`<br>`d_4d210863090143682eca22c7a94e067d` |
| 1669 | Vacant Sites Sold By URA | ad-hoc | 1 | `d_e225b635fbe3ecf5b378447e4b517939` |
| 1670 | Approval, Construction Commencement and Completion of Commercial Development | annual | 2 | `d_34fc34d1be1fd5ae0d4eb19077da450e`<br>`d_a4c4d4f5b85f808708827e016668ed75` |
| 1671 | Approval, Construction Commencement and Completion of Private Residential Properties | annual | 1 | `d_38ed343cc32c3e0b6ebc43a6058e9860` |
| 1672 | Available and Vacant Commercial Properties | annual | 1 | `d_d23a8c26d4a9530d651fbe0248a3f1fc` |
| 1673 | Available and Vacant Executive Condominiums | annual | 0 | _(none)_ |
| 1674 | Available and Vacant Private Residential Properties | annual | 1 | `d_28b999e22ae1e23caf80172227d23830` |
| 1675 | Capacity of URA Parking Places | quarterly | 2 | `d_9bf8620ecfdc8a5f8f77e3f02160af5c`<br>`d_66fd217ca88eb204f995a08b34b4bc3a` |
| 1676 | Private Property Price Index by Type, Quarterly | quarterly | 2 | `d_f333bf427c827efb484cf57a73ff700a`<br>`d_97f8a2e995022d311c6c68cfda6d034c` |
| 1677 | Conservation Area Map | ad-hoc | 2 | `d_f105660dd749c0aafa1a858f435603f2`<br>`d_89f09395985c13c7a664e0342ff3694a` |
| 1678 | Development Charge Rate | half_year | 2 | `d_16edb7b98dfb6e9d9402c362e664730c`<br>`d_443c0c1af080e61e9ea6d0bc3ae933b1` |
| 1679 | Master Plan 1998 Planning Area Boundary (No Sea) | ad-hoc | 2 | `d_8d0d2665195329fa1ad2f97fc28456ab`<br>`d_dec48c94989d4f17d778e3c59f9a52e0` |
| 1680 | Master Plan 1998 Region Boundary (No Sea) | ad-hoc | 2 | `d_a1872ab3ea2e07b055f2955de7248b6d`<br>`d_58ec3f889ace525fd3e7cec6b8bf5a49` |
| 1681 | Master Plan 1998 Subzone Boundary (No Sea) | ad-hoc | 2 | `d_3c3a3afaaf9a10b7e4e0cd4fec1b4b70`<br>`d_76e75d1f980113773b437a28d138d24b` |
| 1682 | Master Plan 2008 Planning Area Boundary (No Sea) | ad-hoc | 2 | `d_50a3ca3b8d9d47f6d43eb1e2b8201dec`<br>`d_80a6f548e63d18bbb3d6bd7a7d05e64e` |
| 1683 | Master Plan 2008 Region Boundary (No Sea) | ad-hoc | 2 | `d_89c64733ceea38b44be5f007e026e5d7`<br>`d_835e547fee2d145e28856c0bfaeeab17` |
| 1684 | Master Plan 2008 Subzone Boundary (No Sea) | ad-hoc | 2 | `d_9707b9b3d3d86a02b1dca29c36036060`<br>`d_d1d0f39bc9164a3228987358a8cf6ce1` |
| 1685 | Master Plan 2014 Above Ground Line | ad-hoc | 2 | `d_0ba6149c1ae1224d5b774642058dc46c`<br>`d_aa6be78b4c212e0b547814735cf278fd` |
| 1686 | Master Plan 2014 Building | ad-hoc | 2 | `d_91acddfb0ccc514a65a404206e69dad7`<br>`d_292d7dea4ecb6dda8eb13541bebd2683` |
| 1687 | Master Plan 2014 Conservation Area Text | ad-hoc | 2 | `d_a3735a9dee65980dd92690506e8e950c`<br>`d_4b10039e49ce06c42895e7554dee7376` |
| 1688 | Master Plan 2014 Conservation Boundary Line | ad-hoc | 2 | `d_1f9e36aa3f8d573d7be970de79c29a8f`<br>`d_de13b97e8def5ca19abeb84cf89eaa07` |
| 1689 | Master Plan 2014 Conserved Building | ad-hoc | 2 | `d_356d31fa333a5a76e42328cbebcc1bd3`<br>`d_ebf42eab2349ef61f97690e20a20e174` |
| 1690 | Master Plan 2014 Gross Plot Ratio Line | ad-hoc | 2 | `d_7ab0d91229ff2f005f3d644f5eac82e2`<br>`d_134b8042e3669c74eece4a4be0656c09` |
| 1691 | Master Plan 2014 Land Use | ad-hoc | 2 | `d_4400f3f9d5b64ccdafeb8b0a07664a7c`<br>`d_df7b1fc30f97d862c4ef20652d97ba64` |
| 1692 | Master Plan 2014 Land Use Text | ad-hoc | 2 | `d_72f1c540753acb93a7ed7493e1773ea6`<br>`d_a70c6a49bec84c6a76c8b04cc94d19aa` |
| 1693 | Master Plan 2014 Monument Building | ad-hoc | 2 | `d_7f3a1354852d0d8ec98d4418ef6011c9`<br>`d_8b3ecfdee5f721367b7d9845c05be64d` |
| 1694 | Master Plan 2014 Monument Site Boundary | ad-hoc | 2 | `d_1f5524cf79c74d6c4a928bddc2853a86`<br>`d_209c471f0b9c5a08e64fa9ee7cf673e9` |
| 1695 | Master Plan 2014 Monument Text | ad-hoc | 2 | `d_817e06322a06484a29ecb0f843223cd4`<br>`d_34835d12ccac564a07ee44f201ecc0b5` |
| 1696 | Master Plan 2014 Nature Line | ad-hoc | 2 | `d_49dc8bf1f5185804d9d6d75976e17f3c`<br>`d_08daa838a1db5ec8cc348d1e22096536` |
| 1697 | Master Plan 2014 Nature Text | ad-hoc | 2 | `d_001146a730035d445319e8ee86529b9d`<br>`d_108b4b43514cae565be43b601e25c1ea` |
| 1698 | Master Plan 2014 Other Line | ad-hoc | 2 | `d_7d053fe7210ae3956a26b0c154db3746`<br>`d_74f6f68dc351f5ed65443310a2891af4` |
| 1699 | Master Plan 2014 Other Text | ad-hoc | 2 | `d_30812be44d00834e099f10fa4482bb39`<br>`d_2aa4aa10db937a13e7dfbabf6a3676db` |
| 1700 | Master Plan 2014 Planning Area Boundary (No Sea) | ad-hoc | 2 | `d_3132a1c15c5cb5f34a9971e54ce67a58`<br>`d_ae891df9d691b091f5383f87b842645a` |
| 1701 | Master Plan 2014 Planning Area Boundary (Web) | ad-hoc | 2 | `d_6d6fd6505f23d7fb90dec567afd555bb`<br>`d_1f81f5f4167db3b0bef9e63f0f0d045d` |
| 1702 | Master Plan 2014 Rail Line | ad-hoc | 2 | `d_d12ed1afcb8a618528b596cee86c9246`<br>`d_1634dd07f90823449b933016e5634fad` |
| 1703 | Master Plan 2014 Rail Station | ad-hoc | 2 | `d_e5b0e670d35171049dc540bfb3285897`<br>`d_69789d150bb7aa1eb156f51d0ea53ce9` |
| 1704 | Master Plan 2014 Rail Station Text | ad-hoc | 2 | `d_a2ec5dcb72f9aa518ced80f924df046a`<br>`d_71beec3c3baa2a55d726590470e31dcc` |
| 1705 | Master Plan 2014 Region Boundary (No Sea) | ad-hoc | 2 | `d_207f8bebb1fb4a35ccf90a0845041ded`<br>`d_3a19667d35455733976ed3f289eca22a` |
| 1706 | Master Plan 2014 Region Boundary (Web) | ad-hoc | 2 | `d_cae8e0c42c72584936b0ca5193805796`<br>`d_ae0b4a01593ea5a076b0c85d9cc23524` |
| 1707 | Master Plan 2014 Subzone Boundary (No Sea) | ad-hoc | 2 | `d_49fc1d59dd39726b5fe3ad7f0f4f220e`<br>`d_2781554f03047c05bd200db3b9c224e3` |
| 1708 | Master Plan 2014 Subzone Boundary (Web) | ad-hoc | 2 | `d_d14da225fccf921049ab64238ff473d9`<br>`d_5cb80a95445f236737f6bc2bfe5f159d` |
| 1709 | Master Plan 2014 Underground Line | ad-hoc | 2 | `d_a31f680d7df8167424c3faa5fe86cc17`<br>`d_2a47b7a11b5ca1b36ddcf17a60b51282` |
| 1710 | Master Plan 2019 Monument Building layer | other | 2 | `d_1111cc35cbd2d258f0de4d1634654466`<br>`d_bc4b13a83e841872a297b2df05261377` |
| 1711 | Master Plan 2019 Monument Number layer | other | 2 | `d_55c49160dc59369c1dabe2df5aef2a5a`<br>`d_267350ed943fd623efed4b50ad268e14` |
| 1712 | Master Plan 2019 Monument Site layer | other | 2 | `d_c82fca3e765086f631a725cf2d21ee7b`<br>`d_2901b6d6ffe5c93679ab7bf04797b155` |
| 1713 | Master Plan 2019 Other Line layer | other | 2 | `d_dfd37db176ed8417401a5ecbc145aa4b`<br>`d_ce168eecad7933d33b9337814d9c1332` |
| 1714 | Master Plan 2019 Other Text layer | other | 2 | `d_bafc1986fdb065f3c73ee1ba3af452b6`<br>`d_ef5397203b8e2fcf52a01f3da6554054` |
| 1715 | Master Plan 2019 Rail Station layer | other | 2 | `d_8d886e3a83934d7447acdf5bc6959999`<br>`d_38231948814802f2f4368d95c6fdf571` |
| 1716 | Master Plan 2019 Rail Station Name layer | other | 2 | `d_bd17bca97549a4ab0fb7b6ad102d640c`<br>`d_6f078283ca1b48017a565109b9eaeb92` |
| 1717 | Master Plan 2019 Region Boundary (No Sea) | other | 2 | `d_bf4d24df9129d5a8ff8cf82e20959ee0`<br>`d_ef3fc5c7a62139471ebc9ffa598b60e8` |
| 1718 | Master Plan 2019 Road layer | ad-hoc | 1 | `d_d3f41348bf6d6be82371249de564d057` |
| 1719 | Master Plan 2019 SDCP Building Height Control layer | other | 2 | `d_ee8e2e0d13a50a699f9100029b8c0b0a`<br>`d_5ac3dc864699b147ce4336f5351dee91` |
| 1720 | Master Plan 2019 SDCP Building Height Control Relaxation layer | other | 2 | `d_75f54d927e9797d3b65ef095770155b3`<br>`d_6fccced3bee10f15a3946f124af341da` |
| 1721 | Master Plan 2019 SDCP Building Height Control Text layer | ad-hoc | 2 | `d_22899c44540ff47fa67ff0fc756950ee`<br>`d_92355dd0ca6651a4c69d787ca7d0328b` |
| 1722 | Master Plan 2019 SDCP Car Lite Precinct layer | other | 2 | `d_8072b48ad671f267aa881f76775ff567`<br>`d_11c483e8c3f29e7f6e09ed16e73d7c92` |
| 1723 | Master Plan 2019 SDCP Car Lite Precinct Name layer | other | 2 | `d_03fe30f6e65b4449aab6647b3c1d07a6`<br>`d_9fb538a0a39b080c2b3c985ab60e875d` |
| 1724 | Master Plan 2019 SDCP Civic District Boundary layer | other | 2 | `d_fff12058a53038dba0a3b4804680c808`<br>`d_85419fb5a37d2bc388981859ec385d29` |
| 1725 | Master Plan 2019 SDCP Conservation Area layer | ad-hoc | 2 | `d_8c8162ffb9deb8d11b00623048f65a70`<br>`d_1de7aacae7a8cdd5d61b6d879f951959` |
| 1726 | Master Plan 2019 SDCP Integrated Transport Hub layer | other | 2 | `d_3ebc4424254906fb51e6b34916df10a9`<br>`d_1c217f3f202b281831e1bb0865b71494` |
| 1727 | Master Plan 2019 SDCP Landed Housing Area layer | other | 1 | `d_cef89e55a52d87e433d7460aa4236e18` |
| 1728 | Master Plan 2019 SDCP Landed Housing Area Leader Line layer | other | 2 | `d_e9e9ba577d5b2d359cd1cc3abbac3388`<br>`d_7bc7dc177fffeb3751f2c45b2e12ce0a` |
| 1729 | Master Plan 2019 SDCP Landed Housing Area Text layer | other | 2 | `d_5bb472b597121183747651ec6b56b583`<br>`d_df2f1f4bb14e554dbe535b003379ac7b` |
| 1730 | Master Plan 2019 SDCP Monument layer | other | 2 | `d_f6845e32608857ee2f8d5bc4ef1afcba`<br>`d_902751d97053686227e3e545b52ec6da` |
| 1731 | Master Plan 2019 SDCP Monument Number layer | other | 2 | `d_113fc7bba2e0ff102d7343e2840b119f`<br>`d_7d89ff744118d86334d2c1fcba4dad0b` |
| 1732 | Master Plan 2019 SDCP Monument Site layer | other | 2 | `d_7ac10cc1e10442e98083d5e75db12166`<br>`d_b4abc7b175ad15da1974c348f5c709e7` |
| 1733 | Master Plan 2019 SDCP Nature Boundary layer | other | 2 | `d_ba06412f3a4469e8ce4354d67b8944bc`<br>`d_a45dc4e6b4dc81cd1ac46cc34a9f1211` |
| 1734 | Master Plan 2019 SDCP Nature Boundary Line layer | other | 2 | `d_0ab1d7a2f87ac4958c2f989ec17a846b`<br>`d_a6756fed5ed0d44c137c79ca370aac34` |
| 1735 | Master Plan 2019 SDCP Nature Boundary Text layer | ad-hoc | 2 | `d_4d26163e789f0c12f0e27a194884d679`<br>`d_d4297c454e5ff644579121caf208665e` |
| 1736 | Master Plan 2019 SDCP Park and Open Space Text layer | ad-hoc | 2 | `d_7ff35fdcde2d1949be305daec9f0473f`<br>`d_d8ddc0ee2113b8ae7e15a682aa1b3c31` |
| 1737 | Master Plan 2019 SDCP Park Connector Line layer | ad-hoc | 2 | `d_2af336c61fe43a0131ac1d6455147e6c`<br>`d_3e902a9be74243ad68998e66b7dd4970` |
| 1738 | Master Plan 2019 SDCP Park Connector Text layer | ad-hoc | 2 | `d_30404bb06ccc9880c63dc007b67a3670`<br>`d_8b72c584078e39f61d47376dc5a7fb78` |
| 1739 | Master Plan 2019 SDCP Park Landscaped Rooftop layer | other | 2 | `d_395d9326fab657514f2c964e2321ee1e`<br>`d_44ac2204e3d1122ec4cb9eb7ee576e4c` |
| 1740 | Master Plan 2019 SDCP Park Leader Line layer | other | 2 | `d_48cc043eb94baf07d8d4832a4be2d4ca`<br>`d_378cabea699149321fbdf8fb98ee4a11` |
| 1741 | Master Plan 2019 SDCP Park Mall, Promenade and Public Link | other | 2 | `d_f72246aac3251a588888e58d9660dbf0`<br>`d_41dcf0e232c88d0bb0d492084db8edde` |
| 1742 | Master Plan 2019 SDCP Public Space layer | other | 2 | `d_4abad189bae782ff4c89ad83a2a672a9`<br>`d_fda6cbc90d92874f2d2243702f40a12e` |
| 1743 | Master Plan 2019 SDCP Street Block layer | other | 2 | `d_07b3e42fba1ec69cd6044bedd3545ccb`<br>`d_08d760bec1f45e23beaee52d9207708b` |
| 1744 | Master Plan 2019 SDCP UNESCO Heritage Site layer | other | 2 | `d_7f71726b0c1ab098e99a91eba7d00e53`<br>`d_313c52d02fcaedc35b141e722bbe3872` |
| 1745 | Master Plan 2019 SDCP Urban Design Area layer | other | 2 | `d_e21c8d98400c9457706b2988cafe43ef`<br>`d_96c22747a33123ca88355e862ec443ba` |
| 1746 | Master Plan 2019 SDCP Urban Design Corridor layer | other | 2 | `d_3fc1a5a67a55da9e238911171671fbe7`<br>`d_765ad10eee03cf6acebdd0de3aead614` |
| 1747 | Master Plan 2019 SDCP Urban Design Guideline layer | other | 2 | `d_bc3abe6a8c6d732b09e7e33a1cf7be9e`<br>`d_42886ce671e349d227a7e2b1c2ca2668` |
| 1748 | Master Plan 2019 SDCP Waterbody layer | ad-hoc | 2 | `d_0b0792ae30cd6cce62e5ea55fc37860e`<br>`d_e0207b5f0f4313f146183690fcda4505` |
| 1749 | Master Plan 2019 Subzone Boundary (No Sea) | other | 2 | `d_8594ae9ff96d0c708bc2af633048edfb`<br>`d_0900fdcfdb4666fe2a630f37a532fc06` |
| 1750 | Master Plan 2019 Symbol Line layer | other | 2 | `d_fe6db1a882ca2ceddb208d1ab6c7d874`<br>`d_8e6b9d7ffa8ec3d81a408f6a28f1635a` |
| 1751 | Master Plan 2019 Underground Structure layer | other | 2 | `d_14ead08d03e3dcd429f8b5296b1dd70d`<br>`d_08a6fe04200b0892bcf37496ed351464` |
| 1752 | MP08 Land Use | ad-hoc | 2 | `d_b5c6c1d7b564d5659d252316fe594366`<br>`d_097f251ddf0611f3d20bba91c0ece712` |
| 1753 | MP08 Mapsheet Conservation Area Text | ad-hoc | 2 | `d_265db7f5bb36111753df8d69f995df46`<br>`d_b980ce2001575c9449fe7f8d74101ce5` |
| 1754 | MP08 Mapsheet Conservation Area Text-CA | ad-hoc | 2 | `d_9692fd2cdec36f605a575c6a2f4c3b0a`<br>`d_53e5018be1706b832fc8c3fb97130e9e` |
| 1755 | MP08 Mapsheet GPR Text-CA | ad-hoc | 2 | `d_cbc8f50a3fc0662d460fd70bda4b8ae1`<br>`d_fea4b0bab45fda7af9f574c35c6b6cb5` |
| 1756 | MP08 Mapsheet Gross Plot Ratio Text | ad-hoc | 2 | `d_913a4499cb6b75f357d3294633c91bf2`<br>`d_c240d04f50aa233ab76c59ca9896bf70` |
| 1757 | MP08 Mapsheet Land Use Text | ad-hoc | 2 | `d_412069706423ebbd5194f62165b38ca5`<br>`d_e10c41d1885fccef78a698a43214c8a9` |
| 1758 | MP08 Mapsheet Land Use Text-CA | ad-hoc | 2 | `d_f4c65e325eb5e03f9daf03750cf54a8c`<br>`d_544cd547626869f0572c85574dd1ff95` |
| 1759 | MP08 Mapsheet Major Road Name | ad-hoc | 2 | `d_383f74f9752ccd448bfa1b1adae14333`<br>`d_1bf3b1923fd3dcc761de6bb083eb4e8e` |
| 1760 | MP08 Mapsheet Major Road Name-CA | ad-hoc | 2 | `d_7beedaaa7b8d037e8fd7afd459a39e9e`<br>`d_15f3b4719ec039b43738caec34331081` |
| 1761 | MP08 Mapsheet Minor Road Name | ad-hoc | 2 | `d_dffe4bff8bf020fa2a62618963d43678`<br>`d_f66e0838eb00c4768c6fbc655ddebe1a` |
| 1762 | MP08 Mapsheet Minor Road Name-CA | ad-hoc | 2 | `d_21d265a54e2f17e164f503d21b23f49e`<br>`d_30ef752e6c8c23a35d266f00365326cd` |
| 1763 | MP08 Mapsheet Monument Text | ad-hoc | 2 | `d_cfcb8d1cfb225c9b4c0bb7fb3e0c8472`<br>`d_b2562a1a4ab56f16be0767e09449f21b` |
| 1764 | MP08 Mapsheet Monument Text-CA | ad-hoc | 2 | `d_4a9feeb38508c38f7ec3e44b70b2ddb6`<br>`d_b9648dd088eec099121659be9d240536` |
| 1765 | MP08 Mapsheet Nature Text | ad-hoc | 2 | `d_c976548393c9a425297f88ccb65d5bf1`<br>`d_5fda4f2c03e65672100fba8a57762f4b` |
| 1766 | MP08 Mapsheet Nature Text-CA | ad-hoc | 2 | `d_92da4eab76ddd575e074b9ea052d52d1`<br>`d_50c2b6524876683b204a4d6622d5e557` |
| 1767 | MP08 Mapsheet Other Text | ad-hoc | 2 | `d_b688ac2779ba32f733d1519e3545319d`<br>`d_ff8e966ffa53fb7b235969bbd476a91e` |
| 1768 | MP08 Mapsheet Other Text-CA | ad-hoc | 2 | `d_012428d0ec60843c2df97fc048b133e4`<br>`d_b3e388695ff19fe5ec7f64b7ce38f3fc` |
| 1769 | MP08 Mapsheet Rail Station Name | ad-hoc | 2 | `d_0053ab2fd2fb1a56423f29324edaa58d`<br>`d_c4fa381a90b2b275a0f20e481ac82471` |
| 1770 | MP08 Mapsheet Rail Station Name-CA | ad-hoc | 2 | `d_8022385874b3bd5e91ca332136224124`<br>`d_37c8815d5851a1599750c8e63f9293a5` |
| 1771 | MP08 Monument Boundary | ad-hoc | 2 | `d_55d358e3fe7333c40704ac0961bbc513`<br>`d_9cc735bb2a8448168092d52f9383804b` |
| 1772 | MP08 Other Line | ad-hoc | 2 | `d_73539c534e0e483160b7e1db51070724`<br>`d_bcd37c7afe7d1e7933fa521608d838a2` |
| 1773 | MP08 Rail Line | ad-hoc | 2 | `d_ecd5e7ce5d86880686039c48974fc5f8`<br>`d_fbdefb8fbd1f21d6690a32cbe8ec6d5f` |
| 1774 | MP08 Rail Station | ad-hoc | 2 | `d_3e318e902f33e24b2467215cfc6de9fc`<br>`d_a5ef357843d9583d922ef3611c847205` |
| 1775 | MP14 SDCP AGU PLAN - 1st Storey (Encouraged) | ad-hoc | 2 | `d_50d6c1eeed7d64f6654b00df2059dfb7`<br>`d_b2a1dc03b58ab69525ff8df05d90bab2` |
| 1776 | MP14 SDCP AGU PLAN - 1st Storey (Mandatory) | ad-hoc | 2 | `d_cfae4f4a3560a316486f5e2a2231f227`<br>`d_9ca72cad0254793be67bd97d9763cfa1` |
| 1777 | MP14 SDCP AGU PLAN - 2nd Storey (Encouraged) | ad-hoc | 2 | `d_f1f48a95eeda7302f4a39b2f463a62c0`<br>`d_4a5775b1ba9aa3a8c4c0c67b123c457e` |
| 1778 | MP14 SDCP AGU PLAN - 2nd Storey (Mandatory) | ad-hoc | 2 | `d_9b12b70190daf90fb55a3b60d678c149`<br>`d_11f0f9d073dd5f9fbeb73e2914b94516` |
| 1779 | MP14 SDCP AGU PLAN - Basement (Encouraged) | ad-hoc | 2 | `d_c0f696ccc6428128150feede7bf82a12`<br>`d_d76c82069edf6d315d433c824bb17c26` |
| 1780 | MP14 SDCP AGU PLAN - Basement (Mandatory) | ad-hoc | 2 | `d_fd8b6c1388bfbb9437f078f74ca8f2d8`<br>`d_7b33751c8f869efa3c5805cc5d29af5a` |
| 1781 | MP14 SDCP AGU PLAN - MRT Station Name | ad-hoc | 2 | `d_74980b9b0391c1d617567224e217c3cf`<br>`d_e32aa53f95e9e8b8491f724260523247` |
| 1782 | MP14 SDCP AGU PLAN - MRT Station Symbol | ad-hoc | 2 | `d_545e5e606c023959d970a76268bb34c1`<br>`d_77b4fdda9f586ea6aeabbc8eab1fd306` |
| 1783 | MP14 SDCP BH PLAN - Building Height Control Plan (metre AMSL) | ad-hoc | 2 | `d_69bce44ccad018f56c54906c9224d006`<br>`d_aa3924eda75b07243b13bc2b3281ccfa` |
| 1784 | MP14 SDCP BH PLAN - Building Height Control Plan (No of storeys) | ad-hoc | 2 | `d_7d1a2d2e0260eb3b425c3d1beaef48e7`<br>`d_1fccfaed5a20213bcd5c74d69603419b` |
| 1785 | MP14 SDCP BH PLAN - Building Height Control Relaxation Area | ad-hoc | 2 | `d_55201a7752c85a161f119041fa1a1819`<br>`d_7f904eaede8c8982bc0f96c89b4cb369` |
| 1786 | MP14 SDCP BH PLAN - Building Height Control Text (No of storeys) | ad-hoc | 2 | `d_b7df50048b00ad506005bb99de023728`<br>`d_8fdf5535bd232bd6ea8a4b3f6a36285a` |
| 1787 | MP14 SDCP LHA PLAN - Landed Housing Area | ad-hoc | 2 | `d_804127cb8369f7cba2db49b9f0cf165b`<br>`d_043d81e53653107e2ef36141916da96a` |
| 1788 | MP14 SDCP LHA PLAN - Landed Housing Area Arrow Line | ad-hoc | 2 | `d_70daf825a9096945e547073934bbca1e`<br>`d_2bcc9e4072813ace690905ba92749a33` |
| 1789 | MP14 SDCP LHA PLAN - Landed Housing Area Text | ad-hoc | 3 | `d_492838abb5b4459676c036ecd3c9ffe8`<br>`d_e74337f3cb15479941dec14e86473cd2`<br>`d_21f77012b5614b605f1abae0698c60a3` |
| 1790 | MP14 SDCP PW PLAN - Arrow and Leader Line | ad-hoc | 2 | `d_fce52fcea6642af46ce2cd29fa1ae936`<br>`d_5e8837ffc0cb048c1184c4218dc40f99` |
| 1791 | MP14 SDCP PW PLAN - Island and Other Text | ad-hoc | 2 | `d_ecd9a16f7ba38b1583755301ccea8fbd`<br>`d_932cbe1ca7975b82baa922936f6cf8f5` |
| 1792 | MP14 SDCP PW PLAN - Landscape Rooftop | ad-hoc | 2 | `d_84a60c827afd399a5b352974a8da6914`<br>`d_95c3383848262a440213e5dbd922de5b` |
| 1793 | MP14 SDCP PW PLAN - Mall and Promenade | ad-hoc | 2 | `d_d0c0c992372ec27d14ce81100110e288`<br>`d_ab5757915447509c0db9b8a2a144d2f7` |
| 1794 | MP14 SDCP PW PLAN - Mall and Promenade (Line) | ad-hoc | 2 | `d_ee984834287c8b8f1449c43bc88890bb`<br>`d_dfc4c9d2ab767c37c47652527300b64e` |
| 1795 | MP14 SDCP PW PLAN - National Park | ad-hoc | 2 | `d_ad279ecb5883fddd194bca71c3ba8f9c`<br>`d_2a28925b2b4579037a936c23bc3f1ab7` |
| 1796 | MP14 SDCP PW PLAN - National Park Annotation | ad-hoc | 2 | `d_c437597e49d19c703c4419092952fd20`<br>`d_92b45d10d50b0fd2b37673cb47f70e6b` |
| 1797 | MP14 SDCP PW PLAN - National Park Boundary Line (offset) | ad-hoc | 2 | `d_c3d8660cf83d73db6c4e8df20e58d90f`<br>`d_bf283054b146798fda6a78f0be229d55` |
| 1798 | MP14 SDCP PW PLAN - Nature Boundary | ad-hoc | 2 | `d_ce9ddc5d196dfbfb38c69730f7e2bff1`<br>`d_60b001196dc4cb0dd4056b8ee570468b` |
| 1799 | MP14 SDCP PW PLAN - Nature Boundary Line (offset) | ad-hoc | 2 | `d_1cbfb44d9f01a44d7884f0ef528839f4`<br>`d_6c8b675a503d3ec96c5c635bebbd56e5` |
| 1800 | MP14 SDCP PW PLAN - Park Connector | ad-hoc | 2 | `d_bdcabc5b45a83011a40b04cb0a713806`<br>`d_1639ac5fd56d23a1f6583bb7ddf4dc62` |
| 1801 | MP14 SDCP PW PLAN - Park Connector Line | ad-hoc | 2 | `d_89899f41c73fbf3457c2544c700a3869`<br>`d_3e05e4b07798d35ec9f1a9ac8f73c2fe` |
| 1802 | MP14 SDCP PW PLAN - Parks and Open Space | ad-hoc | 2 | `d_83bdc9dbb7d05756280e97179ce49d2d`<br>`d_8a1e3346989229106221f0e9e09b8480` |
| 1803 | MP14 SDCP PW PLAN - Parks and Open Space Name | ad-hoc | 2 | `d_0831c8b220a3cca22a5112305a0d9551`<br>`d_3af42a25138deed1d9b4406593ef2b53` |
| 1804 | MP14 SDCP PW PLAN - Public Space | ad-hoc | 2 | `d_0b8a1f3ed8a78f4940f9accff9a7b761`<br>`d_71a555818b1c3ccb1ad95d99e7e922d0` |
| 1805 | MP14 SDCP PW PLAN - Waterbody | ad-hoc | 2 | `d_9753146d5972ea81d362b98be175ff10`<br>`d_9cf966bb78d00abab3b55a6732777529` |
| 1806 | MP14 SDCP SBUD PLAN - Conservation Area Boundary | ad-hoc | 2 | `d_fa6832ee582a539bcc9fe428668729e5`<br>`d_d0414d1a18dc8f453f1a4763e932e4cd` |
| 1807 | MP14 SDCP SBUD PLAN - Conservation Area Line (offset) | ad-hoc | 2 | `d_1eb4f2a679cf0fe4ec14fdf0c2e1465b`<br>`d_c9cd02f3797ba7d1f8d0122cc42ad795` |
| 1808 | MP14 SDCP SBUD PLAN - Conserved Building | ad-hoc | 2 | `d_11c39f3a9b1611e5dc2662082ff69aed`<br>`d_e2f9bf37faa71fdae0bcd2ec73d8d2b7` |
| 1809 | MP14 SDCP SBUD PLAN - Designated Urban Design Area | ad-hoc | 2 | `d_295524c70d2d62a70bd6bd344a95bd4f`<br>`d_811431e815bc01325b7816547fde18ca` |
| 1810 | MP14 SDCP SBUD PLAN - Designated Urban Design Area Text | ad-hoc | 2 | `d_6cd3d6977d107c500a7fe3be29ac3ecc`<br>`d_95974ab46dd4463c9d94666735fa121e` |
| 1811 | MP14 SDCP SBUD PLAN - Monument Building | ad-hoc | 2 | `d_59a21453f30e675e86401f49b87f239b`<br>`d_c0d74e6bb17255199bc670f85ddb885c` |
| 1812 | MP14 SDCP SBUD PLAN - Monument Number | ad-hoc | 2 | `d_65777bbfc9d56c2f3e4de8d5157b464c`<br>`d_b304106dd5b20af0b594f5409838f8ec` |
| 1813 | MP14 SDCP SBUD PLAN - Monument Site Boundary | ad-hoc | 2 | `d_52f2a8107070a24c6356ecd679f27194`<br>`d_8e3e1397527c09fad3d9409766ede472` |
| 1814 | MP14 SDCP SBUD PLAN  - Street Block Plan | ad-hoc | 2 | `d_f5d4541707c9d92428e4099ec823ac1c`<br>`d_d4a92b06c779ddad78a2cc5234019c83` |
| 1815 | MP14 SDCP SBUD PLAN - Urban Design Area | ad-hoc | 2 | `d_ec414faaa70627339111e923c7b0178f`<br>`d_231ec0dd0ce9e4bdeea887874ab0982a` |
| 1816 | SDCP Nature Reserve | ad-hoc | 2 | `d_c8a8172673a56150e3b8f82c409fa141`<br>`d_71d47f8bccddb63cff8566e2e4ea4d56` |
| 1817 | Planning Area Census 2010 | ad-hoc | 2 | `d_d54358fe9f96daf3fc6904791e9428b7`<br>`d_7b72c5cb0c7bee019dfabbec741354bb` |
| 1818 | Private Residential Property Price Index | quarterly | 2 | `d_c0c26484c655113b0ab5abaa0a49952b`<br>`d_f76411aa34d98559b6194419d796ce59` |
| 1819 | Region Census 2010 | ad-hoc | 2 | `d_4040186ab8d95aee267ab7de906b5ecd`<br>`d_3e8580b940ed7f0867bf790e5326f461` |
| 1820 | Private Property Rental Index by Type, Quarterly | quarterly | 2 | `d_862c74b13138382b9f0c50c68d436b95`<br>`d_8e4c50283fb7052a391dfb746a05c853` |
| 1821 | SDCP National Park | ad-hoc | 2 | `d_81c0429d0f722f594aedd51210966956`<br>`d_cc91b0b59d5ea99a7b292a7d0824d9a5` |
| 1822 | SDCP Nature Area | ad-hoc | 2 | `d_dedefb145735431c9fe9d22d15b17e13`<br>`d_382bd40f0631a02d9b20896fa979c134` |
| 1823 | SDCP Activity 1st Storey | ad-hoc | 2 | `d_69c472423f9afedf5ba7d80d7d1592ad`<br>`d_1050e3a303e73f507345ee43654440c0` |
| 1824 | SDCP Activity 1st Storey Basement | ad-hoc | 2 | `d_8b6f4a9dcc05f894e8a48dfe6001a15f`<br>`d_e9eda1123404fa8751e8d8e1b4bc342b` |
| 1825 | SDCP Building Height Control Plan-Amsl | ad-hoc | 2 | `d_240a851f947dd4b3c9cbca808a4a5f09`<br>`d_51494a55fd12f07f60dbadfa8e6697b3` |
| 1826 | SDCP Building Height Control Plan-Storey | ad-hoc | 2 | `d_ea911775a043f6ab0328db301d7f163d`<br>`d_166ecd30d995c5cf283509a5bb7e2789` |
| 1827 | SDCP Building Height Control Plan Text-Amsl | ad-hoc | 2 | `d_2579b516f38204b7018d339580688034`<br>`d_f01ed0b0ccebec0106c8aff04bd9d674` |
| 1828 | SDCP Conservation Area Boundary | ad-hoc | 2 | `d_21152ce0981e3fad7c71d888209d3b83`<br>`d_771034fa6194c93430535299e05d3311` |
| 1829 | SDCP Detailed Urban Design Guidelines | ad-hoc | 2 | `d_d6baefc0b1d1310eb0ae51f818940486`<br>`d_68a235a485ff1bd85c8c0f18bae3bd11` |
| 1830 | SDCP Interim Park | ad-hoc | 2 | `d_60f5500add14e3c07b1a933b542b96f0`<br>`d_81fbe8c9d84837d173b77bf8cb6da1f9` |
| 1831 | SDCP Landed Housing Area | ad-hoc | 2 | `d_d915b6ade6868f1d82d5df8bbd639363`<br>`d_8dc00b2b96477944e5f8402ac6edbc31` |
| 1832 | SDCP Landscape Rooftop | ad-hoc | 2 | `d_984490e5f00aaa371d8b5288813ff531`<br>`d_3d9622eea553371fbb9973284202ac2c` |
| 1833 | SDCP Monument Boundary | ad-hoc | 2 | `d_46f8b9bff447926377b91efc878a91dc`<br>`d_17cceb821bcfa0f9b77e1b797303ec44` |
| 1834 | SDCP Monument Building | ad-hoc | 2 | `d_c0538e3ee406ed3a8c5cdbb5ec15cc25`<br>`d_4f6aaacf0a7e8ba5debaafd04ff82456` |
| 1835 | SDCP Monument Text | ad-hoc | 2 | `d_cbe5368c9272af5ded6fe0a823189013`<br>`d_70d2585455c4a10fd61b10bc5706cfe0` |
| 1836 | SDCP MRT Station Point | ad-hoc | 2 | `d_eeed7424e3d5c22b17d17bbb1d2fbb10`<br>`d_e6ca44d2edb1d0ada18c2b6b8cb175a7` |
| 1837 | SDCP MRT Station Point Name | ad-hoc | 2 | `d_b1662d28c2340182b526c480a9e5b33e`<br>`d_a95a2681feaae4ef1a2de597faa6cfab` |
| 1838 | SDCP Nature Resv or National Pk or Nature Area Txt | ad-hoc | 2 | `d_eaa68eb7a3963f0d26a766f2decf2431`<br>`d_b4d749a8bab3013f0d7f119a5d065bef` |
| 1839 | SDCP Park | ad-hoc | 2 | `d_dec52717093b20d30677a938d39f0dac`<br>`d_c1c7810196ea27efedc1816becd44358` |
| 1840 | SDCP Park Connector | ad-hoc | 2 | `d_ecaf168965932ea188102d231e253a4a`<br>`d_98a63d7d20d5a2199caa392599b70796` |
| 1841 | SDCP Park Connector Line | ad-hoc | 2 | `d_54e97aeae8a11a9c3a2bb4bce1ca3bab`<br>`d_4821a484aef22857f484aa20f0e237ca` |
| 1842 | SDCP Park Name | ad-hoc | 2 | `d_844e9cea328d416ee72b877cf892a287`<br>`d_93508d1096ad0b519400d0a325aeae0e` |
| 1843 | SDCP Promenade | ad-hoc | 2 | `d_cb79def897dfbaaef5eee30be6e17224`<br>`d_5281a8faf962dfe63d8ed8a0766e1e23` |
| 1844 | SDCP Promenade or Interim Park Connenctor Line | ad-hoc | 2 | `d_0463c97ec5a68d9977f213ba18da3bab`<br>`d_e7b41bbc31639ad55fef393f6a0977b4` |
| 1845 | SDCP Public Space | ad-hoc | 2 | `d_434d4e40029fd22acc3c133abd513ae3`<br>`d_ae48f720f433bfe47e8ca155e728c1c3` |
| 1846 | SDCP Street Block Plan | ad-hoc | 2 | `d_494cef4f3bd792d5791be936add45b5a`<br>`d_6f372babada58fd08e4e1b0b4f499bf6` |
| 1847 | SDCP Urban Design Guidelines | ad-hoc | 2 | `d_78f6ea2d8d11ed34bcdfdd620243e273`<br>`d_b6e3ac0a130d5a669e45be1463769d9c` |
| 1848 | SDCP Waterbody | ad-hoc | 2 | `d_ac96e2529e7493b4bcda8c6f882b8676`<br>`d_d67ba6a899dbd1aa3a6a4e3abf00765a` |
| 1849 | SDCP Waterbody Name | ad-hoc | 2 | `d_ec507b5a601025f990630b5a2dfa3c9f`<br>`d_44757e75c879f9d7005e8807cce02b27` |
| 1850 | Subzone Census 2010 | ad-hoc | 2 | `d_02cba6aeeed323b5f6c723527757c0bc`<br>`d_329b1a8026ffe8f7ef0c60874e88c1f2` |
| 1851 | Supply of Commercial Properties in the Pipeline by Development Status | annual | 1 | `d_fd59b378382d9120f872ee08c7b26380` |
| 1852 | Supply of Executive Condominiums in the Pipeline by Development Status | annual | 1 | `d_4e8073b6cf272998f14fd970a24c1639` |
| 1853 | Supply of Private Residential Properties in the Pipeline by Development Status | annual | 2 | `d_baa848bbdbf4af7b4d709f147fcf3c9b`<br>`d_7a882bd3d44374a7f701fc6a07620bf8` |
| 1854 | URA Parking Lot | quarterly | 2 | `d_d959102fa76d58f2de276bfbb7e8f68e`<br>`d_51024081689217ae976a6987db337b16` |
| 1855 | URA Sale Sites | ad-hoc | 2 | `d_0e2b42f98535686282031a42c9c7b05a`<br>`d_bdd2c54fa27bdce7643ed905b9e173ab` |
| 1981 | Master Plan 2019 SDCP Cycling Path layer | ad-hoc | 2 | `d_4d1c99c6bb6f002ee566b8f55ffb0d58`<br>`d_9326f791b521187f503149712fc400ef` |
| 1982 | Master Plan 2019 SDCP Conserved Building layer | ad-hoc | 2 | `d_3d73d61e5f5fe3ce52ac5d86b395d0b2`<br>`d_f3f701b89243490455d511847f8c95fc` |
| 2031 | Master Plan 2019 Road Name layer | other | 2 | `d_93f8f9b3a463fc491b25d9a49f1dc654`<br>`d_352b7b58625ed3ff7db4c1ab13f2b35b` |
| 2037 | Master Plan 2003 MRT Line | other | 2 | `d_ae38cc7a5c706d33f115bebc01f9e4f7`<br>`d_a1441fb8b093e5e14a77a1e79ed194fc` |
| 2040 | Master Plan 2003 MRT Name | other | 2 | `d_dbc192abee39f51efecc0adbe9f1a75d`<br>`d_bae25854ceba2bdffb3cf157aee123d4` |
| 2042 | Master Plan 2003 Conservation Area Text | other | 2 | `d_d52c03795ad70ab5cc25e9f7f4fa9f26`<br>`d_ffcbe841ebf4ad146b01dd98814452cc` |
| 2043 | Master Plan 2003 Gross Plot Ratio Text | other | 2 | `d_cc6c47963a74cb10cccd68829f1b2c28`<br>`d_aca7d65830cae37efa80d7630620c588` |
| 2044 | Master Plan 2003 Gross Plot Ratio Line | other | 2 | `d_8cd45074bd202c98a14309703496ed63`<br>`d_5c1bfb6253692ca70ea57917a42321f9` |
| 2045 | Master Plan 2003 National Park Line | other | 2 | `d_0dc514a8d95d0a5fcc967b148efd6799`<br>`d_3f46d5dff440437b07b1effb4c4a0795` |
| 2046 | Master Plan 2003 Land Use Text | other | 2 | `d_8997382479d0b76e931fc27192cb010e`<br>`d_1a48c5fbe685a1c87795735eeaccc725` |
| 2047 | Master Plan 2003 National Park Text | other | 2 | `d_18a47e3e307475042a7ffd5d59b2191a`<br>`d_32700659c8ae2d1175ca14d73fb04da3` |
| 2048 | Master Plan 2003 Nature Reserve Text | other | 2 | `d_dd919ea6ce196b22eceedc73e32796e9`<br>`d_18a2f6b5ba1d479c88ba2b2be3a96cec` |
| 2050 | Master Plan 2003 Railway Line | other | 2 | `d_578951a3bf445c5ec9aa4e1e09fecaf0`<br>`d_a8f85655c9ce23100bf6ece8bd96bd97` |
| 2054 | Master Plan 2003 Land Use | other | 2 | `d_78c9a05019ea8594a657c192bddcd2d6`<br>`d_c8d2ff96d071a0ee4a135cbc6b0cf609` |
| 2055 | Master Plan 2003 Minimum Base Plot Ratio | other | 2 | `d_d76e282ad66c6afb5882872ac884fb61`<br>`d_ac146164955294efcba313061ddf2d79` |
| 2056 | Master Plan 2003 LRT Line | other | 2 | `d_0c07ca2d2e2e9cbb766f4ad8a527168d`<br>`d_a8cd5169a746fd85cfc7eb67dd634a51` |
| 2058 | Master Plan 2003 Monument Text | other | 2 | `d_ade878be574b3bb016708ec2b2e40915`<br>`d_063532513a430600bec6dfd4f3915f2d` |
| 2059 | Master Plan 2003 White Quantum Text | other | 2 | `d_0aad6b466044b379e932b9bfaa7d3b47`<br>`d_a3e48a7cc6d9c07350c8ecab801b1648` |
| 2069 | Amendment to MP2014 Monument Site Boundary | ad-hoc | 2 | `d_b2f20eee50d171b3900721528c54b08d`<br>`d_1dc7b02ef08056c402e4479a066af110` |
| 2070 | Amendment to MP2014 Above Ground Line | ad-hoc | 2 | `d_e9771484480cb79092c02b5bda1f35e6`<br>`d_cae2f7c05369b1f12173de4396d1a2cd` |
| 2071 | Amendment to MP2014 Conservation Boundary Line (offset) | ad-hoc | 2 | `d_ef88482163be784cde5aa2cc852dd95a`<br>`d_91010a4bf16f4b993607f0ccd70ba08d` |
| 2073 | Amendment to MP2014 Gross Plot Ratio Line (offset) | ad-hoc | 2 | `d_fb55d636d5869145b5097e3c5da90d15`<br>`d_c5be78af6f86ab9da0440ff900d99890` |
| 2076 | Amendment to MP2014 Land Use Text | ad-hoc | 2 | `d_e673f3d152e935f61677da557ec815a6`<br>`d_97d4b4b25bfcd9bf05715b57550cf5fe` |
| 2078 | Amendment to Master Plan 2019 Symbol Text layer | ad-hoc | 2 | `d_151115e39eeede076bad214b2e93342a`<br>`d_63cc1d624d6a9320483734648a4fc842` |
| 2079 | Amendment to MP2014 Rail Line | ad-hoc | 2 | `d_15fedf3e20474f69373e526fdf623b6f`<br>`d_125fc6c86fa9acce7a1de135770a8720` |
| 2081 | Amendment to Master Plan 2019 Building layer | ad-hoc | 2 | `d_ee3bd86e1334fbc58b520cd987090e54`<br>`d_bf2b5db32c64be95d21cade5bc757b9c` |
| 2083 | Amendment to Master Plan 2019 Other Text layer | ad-hoc | 2 | `d_6e560a1c5428740b25a4d12dc3586956`<br>`d_5bb5dbac9f505521a782872b6855df00` |
| 2086 | Amendment to MP2014 Building | ad-hoc | 2 | `d_71df24d467aaf553cf69e4449da7b3d5`<br>`d_55212cda1576d883f48ec23245c6b2c3` |
| 2087 | Amendment to MP2014 Conserved Building | ad-hoc | 2 | `d_02f0a4a1d198f3678f697edffc028de8`<br>`d_f7f9763057cd03efa6dcecb104d20173` |
| 2088 | Amendment to MP2014 Other Line | ad-hoc | 2 | `d_81c4cfd58a5291b2b264cfa801493db1`<br>`d_413f475881a5a27cbe47b4c46f497ad0` |
| 2089 | Amendment to MP2014 Land Use | ad-hoc | 2 | `d_6d8bba518bf424592a5291a1c99fbcf2`<br>`d_3759e05898b8bfc6a013829107a475d4` |
| 2090 | Amendment to MP2014 Monument Building | ad-hoc | 2 | `d_934b60e2f289ca9a9e919ddb23f7942e`<br>`d_ed55e21070c2c3fb226b64e66ec947b1` |
| 2091 | Amendment to MP2014 Nature Text | ad-hoc | 2 | `d_14521804fba0c9a24c4c261fed00d89e`<br>`d_a5a110145f65f7c321828effb753485e` |
| 2092 | Amendment to MP2014 Gross Plot Ratio Text | ad-hoc | 2 | `d_a9da7da628e083dff085fd4cb2d07afd`<br>`d_c9690f410315fbdf4cba3573d11c4f5e` |
| 2093 | Amendment to MP2014 Underground Line | ad-hoc | 2 | `d_379472bbc3e57d1c1e1588dee376096c`<br>`d_b57f7626eeed4c08545732801e605c54` |
| 2094 | Amendment to MP2014 Nature Line | ad-hoc | 2 | `d_c41523940e7cc6a2ef57ac535db8d2c3`<br>`d_893be5b161ac9c426afd53e45ce4d163` |
| 2095 | Amendment to MP2014 Road Name | ad-hoc | 2 | `d_7f666579b0f52bf801ad1039dca8b286`<br>`d_76138706b2310f287ae10b1a02d1bcc1` |
| 2096 | Amendment to MP2014 Monument Text | ad-hoc | 2 | `d_4f7b19c288b2c77923c27abbb1b90119`<br>`d_5a5d4ad53bcedda973cf325c179a5ba0` |
| 2097 | Amendment to Master Plan 2019 Monument Number layer | ad-hoc | 2 | `d_2c52ac8273c0facfba2be8121d9aee97`<br>`d_9a99a3ed1b29526631966f7618ffe734` |
| 2098 | Amendment to Master Plan 2019 Monument Building layer | ad-hoc | 2 | `d_e3e2091dcac52b7c143b67ee53d93ded`<br>`d_e3fedb620b88804a3ec6166882b16259` |
| 2099 | Amendment to MP2014 Rail Station Text | ad-hoc | 2 | `d_3f162672107f169d0f49babb19d666f9`<br>`d_75f554887e7f5031197b76f0ad6bd436` |
| 2100 | Amendment to Master Plan 2019 Other Line layer | ad-hoc | 2 | `d_077938876fb795f1249afcb5fe45fe25`<br>`d_3594e8f9489ba96fb04e9be1e42fb6f8` |
| 2101 | Amendment to Master Plan 2019 Rail Station Name layer | ad-hoc | 2 | `d_5cb3563c5584bb533dfc3fbec97153e8`<br>`d_fd356f10c5e0920240baeadcc2d5ee14` |
| 2102 | Amendment to Master Plan 2019 Road Name layer | ad-hoc | 2 | `d_05c01c4d790989db80a58c4a24378c04`<br>`d_8da07117026e2b7705b5f264ef58fb49` |
| 2103 | Amendment to Master Plan 2019 Underground Structure layer | ad-hoc | 2 | `d_ea00679316060060cac8b0db6c304ff5`<br>`d_4f808bdd0086f7eb05e133937acb8269` |
| 2104 | Master Plan 2019 Planning Area Boundary (No Sea) | other | 2 | `d_4765db0e87b9c86336792efe8a1f7a66`<br>`d_6c6d7361dd826d97b91bac914ca6b2ac` |
| 2105 | Amendment to Master Plan 2019 Rail Line layer | ad-hoc | 2 | `d_e8bf3cff62f97300817d1fdcce382584`<br>`d_080924a72e11f6a4441fff8467f24095` |
| 2107 | Amendment to Master Plan 2019 Land Use layer | ad-hoc | 2 | `d_c0e06af6b1a36e6a82223f67c1e17fbd`<br>`d_f8adc7bd980dd15861c83ff370a72eaa` |
| 2109 | Amendment to Master Plan 2019 Road Graphic layer | ad-hoc | 2 | `d_fc51c8e2af0691c60a8fb3359a7d6a25`<br>`d_083b56d5b04fd33d0fa9fa3651021499` |
| 2110 | Amendment to Master Plan 2019 Rail Station layer | ad-hoc | 2 | `d_9a6bdc9d93bd041eb0cfbb6a8cb3248f`<br>`d_ce14e203aec255405d9c10f8b1930594` |
| 2111 | URA No of Dwelling Units (current year) | other | 0 | _(none)_ |
| 2112 | Amendment to MP2014 Conservation Area Text | ad-hoc | 2 | `d_103d944e0510a26382872dead994b667`<br>`d_b2df562151b5fa5e7e550bcad813ba58` |
| 2113 | Amendment to MP2014 Other Text | ad-hoc | 2 | `d_482dbfe45f24658f6ac931b56e71e279`<br>`d_10cb7e5776a6d136da41af31df1fa84c` |
| 2114 | Amendment to MP2014 Rail Station | ad-hoc | 2 | `d_af90df38d609c426c73bc9acea366786`<br>`d_0a39b2bbb83a5b0efc50a71ca7a19e7f` |
| 2115 | Amendment to Master Plan 2019 Monument Site layer | ad-hoc | 2 | `d_2a9bde71d16bf9e98530a86130bab404`<br>`d_d2b2b70e49e9b771664f70e705c0b346` |
| 2116 | Amendment to Master Plan 2019 Symbol Line layer | ad-hoc | 2 | `d_d1f75da15d366d767c991198647dce13`<br>`d_bc56c91528a8f56877aa2ffbcc828269` |
