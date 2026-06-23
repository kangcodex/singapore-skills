---
name: agent-match-skill
description: "Find a CEA-registered property salesperson (estate agent) in Singapore. Look up by name or registration number, filter by postcode sector, attach track-record from CEA monthly transaction records. Uses Council for Estate Agencies (CEA) data from data.gov.sg. Use when the user asks 'find me an agent', 'is this salesperson registered?', 'who are the agents in my area?', or 'show me agents who have closed deals in TOWN'."
---

# agent-match-skill

A Singapore property salesperson (estate agent) directory backed by CEA's public register. Look up active salespersons by name or registration number, optionally filter to a postcode sector, and attach track-record (closed transaction count by town + flat type) pulled from CEA's monthly transaction records dataset.

## Quick Start

```bash
# Look up by name
python3 skills/agent-match-skill/scripts/agent_match.py --name "Alice Tan"

# Look up by registration number
python3 skills/agent-match-skill/scripts/agent_match.py --registration-no R012345X

# Filter to a postcode sector (e.g. postal district 23)
python3 skills/agent-match-skill/scripts/agent_match.py --name "Alice Tan" --postcode 570123

# Attach track-record (count of closed deals in Tiong Bahru, 5-room HDB)
python3 skills/agent-match-skill/scripts/agent_match.py --name "Alice Tan" \
    --town "TIONG BAHRU" --flat-type "5-ROOM"
```

Stdlib only — no `pip install`. Auth: reads `DATA_GOV_SG_API_KEY` from env if set; works anonymously otherwise (lower rate limit).

## Triggers

Run this skill when the user says any of:

- "Find me a property agent in TOWN"
- "Is R012345X a registered salesperson?"
- "List agents with the name Alice Tan"
- "Who are the active salespersons in district 09?"
- "Show me agents who closed HDB deals in Bishan last quarter"

Do not run for: real estate lawyers, mortgage brokers, property tax advisors, or for non-Singapore properties.

## Lookup modes

| Mode                     | Flag                | Behaviour                                                                 |
| ------------------------ | ------------------- | ------------------------------------------------------------------------- |
| Name                     | `--name <str>`        | Case-insensitive substring match on salesperson name                       |
| Registration number      | `--registration-no`   | Exact match on CEA registration number (e.g. `R012345X`)                 |
| Name + postcode sector   | `--name + --postcode` | Above + filter to 2-digit postcode sector (first 2 digits of 6-digit)     |
| Name + track record      | `--name + --town`     | Above + count closed transactions per reg_no in town / flat type          |

`--name` and `--registration-no` are mutually exclusive. `--postcode`, `--town`, `--flat-type` are independent optional filters that can be combined.

## Workflow

1. **Parse CLI args.** `--name "Alice Tan"` (or `--registration-no R012345X`). Optional: `--postcode 570123`, `--town "BISHAN"`, `--flat-type "5-ROOM"`.
2. **Fetch CEA salesperson register.** `fetch_cea_salesperson(query)` returns the full salesperson list (~50k records, refreshed 3x daily).
3. **Match.** Name lookup: case-insensitive substring on `name` field. Registration number lookup: exact match on `registration_no`. The 1 lookup call returns up to N matches; the script does no further matching.
4. **Postcode filter (optional).** Geocode the postcode via OneMap → extract `lat`/`lon` → compute 2-digit sector from the first 2 digits of the postcode. Filter matches to those whose `registered_postcode` starts with the same 2 digits.
5. **Track record (optional).** Pull CEA transaction records via `fetch_cea_transaction_records(town, flat_type)`. For each matched reg_no, count closed transactions matching that reg_no. Attach `closed_in_town`, `closed_in_flat_type`, and `last_deal_date` to each match.
6. **Output JSON.** Always includes `query`, `matches: [{...}]`, `match_count`. Includes `location` block when `--postcode` is set, `track_record` block when `--town` is set.

## Output shape (canonical)

```json
{
  "query": "Alice Tan",
  "matches": [
    {
      "registration_no": "R012345X",
      "name": "Alice Tan",
      "status": "active",
      "agency": "ERA Realty Network Pte Ltd",
      "last_refreshed": "2026-06-22"
    }
  ],
  "match_count": 1
}
```

With `--postcode 570123`:

```json
{
  "query": "Alice Tan",
  "matches": [...],
  "match_count": 1,
  "location": {
    "postcode": "570123",
    "geocoded_address": "Bishan",
    "sector": "57"
  }
}
```

