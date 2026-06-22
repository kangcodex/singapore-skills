# CEA Data Sources

This skill uses one CEA dataset (the salesperson directory) to power the
optional `--verify-salesperson` flag. The CEA Salespersons' Property
Transaction Records dataset (coll 55) is **not** used by this skill — it
is reserved for the future `agent-match-skill`.

For the full CEA catalog (2 collections), see the canonical
[`docs/api/CEA.md`](../../../docs/api/CEA.md).

## Datasets used by this skill

| Dataset                       | Collection | Frequency | Used by mode                  |
| ----------------------------- | ---------- | --------- | ----------------------------- |
| `CEA_SALESPERSON_DATASET_ID`  | 54         | 3x daily  | optional CEA verification     |

The fetcher function lives in the shared `singapore_api` client:

- `fetch_cea_salesperson(query)` — `d_07c63be0f37e6e59c07a4ddc2fd87fcb`
  - Empty / `None` / whitespace-only `query` → returns `[]` without
    touching the network
  - If `query` starts with `R` and is at least 3 characters long, it is
    treated as a registration number (case-insensitive exact match on
    the `registration_no` column)
  - Otherwise, the `query` is matched as a case-insensitive substring of
    the `name` column

## Data shapes

Typical columns in the salesperson dataset:

- `registration_no` — string, e.g. `R012345X`
- `name` — string
- `status` — `active` / `inactive` (live CEA status)
- `agency` — string (e.g. `ERA Realty Network`, `PropNex`, `OrangeTee`)

The `cea_verification` field in the v2 output is:

```json
{
  "registration_no": "R012345X",
  "name": "Alice Tan",
  "status": "active",
  "agency": "ERA Realty Network"
}
```

or `null` if `--verify-salesperson` was not passed, or if the query
matched no record. Failure to match is **not** an error — a warning is
logged to stderr but the JSON output still has the rest of the verdict.

## Quirks

- The dataset is refreshed **3 times per day**, so a fresh query can
  confirm registration within hours of any change.
- Registration numbers in Singapore follow the pattern `R` + 6 digits +
  1 letter. The skill does **not** validate the pattern; an exact match
  is attempted if the query starts with `R` and has ≥ 3 characters.
- Multiple salespersons can share the same name across agencies. The
  substring match on `name` will return all of them — callers should
  display the full `registration_no` so the user can pick the right
  person.
- The CEA dataset is large (~50 000 rows in 2026). The first
  uncached call to `fetch_cea_salesperson` can take 20–30 s. Subsequent
  calls in the same hour are served from the
  `datastore|d_<resource_id>` cache.

## Cross-references

- Canonical CEA catalog: [`docs/api/CEA.md`](../../../docs/api/CEA.md)
- Shared client: [`singapore_api.py`](../../../singapore_api.py) (look for
  `fetch_cea_salesperson` in the `── Property data layer (S08) ──` section)
- Fetcher is smoke-tested in
  [`tests/test_singapore_api.py`](../../../tests/test_singapore_api.py) —
  class `TestS08PropertyFetchers`, methods
  `test_fetch_cea_salesperson_empty_query_returns_empty`,
  `test_fetch_cea_salesperson_reg_no_exact_match`,
  `test_fetch_cea_salesperson_name_substring_match`
