# Style / Pace / Accommodation / Rhythm playbooks

The four "what kind of trip" dimensions. Each is independent — the LLM composes them. Companion is in [`persona-matrix.md`](persona-matrix.md).

---

## 🏛 Style — what the trip is about

The five styles are **mostly orthogonal to Companion / Pace / Accommodation / Rhythm** — a `family + nature` trip and a `couple + nature` trip both want parks, but the *framing* is different (kid-friendly trails vs. romantic scenic drives).

### Cultural

**Mental model:** Deep, slow immersion in the local way of life. The traveler would rather have one tea ceremony with a 6th-generation master than three temple selfies.

- **Prioritize:** Temples, shrines, traditional craft workshops, tea ceremony, calligraphy, local festivals, language classes, neighborhood markets, family-run restaurants.
- **Skip:** Generic "Top 10" landmark lists. Branded chain experiences. Tour-bus stops under 30 min.
- **Anchor density:** 1-2 cultural anchors/day max (deep, not wide).
- **Dining:** Family-run or neighborhood institution. Order the hyper-local specialty — not the version the menu has in English.
- **Pacing notes:** Pairs well with `relaxed` or `moderate`. `ambitious + cultural` is contradictory — depth requires unhurried time.
- **Companion notes:** Powerful for `couple` (shared meaning), `solo` (deep immersion), `elderly` (slow tempo). Can be done by `family` if kids are 8+ and the parent is willing to translate.

### Classic

**Mental model:** The famous sights of the destination, done at the right time of day. The traveler is a first-timer or a bucket-lister.

- **Prioritize:** The famous landmarks of the destination, done at the right time of day (sunrise, golden hour, after dark).
- **Skip:** Mid-day at the headline attraction — wait for golden hour or do sunrise to skip crowds.
- **Anchor density:** 2 anchors/day is fine. Add a third only if it's a quieter indoor pivot.
- **Dining:** Mix — one signature / tourist-friendly spot, two local finds.
- **Pacing notes:** Fits all three paces. The `ambitious` version of classic is "do all 5 famous sights in 2 days."
- **Companion notes:** Works for every companion type. The default style for first-timers.

### Nature

**Mental model:** The trip is about the outdoors. The traveler wants to come home with tired feet and a camera roll of landscapes.

- **Prioritize:** Parks, trails, scenic drives, alpine lakes, coastline. Wildlife (ethical, distance-based) where it exists.
- **Skip:** Urban-only itineraries. Multi-hour indoor museums. Late drives to remote trailheads.
- **Anchor density:** 1-2 nature anchors/day. The third block is rest, picnic, or a short hike.
- **Dining:** Local farm-to-table, picnic supplies from local market, mountain hut food.
- **Pacing notes:** Fits `ambitious` (multi-day treks) and `relaxed` (one slow morning walk per day). `moderate` is the "do a trail in the morning, town in the afternoon" default.
- **Companion notes:** Excellent for `elderly` (accessible scenic drives, short paved trails) and `friends` (group hikes). Trickier for `family` with very young kids.

### Cityscape

**Mental model:** The trip is a city. Urban architecture, food, art, shopping, transport-as-attraction. The traveler doesn't need to leave the city limits to have a full trip.

- **Prioritize:** Architecture walks, neighborhood food crawls, contemporary art, shopping, transport-as-attraction (tram, ferry, metro art).
- **Skip:** Single-city day trips that eat the daylight. Beating the same neighborhood three times.
- **Anchor density:** 2-3 anchors/day, all within the city. Use transit time as observation time.
- **Dining:** One signature meal per trip. Hawker / market crawls. Rooftop / view-bar evenings.
- **Pacing notes:** Pairs well with `ambitious` (cover 4 neighborhoods/day) and `moderate`. Less natural for `relaxed` — a `relaxed + cityscape` trip is "stay in one neighborhood, repeat 2 restaurants."
- **Companion notes:** Best for `couple`, `friends`, `solo`. Can work for `family` if the city has parks + kid-friendly museums. `elderly + cityscape` means short walks, lots of taxis, sit-down meals.

### Historical

**Mental model:** The traveler wants to understand the past. They read the plaques. They hire the local guide.

- **Prioritize:** Ruins, museums, ancient sites, war memorials, old quarters. Pre-book guided tours for context.
- **Skip:** Anything in the "ancient but newly built" category (verify provenance). Surface-level photo stops.
- **Anchor density:** 1-2 deep-dive anchors/day, with a guide where possible.
- **Dining:** Period-appropriate / regional-historical dishes, not international chains.
- **Pacing notes:** Almost always `moderate` or `relaxed`. `ambitious + historical` is the "ruin-bagging" trip — possible, exhausting.
- **Companion notes:** Best for `couple`, `solo`, `elderly` (lifetime interest in history). Not for `friends` unless they specifically want it.

---

## ⏱ Pace — how dense

The pace is **fixed for the whole trip** — don't oscillate between ambitious Monday and relaxed Tuesday without a reason (e.g. arrival day is relaxed, then ambitious Tuesday onward).

### Ambitious — full days

- **Anchors per day:** 2-3
- **Activity hours per day:** 8-10h
- **Rest blocks:** One short rest block (30-60 min) at the hotel mid-afternoon. No full day off.
- **Transit willingness:** Willing to spend 3-4h/day in transit. Heavy Transit Days OK if the destination is worth it.
- **Suits:** `friends`, `solo` on a bucket-list trip, `couple` on an anniversary
- **Contradicts:** `family` (kids cap at 5h), `elderly` (energy limits)
- **Best climates:** Shoulder season, mild weather
- **Reward:** Maximum coverage, "I did it all" feeling
- **Risk:** Burnout by Day 4, no time to absorb the destination

### Moderate — balanced

