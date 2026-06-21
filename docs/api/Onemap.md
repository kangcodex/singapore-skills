# OneMap (Singapore Land Authority)

The OneMap API is Singapore's authoritative geocoding, routing, and coordinate-conversion service, operated by the Singapore Land Authority (SLA).

**Base URL:** `https://www.onemap.gov.sg`

> **Auth required for almost everything.** As of 2025+, OneMap requires an account token for all endpoints. Register at <https://www.onemap.gov.sg/apidocs/maps> then use the `/api/auth/post/getToken` flow below to obtain an `access_token`. Pass it as `Authorization: Bearer <token>`.
>
> The exception is `/api/common/elastic/search`, which still returns results anonymously but embeds an `"Authentication token missing"` warning in the body.

---

## Search & Geocoding

### Search

```bash
curl --location \
  'https://www.onemap.gov.sg/api/common/elastic/search?searchVal=ang+mo+kio&returnGeom=Y&getAddrDetails=Y&pageNum=1'
```

Query params:
- `searchVal` (required) — search string
- `returnGeom` (`Y`/`N`) — include geometry in response
- `getAddrDetails` (`Y`/`N`) — include full address breakdown
- `pageNum` — page number (results are paginated)

## Coordinate Conversions

> **Auth required.** See "Authentication" below.

All conversions are GET requests with `latitude`/`longitude` (for 4326) or `X`/`Y` (for 3414/3857).

```bash
TOKEN="<your_access_token>"

# WGS84 → SVY21 (lat/lon → x/y in metres)
curl --location \
  -H "Authorization: Bearer ${TOKEN}" \
  'https://www.onemap.gov.sg/api/common/convert/4326to3414?latitude=1.31955&longitude=103.8424'

# SVY21 → WGS84
curl --location \
  -H "Authorization: Bearer ${TOKEN}" \
  'https://www.onemap.gov.sg/api/common/convert/3414to4326?X=28983.788&Y=33506.785'

# WGS84 → Web Mercator
curl --location \
  -H "Authorization: Bearer ${TOKEN}" \
  'https://www.onemap.gov.sg/api/common/convert/4326to3857?latitude=1.31955&longitude=103.8424'

# Web Mercator → WGS84
curl --location \
  -H "Authorization: Bearer ${TOKEN}" \
  'https://www.onemap.gov.sg/api/common/convert/3857to4326?X=11546059.65&Y=148620.49'

# SVY21 → Web Mercator
curl --location \
  -H "Authorization: Bearer ${TOKEN}" \
  'https://www.onemap.gov.sg/api/common/convert/3414to3857?X=28983.788&Y=33506.785'

# Web Mercator → SVY21
curl --location \
  -H "Authorization: Bearer ${TOKEN}" \
  'https://www.onemap.gov.sg/api/common/convert/3857to3414?X=11546059.65&Y=148620.49'
```

## Reverse Geocoding

> **Auth required.** See "Authentication" below.

```bash
TOKEN="<your_access_token>"

# Reverse geocode from WGS84 lat/lon
curl --location \
  -H "Authorization: Bearer ${TOKEN}" \
  'https://www.onemap.gov.sg/api/public/revgeocode?location=1.31955,103.8424&buffer=100&addressType=all'

# Reverse geocode from SVY21 x/y
curl --location \
  -H "Authorization: Bearer ${TOKEN}" \
  'https://www.onemap.gov.sg/api/public/revgeocodexy?location=28983.788,33506.785&buffer=100&addressType=all'
```

`buffer` is in metres. `addressType` accepts `all`, `building`, `block`, `street`, `postal`, `hdb`.

## Routing

> **Auth required.** See "Authentication" below.

