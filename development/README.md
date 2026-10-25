# Skill development

Installed skills live under `skills/` and contain runtime instructions, code,
references and reusable output assets. Tests, eval prompts and synthetic fixtures
live here, outside folders copied by skill importers.

From the repository root:

```bash
make test-skills
python3 scripts/package_skills.py --output-dir dist/all-skills
python3 -m unittest discover -s development/sg-home-chef/tests
```

Keep regression tests and fixed eval prompts in Git. Use native skill-creator
evaluation of actual agent outputs for advisory/recipe/itinerary quality; a
deterministic CLI check is not a with-skill versus baseline benchmark. See
[evaluation guidance](evaluations.md). Generated runs, grades and reports are
ignored. Retired bespoke `grade.py` files may remain locally but are not supported
commands or repository dependencies.
