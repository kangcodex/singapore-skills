# CDC Voucher Locator — Subprocess Integration

`hawker-discover-skill` does not import `cdc-voucher-locator-skill`.
It calls it as a **subprocess**. This document explains why, what
the integration looks like, and what the failure modes are.

## Why subprocess, not import

The two skills live in the same repo today, but the install path
is `npx skills add --skill <name>`. A user who installs only
`hawker-discover-skill` should not have to also install
`cdc-voucher-locator-skill` for the import to work.

If we used `importlib.util.spec_from_file_location(...)` to pull
`cdc_voucher_locator.py` from a sibling path, the skill would
break on standalone install.

Subprocess is the right answer because:

1. **Each skill is self-contained on install.** The per-skill
   `scripts/singapore_api.py` handles shared API code (data.gov.sg,
   LTA, NEA). Subprocess handles cross-skill composition.
2. **No `sys.path` hacking.** A common anti-pattern that breaks
   in frozen distributions and in npx-installed skills.
3. **CDC's existing CLI is already a black box.** CDC's
   `cdc_voucher_locator.py` is a runnable script. We use it as one.
4. **Testability.** The integration is mocked at the
   `subprocess.run` boundary — no import path to mock.

## How the call works

```python
# hawker_discover.py
CDC_SCRIPT = (
    SKILL_DIR.parent.parent
    / "cdc-voucher-locator-skill"
    / "scripts"
    / "cdc_voucher_locator.py"
)

def invoke_cdc(query, mode, radius):
    proc = subprocess.run(
        ["python3", str(CDC_SCRIPT), query, mode, str(radius)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if proc.returncode != 0:
        return {"error": "CDC lookup failed (exit %d): %s" % (proc.returncode, proc.stderr.strip())}
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        return {"error": "CDC returned invalid JSON: %s" % e}
```

The skill is installed next to `cdc-voucher-locator-skill` in the
parent directory of the skill (so the relative path
`../cdc-voucher-locator-skill/scripts/cdc_voucher_locator.py`
resolves). This is the only filesystem assumption.

## Why Mode C returns the documented error

CDC has a Mode C ("supermarkets only"). Hawkers have no
supermarkets — the result would be empty. Rather than
silently returning `[]`, the skill returns:

```json
{"error": "Mode C is not applicable to hawker centres"}
```

so the agent (and the user) gets an explicit signal that the
mode is wrong, not that there's no data.

## Reused functions

| function | reused in hawker-discover? | why |
|----------|----------------------------|-----|
| `geocode` | no | CDC runs it. We accept CDC's `lat`/`lon`/`postal`/`location` as-is. |
| `haversine_m` | **inlined** (as `_haversine_m`) | Pure logic. The match-to-centre algorithm needs it locally to avoid a second subprocess. |
| `is_food` | **inlined** | Pure string classification. Parity-tested against CDC's copy. |
| `categorize` | **inlined** | Pure string classification. Parity-tested against CDC's copy. |
| `clean_addr` | not needed | hawker-discover passes CDC's `address` through unchanged. |
| `lookup` | called via subprocess | The whole point — we don't re-implement it. |
| `fetch_data` | called via subprocess | CDC's own caching at `~/.hermes/cache/cdc-vouchers/`. |

Three pure helpers (`haversine_m`, `is_food`, `categorize`) are
**inlined** rather than duplicated, because they are pure logic
(not API code) and hawker-discover needs them inside the parent
process to do the NEA join.

A drift test (`TestHelperParityWithCdc`) loads CDC's script and
asserts the two implementations agree on a sample of merchant
names. If CDC's keyword lists change, this test fails loudly.

## Failure modes

| What goes wrong | What the skill reports |
|------------------|------------------------|
| CDC script file not found | `error: CDC lookup failed (exit N): [Errno 2] No such file or directory: '...'` |
| CDC script crashes (e.g. CDN down) | `error: CDC lookup failed (exit N): ...` with CDC's stderr |
| CDC script returns invalid JSON | `error: CDC returned invalid JSON: <decode error>` |
| CDC subprocess hangs | timeout=60s, then `TimeoutExpired` propagates as an unhandled exception (Python 3.12+ raises; older raises `subprocess.TimeoutExpired` — the skill does not catch it explicitly because in practice CDC's local cache hit is sub-second) |
| NEA `fetch_hawker_closures()` returns empty `result.records` | `open_now: null` for every merchant; no error, no crash |

## What if you want to deprecate the subprocess

If `npx skills add` ever supports declaring peer dependencies, we
could switch to a direct import. Until then, subprocess is the
right cost. The contract is small (one CLI signature, one JSON
output shape) and the integration is well-isolated in
`invoke_cdc()`.

## See also

- [`../SKILL.md`](../SKILL.md) — workflow, mode C rationale, hardening
- [`./nea-hawker-closures.md`](./nea-hawker-closures.md) — NEA dataset, sharing note with S03a
- [`../../cdc-voucher-locator-skill/SKILL.md`](../../cdc-voucher-locator-skill/SKILL.md) — the source skill
