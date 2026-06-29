# Output blueprint — the exact itinerary structure

The agent must emit every itinerary in **this exact order, with these exact section headers**. Do not improvise the layout. The user (and any downstream tool) expects to find these blocks at these positions.

---

## 1. Quick-glance logistical table

Always first. One row per day, including arrival and departure days.

| Day | Date | Base Area | Transport | Persona Anchor | Heavy Transit? |
|-----|------|-----------|-----------|----------------|----------------|
| 1   | 14 Nov | Kyoto (Gion) | KIX → JR Haruka | Arrival + Gion twilight | No |
| 2   | 15 Nov | Kyoto (Gion) | Walking + subway | Fushimi Inari + Nishiki Market | No |
| 3   | 16 Nov | Kyoto → Nara (day-trip) | JR Nara Line | Tōdai-ji + Nara Park deer | No |
| 4   | 17 Nov | Kyoto → Osaka | JR Special Rapid | Dōtonbori evening | No |
| 5   | 18 Nov | Osaka → KIX → SIN | JR Haruka + flight | Departure | Yes (Heavy) |

Rules:
- **Heavy Transit Day** cells use `Yes` or `Yes (Heavy)` — never leave ambiguous.
- **Base Area** is where the traveler sleeps that night, not the morning's location.
- **Persona Anchor** is a one-line theme that ties the day to the persona (e.g. "atmospheric evening" for couple, "kid park play" for family).

## 2. Day-by-day breakdown

For **each** day, emit three blocks — **Morning**, **Afternoon**, **Evening** — and a transit footer.

```markdown
## Day 1 — Thu 14 Nov — Arrival + Gion twilight
**Morning:**
- 09:30 KIX arrival, clear immigration, top up Welcome Suica.
- 10:30 JR Haruka to Kyoto Station (~75 min, reserved seat 6).
- 12:00 Drop bags at hotel (Gion, east side).

**Afternoon:**
- 13:30 Lunch at [name] — order the [specific hyper-local dish].
- 15:00 Walk Higashiyama lanes toward Kiyomizu-dera. Skip the main hall if queueing >20 min — view from the veranda is free.
- 17:00 Sunset check at Yasaka Shrine. The lantern row lights up exactly at dusk.

**Evening:**
- 18:30 Dinner at [name] in Pontocho alley — [reservation note].
- 20:30 Walk back to the hotel via Shirakawa lane. (Couple: stop at the river-bar at Shijo for a 20-min whiskey.)

*Transit blocks: ~95 min total. Sunset 17:00, cutoff 16:00 — outdoor done by 15:30.*
```

Rules:
- Every **time** stamp uses 24-hour local time. Always.
- Every food recommendation names a **specific, named venue** and a **specific dish**. No "explore local cuisine."
- Every **transit block** sums to a single integer in the footer. The LLM should mentally add the legs.
- The **daylight note** at the bottom is mandatory for every day that has any outdoor / driving leg.

## 3. Skip-the-Trap section

**Always** emit one of these per city in the route. Format:

```markdown
## Skip the Trap

### Kyoto
- ❌ **Kinkaku-ji at noon** — packed, sun-bleached, no atmosphere.
- ✅ **Hōnen-in at 7:30am** — moss gate, empty, golden-hour light. Then walk Philosopher's Path before the tour buses hit.

### Nara
- ❌ **Feeding the deer for the photo** — they're aggressive around the crackers.
- ✅ **Walking the sando approach from Kasuga Taisha** — quieter, the lanterns are better.

### Osaka
- ❌ **Takoyaki from the Glico-man corner** — chain-store batter, 30-min line.
- ✅ **Wanaka on Dōtonbori side-street** — small shop, octopus arrives whole, 8-min wait.
```

The point is to **teach the traveler** what locals avoid, and what to do instead. Never recommend a spot that appears on a generic "Top 10" list without explicit local-framing.

## 4. Geographic realism — heavy transit day flag

Plot the route on a mental map **before** writing. If Day 3 is east of Day 2's base, Day 4 should not bounce back west. If it does, that's a **Heavy Transit Day** — flag it explicitly:

```markdown
## Day 5 — Mon 18 Nov — Departure (Heavy Transit Day 🚌)
...
*Note: Heavy transit day — KIX from Osaka (~50 min) plus 13h flight to SIN. No sightseeing after 11:00.*
```

The flag is a **call to action** for the traveler to confirm they actually need the detour, and for the agent to justify it.

## 5. Etiquette & packing

End every itinerary with:

```markdown
## Etiquette & Packing

**Local etiquette**
- Bow vs. nod in Japan — bow is the safer default; handshakes are fine for business.
- Shoes off at temples, ryokans, and many traditional restaurants — look for the *tobi* (slippers) at the genkan.
- Tipping is not customary and can cause confusion; round up taxis to the nearest ¥100.

**Packing for Kyoto mid-November**
- Layers: 8-15°C daytime, 3-7°C at night. Pack a packable down jacket.
- Slip-on shoes — you'll be taking them off ~10x/day at temples.
- A small tote for convenience-store stops (the bag-tax is real, ~¥3 per plastic bag).
- Pocket Wi-Fi or eSIM — 4G is fine in cities, patchy in Arashiyama bamboo grove.

*Verify before you go: visa-free entry (Singapore passport, 90 days), JR Pass activation window, Pontocho dinner reservation for Day 1 evening.*
```

The **Verify** line is the agent's safety valve — anything that requires live verification (visas, transit cards, restaurant reservations) lives here, not in the body of the itinerary.

---

## Anti-patterns to avoid

- ❌ **Quote a flight price.** "Flights from $850" — never. State ranges only with "verify on the day."
- ❌ **Quote a hotel price or availability.** "Rooms at $200/night" — never. State neighborhoods and styles instead.
- ❌ **Recommend a chain hotel as the headline stay.** The point of this skill is to push the traveler to local, characterful, family-run options.
- ❌ **Pad the itinerary with tourist-trap filler.** If you can't find a local recommendation, leave the time-block empty and say "free time" — don't make up a Top-10 attraction.
- ❌ **Skip the daylight footer on a day with driving.** The footer is mandatory, not optional.
- ❌ **Skip the Skip-the-Trap section.** Even for tiny towns.
- ❌ **Use vague dish names.** "Local ramen" — never. "Shio ramen at Satou near Tsukiji outer market, counter-seating, order the kake-jiro" — yes.
- ❌ **End with a generic packing list.** "Bring layers and comfortable shoes" — useless. "Packable down jacket for 5°C Kyoto evenings, slip-ons for temple visits, small tote for the bag-tax" — useful.