```bash
TOKEN="<your_access_token>"

# Public route
curl --location \
  -H "Authorization: Bearer ${TOKEN}" \
  'https://www.onemap.gov.sg/api/public/routingsvc/route?start=1.31955,103.8424&end=1.3521,103.8198&routeType=drive'

# BFA (Barrier-Free Accessibility) variant — wheelchair-accessible routing
curl --location \
  -H "Authorization: Bearer ${TOKEN}" \
  'https://www.onemap.gov.sg/api/bfa/routingsvc/route?start=1.31955,103.8424&end=1.3521,103.8198&routeType=drive'
```

`routeType` values: `walk`, `drive`, `cycle` (check current API for exact set).

## Nearby

> **Auth required.** See "Authentication" below.

```bash
TOKEN="<your_access_token>"

# Nearest bus stops
curl --location \
  -H "Authorization: Bearer ${TOKEN}" \
  'https://www.onemap.gov.sg/api/public/nearbysvc/getNearestBusStops?latitude=1.31955&longitude=103.8424'

# Nearest MRT stations
curl --location \
  -H "Authorization: Bearer ${TOKEN}" \
  'https://www.onemap.gov.sg/api/public/nearbysvc/getNearestMrtStops?latitude=1.31955&longitude=103.8424'
```

## Themes (community / census layers)

> Requires an authenticated OneMap account (see "Authentication" below).

```bash
TOKEN="<your_access_token>"

# List all available themes
curl --location \
  -H "Authorization: Bearer ${TOKEN}" \
  'https://www.onemap.gov.sg/api/public/themesvc/getAllThemesInfo'

# Get metadata for a single theme
curl --location \
  -H "Authorization: Bearer ${TOKEN}" \
  'https://www.onemap.gov.sg/api/public/themesvc/getThemeInfo?themeName=<themeName>'

# Retrieve features within a bbox
curl --location \
  -H "Authorization: Bearer ${TOKEN}" \
  'https://www.onemap.gov.sg/api/public/themesvc/retrieveTheme?themeName=<themeName>&q=&bbox=<xmin>,<ymin>,<xmax>,<ymax>'

# Check theme status / job status for async queries
curl --location \
  -H "Authorization: Bearer ${TOKEN}" \
  'https://www.onemap.gov.sg/api/public/themesvc/checkThemeStatus'
```

## Population Census (popapi)

> Requires an authenticated OneMap account.