With `--town "BISHAN" --flat-type "5-ROOM"`:

```json
{
  "query": "Alice Tan",
  "matches": [
    {
      "registration_no": "R012345X",
      "name": "Alice Tan",
      "status": "active",
      "agency": "ERA Realty Network Pte Ltd",
      "last_refreshed": "2026-06-22",
      "track_record": {
        "closed_in_town": 23,
        "closed_in_flat_type": 15,
        "last_deal_date": "2025-12"
      }
    }
  ],
  "match_count": 1
}
```

Empty matches returns `match_count: 0` (not an error). Errors caught at top level: `{"error": "..."}` with exit code 0.

## Data sources

- **CEA Salesperson Information** (coll 54, `d_07c63be0f37e6e59c07a4ddc2fd87fcb`) — refreshed 3x daily. See `references/cea-salesperson.md`.
- **CEA Salespersons' Property Transaction Records (residential)** (coll 55, `d_ee7e46d3c57f7865790704632b0aef71`) — refreshed monthly. See `references/cea-transactions.md`.
- **OneMap geocoder** for postcode → lat/lon resolution. See canonical `docs/api/OneMap.md`.

Cross-references: canonical `docs/api/CEA.md` for the broader CEA catalog.

## Caching

All upstream calls go through `singapore_api.request_json`, which writes to `~/.hermes/cache/<namespace>/<sha1>.json`. Second invocation within the cache window is free.

Namespaces used:
- `datastore|d_<cea_salesperson_id>` for salesperson register
- `datastore|d_<cea_transactions_id>` for transaction records

## Hardening

- **Empty query rejected.** `--name ""` and `--registration-no ""` produce `{"error": "empty query"}` and exit 0.
- **Mutually exclusive lookup flags.** `--name` and `--registration-no` cannot be combined; argparse exits with an error.
- **No top-level network.** `singapore_api` is lazy; no calls at import time.
- **Postcode validation.** `--postcode` must be exactly 6 digits; geocoder is the source of truth for the sector.
- **Track-record empty when no transactions.** If the matched salesperson has no closed transactions in the town/flat-type, `track_record` is `null` (not an error).
- **No matches → `match_count: 0`.** Not an error. The script returns exit 0 with an empty `matches` list.

## Pitfalls

- **CEA register is updated 3x daily**, but new agents and resignations can lag by 1-2 days. A salesperson listed as `active` may have resigned the day before.
- **Postcode sector is approximate.** Singapore has 81 postal districts; the 2-digit sector of the salesperson's registered address may differ from where they actually operate.
- **Track-record counts closed transactions only.** Pending transactions and exclusive dealings are not counted. The count is the count of CEA-disclosed deals, not the salesperson's true volume.
- **The salesperson name match is substring, not exact.** "Tan" matches "Alice Tan", "Bob Tan", and "Charlie Tan Tan". Use `--registration-no` for precise lookup.
- **No deal date filtering.** `--town` + `--flat-type` count all CEA-reported transactions since the dataset's start date, not a date window.
- **Geocoder requires network.** If OneMap is unreachable, `--postcode` lookup fails with `{"error": "..."}` even if the salesperson register is cached.

## Tests

Smoke tests use stdlib `unittest` + `unittest.mock` to stub `fetch_cea_salesperson`, `fetch_cea_transaction_records`, and `geocode`:

```bash
python3 -m unittest discover -s skills/agent-match-skill/tests
```

The suite covers:
- Name hit (1 row, 1 match)
- Registration number hit (exact match on `R012345X`)
- No match (`match_count: 0`, not an error)
- Empty query rejected
- Postcode sector extraction
- Postcode hit / postcode miss
- Track-record with deals
- Track-record with no deals
- Module import + public surface
- No top-level network calls

## References

- `references/cea-salesperson.md` — coll 54 register schema and quirks
- `references/cea-transactions.md` — coll 55 transaction records schema and track-record logic
- `../docs/api/CEA.md` — canonical CEA catalog (the v2 collection listing)
- `../docs/api/OneMap.md` — geocoder reference for the `--postcode` path

## Install

```bash
npx skills add kangcodex/singapore-skills --skill agent-match-skill
```

The skill ships `scripts/singapore_api.py` as a per-skill copy (synced from the canonical at the repo root via `scripts/sync_singapore_api.py`). No runtime dependency on the parent repo.
