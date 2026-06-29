# Sunset lookup — bundled + LLM-extension guidance

The script `trip_concierge.py` ships with a **bundled sunset table** for ~70 popular Singapore-traveler destinations. If a destination isn't in the table, the script returns `sunset_local: "unknown"` and the agent must **web-search** the exact local sunset for the travel dates — never hallucinate a time.

## How to use the bundled table

The script accepts month input in **any** of these forms:

- `YYYY-MM` → `2026-11`
- `YYYY/MM` → `2026/11`
- `MM` (1-12) → `11`
- Month name → `November 2026`, `Nov`, `november`

It resolves the destination via the alias map in `trip_concierge.py:_ALIASES` (covers `東京`→`tokyo`, `Bali`→`bali`, `KL`→`kuala lumpur`, etc.).

The cutoff it returns is `sunset - 60 minutes`, in local 24h time. This is the hard stop for outdoor / highway driving and remote trail hiking.

## When the destination is missing

If the user says **"Bologna"** and `lookup_sunset("Bologna", 11)` returns `unknown`:

1. Run a web search for *"Bologna sunset November 2026"* or use a reliable API like `api.sunrise-sunset.org`.
2. Use the **actual** sunset time. Do not approximate.
3. Compute the cutoff as `sunset - 60 min`.

The agent's job is to back-fill the missing sunset. The script's job is to **flag** the gap loudly so the agent can't accidentally skip it.

## Why this table exists (the daylight-safety rationale)

Travelling in winter Europe or Japan in November, sunset is around **16:30-17:00** local. By 17:30 it's pitch dark. If a self-drive itinerary puts a traveler on unfamiliar rural roads in Tuscany or Hokkaido at 17:15, they're navigating by headlights in a country with different road rules. That is the single biggest source of overseas driving incidents from Singapore-origin travelers.

**The 60-minute buffer is non-negotiable.** By sunset-60, all driving should be done, parked, and the traveler should be in a restaurant, hotel, or well-lit town square. If the route can't fit in the daylight window, it's a **Heavy Transit Day** and the agent must surface the conflict in the itinerary, not silently violate the rule.

## Seasonal patterns the agent should internalize

| Region | Worst month (earliest sunset) | Sunset window | Notes |
|--------|-------------------------------|---------------|-------|
| Northern Europe (UK, DE, NL, NO, SE) | December | 14:30 – 16:00 | Drives cap at ~13:00-14:00 |
| Japan (Hokkaido) | December | 16:05 | Even Tokyo drops to 16:30 in Dec |
| Mediterranean (IT, ES, GR) | December | 16:40 – 17:15 | Better than N. Europe but still short |
| North America NE (NYC, Toronto) | December | 16:30 – 16:40 | Long drives need to start by 13:00 |
| SE Asia (Bangkok, KL, Singapore) | Year-round stable | 18:30 – 19:30 | Daylight is reliable |
| Australia / NZ (Sydney, Auckland) | June (their winter) | 16:50 – 17:10 | Reverse of N. hemisphere |
| High latitude (Reykjavik) | December | 15:30 — only 4-5 hrs of daylight | Almost no road-tripping feasible |

**Tropical / equatorial destinations** (Bali, Bangkok, Singapore, Manila) have stable 18:00-19:30 sunsets year-round. The daylight constraint rarely bites there — but heavy tropical rain (Nov-Mar in Bali, May-Oct in Bangkok) replaces it as the planning constraint.
