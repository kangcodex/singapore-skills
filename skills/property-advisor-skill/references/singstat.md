# Supply and vacancy context

The legacy client attempts SINGSTAT pipeline/vacancy via CKAN and may return empty
rows on fetch/parse errors. Access and schemas must be verified before relying on
those responses. Empty is unavailable, not zero supply or balanced conditions.

Use dated, definition-compatible observations at the relevant geography. Select
the actual latest quarter, not a historical maximum or sum of stock across time.
Avoid combining totals/subtotals and establish overlap before adding pipeline and
unsold. Four rows are not necessarily four calendar quarters of demand. Vacancy
requires actual vacant/stock definitions; number of rows/series is not a rate.

National context cannot mechanically classify a local submarket. Record timing,
geography, source terms and limitations and keep unsupported signals unavailable.
Legacy outputs retain latest raw context only; the former supply-ratio heuristic
and its balanced default are retired. See [prices-and-costs.md](prices-and-costs.md).