- **Anchors per day:** 2
- **Activity hours per day:** 6-8h
- **Rest blocks:** Mid-day break (1-2h) plus early-evening down time.
- **Transit willingness:** Max 2-3h/day in transit. Heavy Transit Days discouraged.
- **Suits:** Almost every Companion / Style combination
- **Default.** When the user doesn't specify, use this.
- **Reward:** Sustainable energy across the whole trip
- **Risk:** None — this is the safe default

### Relaxed — leisurely

- **Anchors per day:** 1
- **Activity hours per day:** 4-6h
- **Rest blocks:** Long mid-day break (2-3h). One full unscheduled day per week.
- **Transit willingness:** Max 90 min/day. Heavy Transit Days are a no.
- **Suits:** `elderly`, `family` with young kids, recovery-from-jetlag trips, beach holidays
- **Contradicts:** `ambitious` (impossible by definition)
- **Reward:** Deep absorption, real rest, return home not exhausted
- **Risk:** "We could have done more" regret if the user is secretly ambitious

---

## 🛏 Accommodation — where they sleep

The accommodation tier is **fixed for the whole trip**. The script tells the LLM the tier; the LLM recommends specific properties.

### Comfort (3-4*)

- **Hotel class:** Clean, central 3-4* hotel or well-reviewed guesthouse. No frills required.
- **Amenities priority:** central location, clean room, reliable wifi, lift
- **Room requirements:** Private bathroom. Air-con or heating (depends on climate). Blackout curtains.
- **Skip:** Resort fees, club-lounge access, concierge.
- **Suits:** `backpacker` days are over, `solo` on a longer trip, `friends` splitting a multi-room
- **What "comfort" is NOT:** Not 2* hostels, not shared bathrooms, not chain motels off the highway.

### Premium (4-5* boutique / design)

- **Hotel class:** 4-5* boutique or design hotel. Concierge service, on-site restaurant, character.
- **Amenities priority:** characterful property, central location, good bed, on-site breakfast
- **Room requirements:** King or twin. Workspace. Bath. Mini-bar or nearby 24h store.
- **Skip:** Generic international chain hotels with no local character (the Westin-no-matter-where pattern).
- **Suits:** Most Singapore-origin travelers on a normal overseas trip. The default tier.
- **What "premium" is NOT:** Not a 5* chain that could be anywhere in the world.

### Luxury (5* / suite / villa / signature)

- **Hotel class:** 5* hotel, suite-only, or villa / private stay. **One signature property per trip.**
- **Amenities priority:** private butler / concierge, spa or signature wellness, in-room dining, view
- **Room requirements:** Suite or villa. Walk-in wardrobe. Soaking tub. Premium linens.
- **Skip:** Cookie-cutter 5* chain hotels with no signature experience.
- **Suits:** Honeymoons, anniversaries, milestone trips, "we only do this once in a decade" trips
- **What "luxury" is NOT:** Not paying for an executive lounge at a 4*. Not a "luxury resort" with 2000 rooms.

---

## 🌅 Day Rhythm — when they're active

The rhythm is **fixed for the whole trip**. Switching mid-trip is exhausting.

### Early starts

- **Wake:** 06:30-07:30
- **Out by:** 08:30
- **Sights:** 09:00-12:00 (golden hour, no crowds)
- **Mid-day rest:** 12:00-15:00 (siesta / pool / nap)
- **Sights:** 15:00-17:30
- **Dinner:** 18:00-19:30
- **In by:** 21:00-22:00
- **Best for:** Sunrise sights (Fushimi Inari, Angkor Wat sunrise, Taj Mahal at dawn), summer heat (escape by 12:00), crowded tourist cities, photographers, peak-season trips where mid-day is unbearable
- **Suits:** `solo` (photographers), `couple` (sunrise romantics), `family` with early-rising kids
- **Contradicts:** `friends` (group will sleep in)
- **Climate:** All climates, but especially hot summers and cold winters

### Late nights

- **Wake:** 09:30-10:30
- **Out by:** 11:00
- **Sights:** 11:00-17:00 (with 16:00 coffee / snack break)
- **Aperitivo:** 18:00-20:00
- **Dinner:** 20:00-22:00
- **Night activities:** 22:00-24:00+ (night market, izakaya, jazz bar, sky bar)
- **Best for:** Hot climates, night markets, urban / city trips, Mediterranean dinner culture, Bali / Bangkok / Mediterranean Europe
- **Suits:** `couple` (Mediterranean dinner), `friends` (nightlife), `solo` (urban exploration)
- **Contradicts:** `family` with kids, `elderly`
- **Climate:** Tropical / Mediterranean / summer Europe

---

## How the 4 dimensions compose (composite contradictions)

These are the **second-order contradictions** beyond the ones the script auto-flags. Apply judgement, don't silently override.

| Combination | Problem | Safe call |
|-------------|---------|-----------|
| `cultural` + `ambitious` | Depth requires unhurried time | Drop to `moderate` |
| `nature` + `late-nights` | Most nature is best at dawn | Force `early-starts` |
| `cityscape` + `relaxed` | The whole point is to cover ground | One neighborhood, repeat 2 restaurants |
| `historical` + `late-nights` | Ruins close at dusk | Force `early-starts` |
| `luxury` + `ambitious` + `late-nights` | Marathon in a 5* — verify intent | Ask the user |
| `comfort` + `luxury` in style — n/a (orthogonal) | — | — |
| `nature` + `cityscape` | Mix of park and city is fine; alternate days | Default OK |
| `cultural` + `nature` | Both depth-oriented — pick a primary | Default OK |

The script only auto-flags the **Companion × Pace × Rhythm** contradictions. The **Style × Pace × Rhythm** composite contradictions are the LLM's responsibility — apply them in Phase 4 of the SKILL.md.
