# Policy sources (agent mode)

Every policy figure used by `--mode agent` lives in [`policy-tables.json`](policy-tables.json). Each
item carries `as_of` (the date it was checked), `source_url` (the official page or document) and
`status`:

- `verified`: read from the official page or document named in `source_url` on `as_of`.
- `unverified`: could not be confirmed there; `unverified_reason` says why. The value is a
  placeholder to confirm with the named authority, not a fact. The calculators still use it so a run
  completes, and list it under `unverified_assumptions` in the output and the summary.

Singapore rules change. To update: edit the value, set `as_of` to the date you re-checked the
source, and (if you could not read the official page) leave or set `status: "unverified"` with a
reason. Repository tests check that every item is dated, sourced and, if unverified,
explained.

## Items

| Item | What | Authority | as_of | Status | Source |
| --- | --- | --- | --- | --- | --- |
| `bsd` | Buyer's Stamp Duty (residential) | IRAS | 2026-10-19 | verified | https://www.iras.gov.sg/taxes/stamp-duty/for-property/buying-or-acquiring-property/buyer's-stamp-duty-(bsd) |
| `absd` | Additional Buyer's Stamp Duty (residential) | IRAS | 2026-10-19 | verified | https://www.iras.gov.sg/taxes/stamp-duty/for-property/buying-or-acquiring-property/additional-buyer's-stamp-duty-(absd) |
| `ssd` | Seller's Stamp Duty (residential), purchases on or after 4 Jul 2025 | IRAS | 2026-10-19 | verified | https://www.iras.gov.sg/taxes/stamp-duty/for-property/selling-or-disposing-property/seller's-stamp-duty-(ssd)-for-residential-property |
| `property_tax_owner_occupier` | Property tax, owner-occupied residential, on Annual Value | IRAS | 2026-10-19 | verified | https://www.iras.gov.sg/taxes/property-tax/property-owners/property-tax-rates |
| `ltv_bank` | Loan-to-value limits for housing loans from financial institutions (individuals) | MAS | 2026-10-19 | verified | https://www.mas.gov.sg/regulation/explainers/new-housing-loans/loan-tenure-and-loan-to-value-limits |
| `tdsr` | Total Debt Servicing Ratio | MAS | 2026-10-19 | verified | https://www.mas.gov.sg/regulation/explainers/new-housing-loans/msr-and-tdsr-rules |
| `msr` | Mortgage Servicing Ratio (HDB flats, and ECs within the minimum occupation period) | MAS | 2026-10-19 | verified | https://www.mas.gov.sg/regulation/explainers/new-housing-loans/msr-and-tdsr-rules |
| `stress_rate` | Medium-term interest rate floor for TDSR/MSR on residential loans from financial institutions | MAS | 2026-10-19 | verified | https://www.mas.gov.sg/news/media-releases/2022/measures-to-promote-sustainable-conditions-in-the-property-market-by-ensuring-prudent-borrowing-and-moderating-demand |
| `hdb_loan` | HDB concessionary loan | HDB | 2026-10-19 | unverified | https://www.hdb.gov.sg/managing-my-home/finances/loan-matters/interest-rate |
| `ehg` | Enhanced CPF Housing Grant, first-timer families (credited to CPF OA) | HDB | 2026-10-19 | verified | https://www.hdb.gov.sg/-/media/buying-a-flat/flat-grant-and-loan-eligibility/couples-and-families/enhanced-cpf-housing-grant/EHG-amount-Families.pdf |
| `income_ceilings` | HDB / EC household income ceilings for citizen families | HDB | 2026-10-19 | verified | https://www.hdb.gov.sg/-/media/hdb-pulse/news/2026/increase-in-income-ceilings-and-greater-support-for-families-with-children/Annex-A.pdf |
| `family_grant_resale` | CPF Housing Grant (Family Grant), resale, first-timer families | HDB | 2026-10-19 | unverified | https://www.hdb.gov.sg/buying-a-flat/flat-grant-and-loan-eligibility/couples-and-families/cpf-housing-grants |
| `proximity_housing_grant` | Proximity Housing Grant, resale (live with / near parents or child) | HDB | 2026-10-19 | unverified | https://www.hdb.gov.sg/buying-a-flat/flat-grant-and-loan-eligibility/couples-and-families/proximity-housing-grant |
| `hdb_resale_otp` | HDB resale Option to Purchase terms | HDB | 2026-10-19 | verified | https://www.hdb.gov.sg/-/media/managing-my-home/selling-a-flat/process-for-selling-a-flat/option-to-purchase/OTP-Important-Notes.pdf |
| `private_resale_otp` | Private resale option fee and exercise window (market practice) | none (negotiated) | 2026-10-19 | unverified | https://www.cea.gov.sg/ |
| `new_launch_progressive` | Progressive payment schedule, uncompleted private residential (normal scheme) | MND (Housing Developers Rules) | 2026-10-19 | unverified | https://www.mnd.gov.sg/ |
| `cpf_usage` | CPF Ordinary Account usage for housing | CPF Board | 2026-10-19 | verified | https://www.cpf.gov.sg/member/infohub/educational-resources/how-much-cpf-savings-you-can-use-for-your-home-purchase |
| `cpf_accrued_interest` | CPF accrued interest to refund on sale | CPF Board | 2026-10-19 | unverified | https://www.cpf.gov.sg/member/home-ownership/using-your-cpf-to-buy-a-home/cpf-refund-when-selling-or-transferring-property |
| `hdb_mop` | HDB minimum occupation period | HDB | 2026-10-19 | unverified | https://www.hdb.gov.sg/cs/infoweb/residential/buying-a-flat/conditions-after-buying |
| `ec_mop` | Executive Condominium minimum occupation period | HDB | 2026-10-19 | unverified | https://www.mas.gov.sg/regulation/explainers/new-housing-loans/msr-and-tdsr-rules |
| `legal_valuation_fees` | Conveyancing legal fees, valuation fee, and miscellaneous (resale and new launch) | none (market quotes) | 2026-10-19 | unverified | https://www.cpf.gov.sg/member/home-ownership/home-buying-guide-for-members-below-55 |

