---
name: hawker-discover-skill
description: "Find hawker food that accepts CDC vouchers AND is open right now (not in quarterly cleaning). Extends cdc-voucher-locator-skill with NEA closure awareness. Use this skill whenever the user asks 'open hawker near me', 'hawker that takes CDC vouchers', 'cleaning not this week', or wants a hawker that is both voucher-eligible and currently open. Composes with cdc-voucher-locator-skill via subprocess (no copy-paste of the CDC lookup)."
---

# hawker-discover-skill

**Builds on** [`cdc-voucher-locator-skill`](../cdc-voucher-locator-skill/SKILL.md).
Calls the CDC script as a **subprocess** (no import coupling) and
intersects its output with NEA's hawker-centre closure list.

## When to use

Trigger phrases:
- "find hawker that accepts CDC voucher and is open"
- "hawker open now near me"
- "I want to use my CDC voucher, where can I eat that's not closed for cleaning?"
- "hawker + voucher + open"

## Quick start

```bash
python3 hawker-discover-skill/scripts/hawker_discover.py "Ang Mo Kio Hub" B 500
```

Modes: `A` (generic), `B` (food), `D` (budget meal). **Mode C is not
applicable to hawker centres** — the script returns
`{"error": "Mode C is not applicable to hawker centres"}` for that case.

## What it does

1. **Subprocess** invokes
   `../cdc-voucher-locator-skill/scripts/cdc_voucher_locator.py` with
   the same args. This is deliberate: each skill remains
   self-contained on `npx skills add --skill X` install — no
   `sys.path` hacks, no hard-coded import paths to a sibling skill.
2. Calls `singapore_api.fetch_hawker_closures()` (CKAN datastore,
   NEA quarterly cleaning schedule).
3. Matches each CDC merchant to its NEA hawker-centre by haversine
   distance (< 50 m). CDC gives per-merchant `LAT`/`LON`; NEA gives
   per-centre `lat`/`lon`. When they match, the skill attaches
   `open_now` + `next_closure` to the merchant.
4. Returns a single JSON document combining CDC's results with
   closure awareness.

## Output shape

```json
{
  "query": "Ang Mo Kio Hub",
  "postal": "569933",
  "location": "Ang Mo Kio Ave 3",
  "mode": "B",
  "radius_m": 500,
  "last_updated": "2026-06-21T08:00:00+08:00",
  "results": [
    {
      "name": "Ah Lim Chicken Rice",
      "address": "Blk 123 Ang Mo Kio Ave 3",
      "distance_m": 210,
      "category": "🍽 F&B / Dining",
      "open_now": true,
      "next_closure": {
        "start": "2026-09-01",
        "end": "2026-09-14",
        "reason": "Quarterly Cleaning"
      }
    }
  ]
}
```

`open_now` is `null` when the CDC merchant's coordinates don't fall
within 50 m of any NEA hawker-centre record (e.g. the merchant is at
a coffee shop that's not a hawker centre, or NEA's dataset is missing
that record). This is honest "unknown" — not silently open.

## Workflow

1. **Parse user query** → location name (geocoded by CDC).
2. **Subprocess CDC** with the same location + mode + radius.
3. **Fetch NEA closures** via `singapore_api.fetch_hawker_closures()`.
4. **Match** each CDC merchant to its NEA centre by haversine.
5. **Annotate** with `open_now` and `next_closure`.
6. **Filter for the user**: if the user said "I want to eat now",
   drop `open_now: false` (and surface `next_closure` for context).
   If the user asked "what's around", keep both and let them choose.

## Hardening

- **Mode C short-circuit**: returns the documented error before
  touching the network. No subprocess call, no API call.
- **Subprocess timeout**: 60 s. CDC's data files are cached locally
  so this is generous; if the CDN hangs, the skill fails fast.
- **Subprocess exit != 0**: surfaced as a structured error; the skill
  returns `error` + empty `results` rather than crashing.
- **Invalid JSON from CDC**: caught and reported. The CDC script
  uses `json.dumps(..., indent=2)` so the JSON is always valid
  *unless* CDC itself errors and writes to stdout — in that case the
  return code is non-zero and we surface that error first.
- **Hawker-centre not matched**: `open_now: null`, no crash.
- **No top-level network calls**: imports are stdlib + the
  per-skill `singapore_api`. The subprocess and the NEA call only
  fire from `assess()` / `main()`.

## Pitfalls

1. **Subprocess couples this skill to the CDC skill's CLI.** If
   CDC renames or moves its script, this skill breaks. The error
   message ("CDC lookup failed (exit N): ...") makes that obvious
   in production, but if you change CDC's argument convention,
   update `invoke_cdc()` here.
2. **The 50 m match radius is a heuristic.** A merchant on the
   boundary of a hawker centre (e.g. ground-floor coffeeshop that
   shares a building with the hawker centre) may not match. The
   skill surfaces `open_now: null` in that case — better than
   silently dropping or silently flagging.
3. **CDC's data can be stale.** `last_updated` is surfaced; the
   skill does not revalidate freshness. Caller can use it to warn
   the user ("data as of 2 days ago, centre may have reopened").
4. **NEA's closure list is "next closure", not "current closure".**
   The skill filters for "closed today" by date arithmetic. If
   `next_closure_end < today`, that centre is *open today* —
   `open_now: true`. If `next_closure_start <= today <=
   next_closure_end`, it's *closed today* — `open_now: false`.
5. **Parity test with CDC helpers.** This skill inlines `is_food`
   and `categorize` (pure string-classification logic, not API
   code). If CDC's `FOOD_KW` / `CAT_RULES` lists change,
   `TestHelperParityWithCdc` will catch the drift. Update both
   copies together.

## Caching

- **CDC data**: cached by CDC itself at
  `~/.hermes/cache/cdc-vouchers/`. The CDC script's `Last-Modified`
  check means the second invocation is sub-second.
- **NEA closures**: cached by `singapore_api` at
  `~/.hermes/cache/<sha1>.json` (1-day TTL by default). The
  `fetch_hawker_closures()` helper returns the cached envelope
  on the second call within 24 h.

## Testing

```bash
python3 -m unittest discover -s hawker-discover-skill/tests -v
```

25 tests across 6 classes:
- `TestPureHelpers` (7): `_haversine_m`, `is_food`, `categorize`
- `TestInvokeCdc` (4): subprocess call, JSON parse, exit code, bad JSON
- `TestAttachClosure` (5): open, closed, no-match, missing-coords, no-closure-record
- `TestAssess` (6): mode C error, mode A/B/D full reports, CDC error propagation, empty NEA
- `TestHelperParityWithCdc` (2): `is_food` and `categorize` agree on sample merchants
- `TestModuleImport` (1): public surface check

All network paths are mocked. The CDC subprocess is mocked via
`subprocess.run`; `singapore_api.fetch_hawker_closures` is mocked
via the test's `with patch(...)` block.

## See also

- [`references/nea-hawker-closures.md`](./references/nea-hawker-closures.md) — NEA dataset, closure pattern, sharing with S03a
- [`references/cdc-voucher-locator-integration.md`](./references/cdc-voucher-locator-integration.md) — subprocess pattern, mode C rationale, reused-functions table
- [Sibling: `weekend-planner-skill`](../weekend-planner-skill/SKILL.md) — also uses `fetch_hawker_closures` for the hawker pivot
- [Sibling: `cdc-voucher-locator-skill`](../cdc-voucher-locator-skill/SKILL.md) — the source skill invoked via subprocess
