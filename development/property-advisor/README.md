# Property advisor development

This directory is repository tooling, not an installed skill. The importable
runtime is `skills/property-advisor-skill/`; keep its test/eval runs and synthetic
demo inputs here so folder-based importers do not distribute them.

From the repository root:

```bash
python3 -m unittest discover -s development/property-advisor/tests
python3 scripts/package_property_advisor.py
```

`fixtures/assessments/` covers all fourteen focused assessment kinds;
`fixtures/cases/` exercises old and bound schema3 records;
`fixtures/legacy-scenarios/` covers the offline profile/plan/compare CLI.
These are synthetic examples, not real properties or financial approvals.

Keep these definitions/fixtures/tests in Git. Generated eval outputs, transcripts,
grades, review HTML and local coverage reports belong in ignored `evals/runs/` or
repository `reports/`. Do not place personal source/case files in the skill folder.

The package command exports only tracked runtime files into ignored `dist/` and
creates a `.skill` ZIP. It does not copy local ignored casework or caches. Tests
exercise the export in isolation; `.gitignore` is not an installer exclusion policy.
