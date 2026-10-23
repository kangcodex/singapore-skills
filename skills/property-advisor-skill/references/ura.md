# URA source semantics

Use the current entry points in [research-and-evidence.md](research-and-evidence.md).
The public transaction search exposes separate non-strata landed, strata landed,
flat/condo and EC types; its form describes 60-month coverage and incomplete caveats.
Verify actual query/export access and terms before claiming retrieval/completeness.

The historical configured whole-Singapore dataset
`d_7c69c943d5f0d89d6a9a773d2b51f337` publishes `quarter`, `type_of_sale`,
`sale_status`, `units`: transaction VOLUME, not `median_psf`.
EC dataset `d_19c79027c2e6be3c39d637151bd2188d` likewise publishes counts, not prices.
The non-landed rental dataset `d_149ac00a2734bb0a03867bbe2ec0e7b0` publishes project
quarter summaries with `median` and percentile/contract columns, not the legacy
`median_rent_psf_pm` field. Coverage excludes smaller projects/thin quarters under
the page's stated thresholds; absence is not no demand.

These page/schema observations were checked 23 October 2026; they do not prove
live download integration or current unit inventory. Check measurement definitions,
actual schemas and source dates each time. National/regional summaries are context,
not matched exact-home values. Do not rename volume counts into price fields.

Master Plan land use does not prove an amenity is future, when it opens or the
price premium it deserves. Source geometry/CRS must match the consumer. A town
centroid is not walking access, school distance or specific unit coordinates.
Use current planning decisions/controls and disclose uninspected map layers.