```bash
TOKEN="<your_access_token>"

# Planning areas
curl --location \
  -H "Authorization: Bearer ${TOKEN}" \
  'https://www.onemap.gov.sg/api/public/popapi/getPlanningarea'

curl --location \
  -H "Authorization: Bearer ${TOKEN}" \
  'https://www.onemap.gov.sg/api/public/popapi/getPlanningareaNames'

curl --location \
  -H "Authorization: Bearer ${TOKEN}" \
  'https://www.onemap.gov.sg/api/public/popapi/getAllPlanningarea'

# Demographics
curl --location -H "Authorization: Bearer ${TOKEN}" \
  'https://www.onemap.gov.sg/api/public/popapi/getEconomicStatus'
curl --location -H "Authorization: Bearer ${TOKEN}" \
  'https://www.onemap.gov.sg/api/public/popapi/getEducationAttending'
curl --location -H "Authorization: Bearer ${TOKEN}" \
  'https://www.onemap.gov.sg/api/public/popapi/getEthnicGroup'
curl --location -H "Authorization: Bearer ${TOKEN}" \
  'https://www.onemap.gov.sg/api/public/popapi/getHouseholdMonthlyIncomeWork'
curl --location -H "Authorization: Bearer ${TOKEN}" \
  'https://www.onemap.gov.sg/api/public/popapi/getHouseholdSize'
curl --location -H "Authorization: Bearer ${TOKEN}" \
  'https://www.onemap.gov.sg/api/public/popapi/getHouseholdStructure'
curl --location -H "Authorization: Bearer ${TOKEN}" \
  'https://www.onemap.gov.sg/api/public/popapi/getIncomeFromWork'
curl --location -H "Authorization: Bearer ${TOKEN}" \
  'https://www.onemap.gov.sg/api/public/popapi/getIndustry'
curl --location -H "Authorization: Bearer ${TOKEN}" \
  'https://www.onemap.gov.sg/api/public/popapi/getLanguageLiterate'
curl --location -H "Authorization: Bearer ${TOKEN}" \
  'https://www.onemap.gov.sg/api/public/popapi/getMaritalStatus'
curl --location -H "Authorization: Bearer ${TOKEN}" \
  'https://www.onemap.gov.sg/api/public/popapi/getModeOfTransportSchool'
curl --location -H "Authorization: Bearer ${TOKEN}" \
  'https://www.onemap.gov.sg/api/public/popapi/getModeOfTransportWork'
curl --location -H "Authorization: Bearer ${TOKEN}" \
  'https://www.onemap.gov.sg/api/public/popapi/getOccupation'
curl --location -H "Authorization: Bearer ${TOKEN}" \
  'https://www.onemap.gov.sg/api/public/popapi/getPopulationAgeGroup'
curl --location -H "Authorization: Bearer ${TOKEN}" \
  'https://www.onemap.gov.sg/api/public/popapi/getReligion'
curl --location -H "Authorization: Bearer ${TOKEN}" \
  'https://www.onemap.gov.sg/api/public/popapi/getSpokenAtHome'
curl --location -H "Authorization: Bearer ${TOKEN}" \
  'https://www.onemap.gov.sg/api/public/popapi/getTenancy'
curl --location -H "Authorization: Bearer ${TOKEN}" \
  'https://www.onemap.gov.sg/api/public/popapi/getTypeOfDwellingHousehold'
curl --location -H "Authorization: Bearer ${TOKEN}" \
  'https://www.onemap.gov.sg/api/public/popapi/getTypeOfDwellingPop'
```

## Static Maps

```bash
# Get a static map image (PNG) for a given lat/lon/zoom
curl --location \
  'https://www.onemap.gov.sg/api/staticmap/getStaticImage?layerchosen=default&latitude=1.31955&longitude=103.8424&zoom=17&width=512&height=512' \
  -o map.png
```

`layerchosen` options: `default`, `night`, `original`, etc. (See OneMap docs for the full set; some layers require auth.)

## Authentication (for protected endpoints)

```bash
# Get a OneMap access token
curl --location \
  'https://www.onemap.gov.sg/api/auth/post/getToken' \
  --header 'Content-Type: application/json' \
  --data '{
    "email": "your@email.com",
    "password": "your-password"
  }'
```

Response contains an `access_token` field. Pass it as `Authorization: Bearer <token>` for subsequent calls.

If you don't have an account:

```bash
# Register
curl --location \
  'https://www.onemap.gov.sg/api/public/user/registerUser' \
  --header 'Content-Type: application/json' \
  --data '{"email":"your@email.com","password":"..."}'

# Confirm registration (clicked from email link → server will email a confirmation)
curl --location \
  'https://www.onemap.gov.sg/api/public/user/confirmRegistration' \
  --header 'Content-Type: application/json' \
  --data '<confirmation_payload_from_email>'

# Forgot password
curl --location \
  'https://www.onemap.gov.sg/api/public/user/forgetPassword' \
  --header 'Content-Type: application/json' \
  --data '{"email":"your@email.com"}'

# Reset password (after forget-password email)
curl --location \
  'https://www.onemap.gov.sg/api/public/user/resetPassword' \
  --header 'Content-Type: application/json' \
  --data '<reset_payload_from_email>'
```

## Notes

- `searchVal` matches building names, block numbers, postal codes, and street names.
- The `themesvc` and `popapi` endpoints are census/community layers built on Singapore's 2010/2020 census. Check theme status — large bbox queries are async and return a `themeJobId` you poll with `checkThemeStatus`.
- For batch geocoding, rate-limit to ~1 req/s to stay under SLA's published rate limits.