## Why items are unverified (2026-10-19 review)

- `hdb_loan`: The HDB interest-rate and loan pages returned no figures when fetched. Rate (pegged 0.1pp above the CPF OA rate, 2.6% p.a. in Apr-Jun 2025) is from an HDB press-release listing; the current-quarter rate was not confirmed. LTV conflicts: the Sep 2022 joint MAS/MND/HDB release lowered it from 85% to 80%, while a search summary of HDB's FY2024/25 annual report says it was lowered again to 75%; the conservative 75% is used. Maximum tenure 25 years is unconfirmed (MAS caps HDB flat loans at 30).
- `family_grant_resale`: HDB page body could not be read; amounts are from a search excerpt of an older HDB page and may be outdated.
- `proximity_housing_grant`: HDB page body could not be read; amounts are from a search excerpt.
- `private_resale_otp`: Private resale option terms are negotiated, not regulated; 1% option fee and 14-day exercise are market-practice placeholders.
- `new_launch_progressive`: Statute text not retrieved; stages come from several secondary sources that agree. Booking fee 5% must be cash; later stages may use CPF.
- `cpf_accrued_interest`: The page states principal plus accrued interest is refunded but not the rate; 2.5% p.a. compounded (the CPF OA floor rate) is a placeholder.
- `hdb_mop`: Value comes from a search summary of HDB pages; page body not read. Longer MOPs exist for Prime Location (10y) and Fresh Start (20y) flats.
- `ec_mop`: Source_url is the MAS page that mentions the EC minimum occupation period; the length itself was not fetched from HDB; 5 years is the long-standing rule. EC becomes private after 10 years.
- `legal_valuation_fees`: Fees are quoted by lawyers and banks, not set by an authority. Figures are placeholders; get written quotes.

## Notes on verified items

- Stamp duties (BSD, ABSD, SSD) and property tax were read from the IRAS pages. SSD shown is for
  purchases on or after 4 Jul 2025 (up to 4 years' holding). ABSD for joint buyers with different
  profiles is applied at the highest rate (conservative; unverified).
- LTV, tenure caps, TDSR (55%), MSR (30%) and the 4% stress-test floor were read from MAS pages.
  The HDB loan assessment floor of 3% is from the MAS/MND/HDB 2022 measures release.
- HDB income ceilings were read from HDB's Annex A (22 Aug 2026 announcement). The announcement
  raises the resale-with-grant and HDB-loan ceilings to $16,000; the start date for those was
  not stated in the extracted text. EHG amounts were read from HDB's EHG table PDF; the EHG income
  ceiling ($9,000) is the table's last band.
- HDB resale OTP terms (option fee up to $1,000, deposit up to $5,000, 21-day option period) were read
  from HDB's "Important Notes on Option to Purchase".
- Virgin Active prices (weekly) were read from its official membership page on 2026-10-19.
