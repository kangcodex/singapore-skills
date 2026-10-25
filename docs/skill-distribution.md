# Skill shipping audit

The installable `skills/` tree holds runtime instructions, executable dependencies,
agent knowledge and reusable output assets. The entire `development/` directory is
local-only, untracked and ignored, including reusable tests, eval prompts and
synthetic inputs. Existing local files are retained. This is an explicit version-
control policy choice; the reusable verification assets are not classified as dead.
Fresh clones retain self-contained package checks, not the individual-skill corpus.

The 2026-10-25 audit against `556c072` reduced tracked skill-folder files from 147
to 129 and removed a net 781 Python/shell source lines across the repository.
That historical verification used the local corpus: 731 tests and 161 subtests;
all 13 skill manifests validated. It is not the published-only test count.

## All 13 skills

Every skill retains `SKILL.md`. Environment templates are kept where present.
References are agent knowledge even when Python never opens them; a missing Python
caller is not evidence that a reference is dead.

| Skill | Runtime code/data decision | Local-only development material |
|---|---|---|
| agent-match | Keep agent lookup, bundled API client and CEA guides | Tests moved |
| air-quality-advisor | Keep classification CLI, bundled client and health/NEA guides | Tests moved |
| cdc-voucher-locator | Keep locator, bundled distance helper/client and data/URL guides | Tests moved |
| dengue-risk-advisor | Keep risk CLI, client and risk/source guides | Tests moved; three unused test helpers removed |
| hawker-discover | Keep CLI/client/guides; co-install CDC because it invokes the sibling script | Tests moved, including CDC helper-parity checks |
| mrt-rerouter | Keep routing CLI, client and transport/weather guides | Tests moved |
| overseas-trip-planner | Keep trip CLI, embedded tables and four reference guides | Tests/eval prompts moved; bespoke grader untracked |
| property-advisor | Keep 27 reachable modules, 20 guides, five loaded JSON files and case template | Already separated in PR4; exporter now reuses common implementation |
| rental-yield-calculator | Keep calculator, client and URA guides; public compatibility exports retained | Tests moved |
| sg-fruit-price-tracker | Keep standalone scraper with inline dictionaries/parsers | Tests/prompts moved; duplicate grader untracked; useful offline CLI checks retained |
| sg-home-chef | Keep standalone helper and recipe/ingredient/tier/sourcing knowledge | Tests/prompts moved; grader and working design note untracked |
| smart-commuter | Keep parking/weather/traffic CLI, client and operating guides | Tests moved |
| weekend-planner | Keep planner, client and facility/weather/closure guides | Tests moved; unused test stub removed |

### Why the shared clients remain committed

The ten `scripts/singapore_api.py` copies are generated from one canonical source.
Direct GitHub/folder skill imports do not copy the repository root or run a build.
Deleting these copies, replacing them with root imports, or ignoring them would
leave installed skills without their dependency. Keep the copies and verify sync;
do not edit them by hand. Similarly, a tested compatibility export is not dead
solely because the main CLI does not call it.

## Confirmed retirements: preserve local files, remove Git tracking

| Former tracked path | Preserved local path |
|---|---|
| `skills/overseas-trip-planner-skill/evals/grade.py` | `development/overseas-trip-planner/evals/grade.py` |
| `skills/sg-fruit-price-tracker-skill/evals/grade.py` | `development/sg-fruit-price-tracker/evals/grade.py` |
| `skills/sg-home-chef-skill/evals/grade.py` | `development/sg-home-chef/evals/grade.py` |
| `scripts/verify_all_skills.sh` | Same path, ignored |
| `docs/design/sg-home-chef-skill.md` | Same path, ignored |

The verifier names a deleted skill and has no current caller. The graders duplicate
CLI/unit contracts; trip checks unconditionally passed prose/route expectations,
and fruit checks graded canned prose and sorted an already-sorted list. Unique
useful checks now live in tests: elderly lodging, emitted localization/metadata,
usable strategy content, offline retailer CLI results, pitaya aliases and failure
diagnostics. Test caches use temporary HOME directories. Behavioral eval prompts
remain locally and should grade actual native outputs, not script metadata flags.
The local `development/evaluations.md` notes are not distributed in Git.

The home-chef expectations now distinguish actual ingredient suitability from an
echoed dietary label, and dish-appropriate prata technique from a generic wok/
rempah strategy. This is an evaluation correction, not a claim that the existing
recipe scaffolder has passed independent dietary/recipe qualification.

## Clean exports

```bash
python3 scripts/package_skills.py --output-dir dist/all-skills
python3 scripts/package_skills.py --skill hawker-discover-skill --output-dir dist/hawker
```

The second command also exports CDC. Co-install these sibling directories. Each
archive has one named skill root and an MIT license; missing per-skill licenses
are materialized from the canonical license rather than committed repeatedly.
The property-specific command remains supported as a compatibility wrapper.

Exporters select tracked runtime paths, reject symlinked sources and preserve
existing exports. Local graders, outputs, caches, real `.env` files and untracked
casework are excluded. `.gitignore` alone is not a folder-importer package policy.

## Verification boundary

`make test-skills` runs published, self-contained distribution tests. The
distribution test exports every skill, examines each archive and imports its entry
point from the extracted package with no repository cwd, PYTHONPATH, site packages
or user credentials. The public property smoke check executes its bundled empty
case template. `make test-local` additionally runs the private local corpus,
including all 14 focused engines and richer case/advice workflows when that
workspace exists. It fails explicitly if the local workspace is absent.

Import success does not establish live-provider access, correct current data-source
schemas, advisory accuracy, recipe suitability or actual agent quality. Those need
their own behavioral/live-source checks; this cleanup preserves runtime interfaces.
