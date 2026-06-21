# NEA Hawker Cleaning Schedule (`fetch_hawker_closures`)

`hawker-discover-skill` uses this dataset to attach `open_now` +
`next_closure` to each CDC merchant. It shares the helper with
`weekend-planner-skill` (S03a).

**The full data-format, request shape, real response sample, and
pitfalls live in
[`weekend-planner-skill/references/nea-hawker-closures.md`](../../weekend-planner-skill/references/nea-hawker-closures.md).**

This document only covers what's specific to **hawker-discover**.

## How hawker-discover uses it

The CDC data gives per-merchant `LAT`/`LON` (e.g. a specific chicken
rice stall inside a hawker centre). NEA's data gives per-centre
`lat`/`lon` (the building). To attach closure info, the skill matches
each CDC merchant to the **nearest** NEA centre within
`HAWKER_MATCH_RADIUS_M = 50 m`.

| CDC merchant coords | NEA centre coords | match? | result |
|---------------------|-------------------|--------|--------|
| inside a hawker centre | the same hawker centre | yes (< 50 m) | attach `open_now` + `next_closure` |
| inside a hawker centre | a different centre 500 m away | no (> 50 m) | `open_now: null` |
| inside a coffeeshop (not a hawker centre) | n/a (no nearby centre) | no | `open_now: null` |

## Why 50 m, not 1 km

A 1 km radius would over-match: a merchant at Ang Mo Kio Ave 3 would
attach to a different Ang Mo Kio hawker centre ~600 m away. 50 m
matches the typical "stall is inside the centre" geometry.

## What "open_now: null" means to the user

When a CDC merchant doesn't match an NEA hawker centre, the skill
returns `open_now: null`. This is **honest unknown**, not "open" or
"closed". The agent should phrase it as:

> "I don't know whether this stall is in a cleaning-window
> right now — NEA's dataset doesn't list its building."

…rather than silently reporting the stall as open.

## What the skill does NOT do

- **No Singapore-wide pivot.** If a hawker centre is closed, the
  skill does **not** recommend a different centre in a different
  neighbourhood. That's `weekend-planner-skill`'s job. The CDC data
  is already filtered to the user's search radius, so the skill
  stays in scope.
- **No "open in 3 days" prediction.** The skill answers
  `open_now` (true/false/unknown today) and surfaces the next
  closure window. It does not extrapolate future windows.

## Sharing with S03a

`weekend-planner-skill` uses the **same** `fetch_hawker_closures()`
helper. Both skills filter the result for "closed now" by
identical date arithmetic. There is no second source of truth.

## See also

- `weekend-planner-skill/references/nea-hawker-closures.md` — full
  data-format, request shape, real response sample, and pitfalls.
