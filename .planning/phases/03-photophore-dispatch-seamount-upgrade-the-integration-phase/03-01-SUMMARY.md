---
phase: 3
phase_id: "03-photophore-dispatch-seamount-upgrade-the-integration-phase"
plan: 1
plan_id: "03-01"
subsystem: photophore.dispatch
tags:
  - dispatch
  - photophore
  - async
  - ast-lint
  - at-a1
  - policy-03
requirements-completed:
  - DISP-01
  - DISP-02
  - DISP-03
  - DISP-04
  - DISP-05
  - DISP-06
  - CLI-03
  - POLICY-03
dependency-graph:
  requires:
    - thermocline.identity.BrineProvider
    - thermocline.identity.Verifier
    - thermocline.identity.Signature
    - thermocline.canonical.canonicalize
    - thermocline.schemes.KeyScheme
    - photophore.audit.AuditLog
    - photophore.channels.ChannelStore
    - photophore.classifier.classify
    - photophore.policy.author
    - photophore.policy.compare_result_against_policy
  provides:
    - photophore.dispatch.dispatch_async
    - photophore.dispatch.DispatchOutcome
    - photophore.dispatch.DispatchError
    - photophore.dispatch.DispatchSubcode
    - photophore.dispatch._transport.send_async
    - photophore.cli.dispatch_cmds.dispatch_command
    - "photophore.core.AuditEventType.CHANNEL_PUBKEY_REGISTERED"
    - tools/ast_lint_network_isolation.py
  affects:
    - photophore.errors  # late re-exports via PEP 562 __getattr__
    - photophore.cli.channel_cmds  # adds --fetch-pubkey-from option
tech-stack:
  added:
    - httpx>=0.27  # already in pyproject from Task 1; first runtime use here
    - pytest-asyncio>=0.23  # already in dev deps from Task 1; consumed by tests
  patterns:
    - "Sync-core + async shim via asyncio.to_thread (Phase 2 D-11 carry-forward)"
    - "Hard-fail abort gates at steps 5, 8a, 8b (DISP-02, DISP-03, POLICY-03)"
    - "AT-A1 fail-closed compare (None envelope_scheme != concrete channel.key_scheme)"
    - "Canonical-JSON signing input via thermocline.canonical.canonicalize (DISP-04)"
    - "PEP 562 __getattr__ for lazy re-export to break circular imports"
    - "Stdlib ast walk for compile-time network-isolation lint (DISP-05)"
    - "D-07 atomic three-step (keystore → audit → channels.db) on TOFU pubkey fetch"
key-files:
  created:
    - photophore/python/src/photophore/dispatch/_transport.py
    - photophore/python/src/photophore/dispatch/_coordinator.py
    - photophore/python/src/photophore/cli/dispatch_cmds.py
    - photophore/tools/ast_lint_network_isolation.py
    - photophore/tools/__init__.py
    - photophore/python/Makefile
    - photophore/python/tests/dispatch/test_dispatch_coordinator.py
    - photophore/python/tests/dispatch/test_dispatch_at_a1.py
    - photophore/python/tests/dispatch/test_dispatch_cli.py
    - photophore/python/tests/cli/__init__.py
    - photophore/python/tests/cli/test_channel_cmds.py
    - photophore/python/tests/tools/__init__.py
    - photophore/python/tests/tools/test_ast_lint_network_isolation.py
  modified:
    - photophore/python/src/photophore/dispatch/__init__.py  # re-exports dispatch_async + DispatchOutcome
    - photophore/python/src/photophore/dispatch/_errors.py   # Task 1 — DispatchError + DispatchSubcode
    - photophore/python/src/photophore/dispatch/_aio.py      # Task 1 — asyncio.to_thread shim
    - photophore/python/src/photophore/errors.py             # PEP 562 __getattr__ for late re-export
    - photophore/python/src/photophore/core.py               # +CHANNEL_PUBKEY_REGISTERED
    - photophore/python/src/photophore/cli/__init__.py       # registers dispatch_command
    - photophore/python/src/photophore/cli/channel_cmds.py   # --fetch-pubkey-from + D-07 audit step
    - photophore/python/tests/dispatch/conftest.py           # in_memory_keyring fixture
    - photophore/python/pyproject.toml                       # Task 1 — httpx + pytest-asyncio
decisions:
  - "AT-A1 fail-closed: None envelope_scheme against any concrete channel.key_scheme is treated as mismatch (T-03-02). Guarantees an attacker cannot bypass the guard by omitting dispatch_signature."
  - "Lazy re-export of DispatchError/DispatchSubcode in photophore.errors via PEP 562 __getattr__ to break a circular import (errors → dispatch.__init__ → _coordinator → audit → errors)."
  - "Conservative v0.1 POLICY-03 derivation: forge MUST surface persisted_fields and returned_fields in the result envelope; absent fields are treated as empty (the forge wrote nothing)."
  - "DispatchOutcome.result_body field carries the parsed task_result envelope on success — populated only after receipt-verify AND policy-compare both pass; explicit inspection path for Plan 03-03 describe-forge normative-string tests."
  - "Transport carve-out kept narrow: the AST lint allow-list is exactly photophore/dispatch/, photophore/cli/dispatch_cmds.py, photophore/cli/channel_cmds.py. Adding any further httpx import in photophore source MUST extend the allow-list and the threat-model justification."
metrics:
  duration: "~1 hour (resume from Task 1; Task 2 + Task 3 RED/GREEN)"
  tasks_completed: 3
  files_created: 13
  files_modified: 9
  commits: 6
  loc:
    runtime: 815  # dispatch package + cli dispatch + ast lint + Makefile
    tests: 1349   # all dispatch + tools + cli/channel test files
  tests_total: 319  # full photophore suite passing
  tests_new_this_plan: 41  # 6 (Task 1) + 14 (Task 2) + 7+11+2 (Task 3)
completed: "2026-05-11"
---

# Phase 3 Plan 1: `photophore.dispatch` — Async 9-Step Privacy Receipt Coordinator + CLI + AST Lint

The policy engine's runtime kernel: `dispatch_async()` executes the canonical 9-step Photophore flow (resolve → classify → shadow → policy → audit-pre → sign → send → verify → audit-post) with hard-fail gates that make AT-A1, DISP-02, DISP-03, and POLICY-03 structurally inescapable, plus a custom stdlib-AST lint that pins the DISP-05 network-isolation contract to the source tree.

## One-Liner

`photophore.dispatch.dispatch_async(channel_id, task_draft, ...)` — async 9-step coordinator with 12 typed `DispatchSubcode` failure modes, fail-closed AT-A1 key_scheme guard, canonical-JSON signing input (DISP-04), POLICY-03 partial-closure compare at step 8b, single httpx transport surface enforced by stdlib-AST lint (DISP-05), CLI exit code 6 family, plus `channel new --fetch-pubkey-from URL` TOFU registration following the D-07 atomic three-step.

## Final File Inventory

### Runtime (`photophore/python/src/photophore/`)

| File | LOC | Role |
|------|-----|------|
| `dispatch/__init__.py` | 12 | Public surface: `dispatch_async`, `DispatchOutcome`, `DispatchError`, `DispatchSubcode` |
| `dispatch/_errors.py` | 62 | `DispatchSubcode` (12 StrEnum members) + `DispatchError(PhotophoreError)` |
| `dispatch/_aio.py` | 47 | `asyncio.to_thread` shim wrapping Phase 2 sync APIs (D-11) |
| `dispatch/_coordinator.py` | 383 | `async def dispatch_async` — the 9-step flow with 13 raise sites |
| `dispatch/_transport.py` | 80 | `httpx.AsyncClient.post` wrapper with TIMEOUT/REFUSED/MALFORMED mapping |
| `cli/dispatch_cmds.py` | 111 | `@click.command("dispatch")` — `--channel/--task/--forge-url`; exit 6 family |
| `cli/channel_cmds.py` | 275 (Δ +110) | adds `--fetch-pubkey-from URL` with D-07 atomic three-step |
| `cli/__init__.py` | Δ +2 | registers `dispatch_command` under the root click group |
| `core.py` | 103 (Δ +5) | adds `AuditEventType.CHANNEL_PUBKEY_REGISTERED` to `KNOWN_EVENT_TYPES` |
| `errors.py` | Δ +10 | converts late re-export of `DispatchError/DispatchSubcode` to PEP 562 `__getattr__` |

### Tools + build glue

| File | LOC | Role |
|------|-----|------|
| `photophore/tools/__init__.py` | 0 | package marker |
| `photophore/tools/ast_lint_network_isolation.py` | 110 | stdlib-AST DISP-05 enforcer; CLI exits 0/1 |
| `photophore/python/Makefile` | 10 | `lint-isolation`, `lint`, `test` targets |

### Tests (`photophore/python/tests/`)

| File | LOC | Tests |
|------|-----|-------|
| `dispatch/conftest.py` | 47 | `in_memory_keyring`, `tmp_audit_log` fixtures |
| `dispatch/test_dispatch_errors.py` | 131 | Task 1: subcodes, retryable set, optional fields, asyncio shim, D-11 invariant (6 tests) |
| `dispatch/test_dispatch_coordinator.py` | 508 | Task 2: step-1, audit-pre abort, signing, transport, receipt-invalid, policy-violated, happy path, audit-post, canonicalize spy, json.dumps gate (12 tests) |
| `dispatch/test_dispatch_at_a1.py` | 184 | Task 2: AT-A1 fixture replay, AT-A1 fail-closed (no key_scheme field), unknown channel (3 tests) |
| `dispatch/test_dispatch_cli.py` | 251 | Task 3: human/JSON happy path, CHANNEL_RESOLVE_FAILED/RECEIPT_INVALID/POLICY_VIOLATED/AUDIT_FAILED_PRE exit-6 mapping, --help (7 tests) |
| `cli/test_channel_cmds.py` | 89 | Task 3: KNOWN_EVENT_TYPES regression guard + D-07 atomic three-step on pubkey fetch (2 tests) |
| `tools/test_ast_lint_network_isolation.py` | 139 | Task 3: clean tree, httpx/requests/aiohttp rejection, dispatch & cli carve-outs, thermocline.envelope rejection, CLI exit codes (11 tests) |

**Total new tests this plan: 41. Full photophore suite after plan: 319 passing.**

## Subcode Raise-Site Map (`_coordinator.py`)

| Line | Stage | Subcode | Step | Notes |
|------|-------|---------|------|-------|
| 112 | 1 | `CHANNEL_RESOLVE_FAILED` | resolve | channel_show_async exception |
| 124 | 1 | `CHANNEL_RESOLVE_FAILED` | resolve | **AT-A1 fail-closed** key_scheme guard (T-03-02) |
| 135 | 1 | `CHANNEL_RESOLVE_FAILED` | resolve | channel.state is not OPEN |
| 161 | 2 | `CLASSIFICATION_FAILED` | classify | classifier exception |
| 182 | 3 | `SHADOW_GENERATION_FAILED` | shadow | shadow-id collection exception |
| 194 | 4 | `POLICY_AUTHORING_FAILED` | author | policy.author exception |
| 223 | 5 | `AUDIT_FAILED_PRE` | audit-pre | **DISP-02 abort gate** (retryable; signing never runs) |
| 248 | 6 | `SIGNING_FAILED` | sign | BrineProvider.sign exception (retryable) |
| 284 | 8 | `RECEIPT_MALFORMED` | verify | `receipt_signature.bytes_hex` missing |
| 308 | 8 | `RECEIPT_INVALID` | verify | verifier raised (SchemeError, IdentityError, etc.) |
| 317 | 8 | `RECEIPT_INVALID` | verify | **DISP-03 hard-fail gate** — Verifier.verify returned None |
| 336 | 8 | `POLICY_VIOLATED` | compare | **POLICY-03 closure** — compare_result_against_policy returned False |
| 361 | 9 | `AUDIT_FAILED_POST` | audit-post | replay-safe; retryable per CONTEXT D-03 |

Plus the transport-layer raise sites in `_transport.py`:
- `TRANSPORT_TIMEOUT` (stage 7) on `httpx.TimeoutException`
- `TRANSPORT_REFUSED` (stage 7) on `httpx.ConnectError | httpx.HTTPError`
- `RECEIPT_MALFORMED` (stage 8) on non-JSON response body

The 12 distinct `DispatchSubcode` values from CONTEXT D-03 are exhaustively covered — `grep -c "subcode=DispatchSubcode\." python/src/photophore/dispatch/_coordinator.py` returns 13 (one raise site uses CHANNEL_RESOLVE_FAILED twice — unknown channel vs. wrong state).

## AT-A1 Wire-In Evidence

The AT-A1 ("channel impersonation") fixture at `/Users/dom/Projects/dom/thermocline/thermocline/conformance/invalid/AT-A1-channel-impersonation.json` carries `_phase_wired: 3`. The behavioral wire-in lives in `tests/dispatch/test_dispatch_at_a1.py::test_at_a1_fixture_rejected`:

```python
fixture = json.loads(_AT_A1_FIXTURE_PATH.read_text())
envelope = fixture["envelope"]  # declares key_scheme="brine"
_seed_channel(store, channel_id="at-a1-channel-impersonated-id",
              key_scheme="none")  # fixture says channel has key_scheme="none"

with pytest.raises(DispatchError) as excinfo:
    await dispatch_async(...)

assert excinfo.value.subcode is DispatchSubcode.CHANNEL_RESOLVE_FAILED
assert excinfo.value.stage == 1
assert excinfo.value.audit_entry_hash is None  # no pre-dispatch audit
provider.sign.assert_not_called()  # no signing
rows = audit_log.query(envelope_id=envelope["envelope_id"])
assert rows == []  # zero audit entries
```

The **fail-closed** variant in `test_at_a1_envelope_without_key_scheme_field_rejected` pins T-03-02: an envelope with neither `dispatch_signature` block nor top-level `key_scheme` field is **still rejected** at step 1 (None != "brine"), proving the guard cannot be bypassed by omission.

## POLICY-03 Closure Evidence

`tests/dispatch/test_dispatch_coordinator.py::test_step8b_policy_violated_no_audit_post`:

```python
_seed_channel(store, channel_id="chan-1", ceiling="tier-0")
# tier-0 policy: strip_before_persist=["*"] — NOTHING may be persisted.
bad_result["persisted_fields"] = ["leak"]  # forge violates tier-0
# (verifier.verify returns a real Receipt; this isn't a sig failure)

with pytest.raises(DispatchError) as excinfo:
    await dispatch_async(...)

assert excinfo.value.subcode is DispatchSubcode.POLICY_VIOLATED
assert excinfo.value.stage == 8
rows = audit_log.query(envelope_id="env-1")
assert len(rows) == 1, "audit-post must NOT be written when policy is violated"
```

The receipt was verified (good signature), but `compare_result_against_policy()` returned False because tier-0 forbids any persisted fields. No audit-post entry is appended — the verified receipt does not become part of the chain. This closes the partial-closure obligation Phase 2 left open.

## AST Lint Clean Run

```bash
$ cd photophore/python && python ../tools/ast_lint_network_isolation.py \
    src/ ../../thermocline/thermocline/python/src/
$ echo $?
0
```

The lint walks every `.py` file under both source trees, parses each with `ast.parse()`, and rejects any `import httpx|requests|aiohttp` or `from httpx|requests|aiohttp import ...` in the 11 protected modules. The 3 allow-list paths (`photophore/dispatch/`, `photophore/cli/dispatch_cmds.py`, `photophore/cli/channel_cmds.py`) override the protected list. Tested against 11 scenarios in `tests/tools/test_ast_lint_network_isolation.py`.

## Cross-Impl Spec Patches

**None.** The Thermocline + Photophore spec READMEs already define every shape this plan consumed (envelope `dispatch_signature.key_scheme`, `receipt_signature.bytes_hex`, `task_result.persisted_fields`, `task_result.returned_fields`). Phase 2 LEARNINGS THERMO-01 pattern did not trigger.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Circular import via late re-export in `errors.py`**

- **Found during:** Task 2 initial GREEN test run
- **Issue:** `photophore.errors` did `from .dispatch._errors import DispatchError, DispatchSubcode` at module bottom. After Task 2 added `_coordinator.py`, the dispatch package `__init__.py` started importing `_coordinator` (for `dispatch_async`), which transitively imports `audit`, which imports back into `photophore.errors` while it's mid-initialization → `ImportError: cannot import name 'AuditLog' from partially initialized module`.
- **Fix:** Converted the late re-export to PEP 562 module-level `__getattr__`. `DispatchError` and `DispatchSubcode` are now lazily loaded on attribute access; package init runs without ever touching `_coordinator`.
- **Files modified:** `photophore/python/src/photophore/errors.py`
- **Commit:** `dccb0f8` (Task 2 GREEN)

**2. [Rule 3 - Blocker] `CliRunner(mix_stderr=False)` removed in Click 8.3+**

- **Found during:** Task 3 RED run
- **Issue:** Plan's `<read_first>` referenced "Phase 2 LEARNINGS CliRunner `mix_stderr=False` discipline" — but the photophore venv has Click 8.3.3, which removed that constructor argument.
- **Fix:** Removed `mix_stderr=False` everywhere in Task 3 test files; plain `CliRunner()` is the current 8.3.3 idiom (and what existing `tests/test_cli_classify.py` already uses).
- **Files modified:** `python/tests/dispatch/test_dispatch_cli.py`, `python/tests/cli/test_channel_cmds.py`
- **Commit:** Folded into Task 3 RED `9bc49e3`.

### Carry-Forward Deviations from Task 1 (Already Documented in `8c74b62`)

- **[Rule 1 - Bug]** Plan's `<action>` used positional `log.append(entry)` and assumed a string return; the real Phase 2 `AuditLog.append` is kwargs-only and returns `AuditEntry`. The shim in `_aio.py::audit_append_async` adapts the call site and returns `entry.entry_hash` for the coordinator's `pre_audit_hash` / `post_audit_hash` bookkeeping.
- **[Rule 2 - Critical]** Plan implied `AuditLog._schema.connect` needed `check_same_thread=False` for `asyncio.to_thread` to function. The shim works because the sync `AuditLog` connection is reused across thread-pool tasks; verified by `test_aio_shim_audit_append` and the AUDIT_FAILED_POST happy-path test that calls `audit_append_async` twice in the same coroutine.

## Known Stubs

**None.** Every path that the coordinator can reach is either fully implemented or raises a typed `DispatchError`. The conservative POLICY-03 derivation rule (`persisted_fields` / `returned_fields` defaulted to `[]` when missing) is a documented v0.1 simplification — not a stub. Plan 03-03 will exercise it end-to-end against the real describe-forge.

## Threat Flags

None — the implementation introduces no surface beyond the threat model already enumerated in `03-01-PLAN.md`. The DISP-05 lint is the structural mitigation for T-03-05; the AT-A1 fail-closed guard mitigates T-03-02; the DISP-02/DISP-03/POLICY-03 abort gates close T-03-03/T-03-01/T-03-04.

## TDD Gate Compliance

All three tasks landed RED then GREEN:

| Task | RED Commit | GREEN Commit |
|------|------------|--------------|
| 1 (carry-forward) | `320e1df` test(03-01): RED | `8c74b62` feat(03-01): GREEN |
| 2 | `142f074` test(03-01): RED | `dccb0f8` feat(03-01): GREEN |
| 3 | `9bc49e3` test(03-01): RED | `e8dead4` feat(03-01): GREEN |

No GREEN preceded RED. No REFACTOR phase was needed (all GREEN passes were tight on first iteration after the two auto-fixes documented above).

## Self-Check: PASSED

- [x] `photophore/python/src/photophore/dispatch/_coordinator.py` exists (FOUND)
- [x] `photophore/python/src/photophore/dispatch/_transport.py` exists (FOUND)
- [x] `photophore/python/src/photophore/cli/dispatch_cmds.py` exists (FOUND)
- [x] `photophore/tools/ast_lint_network_isolation.py` exists (FOUND)
- [x] `photophore/python/Makefile` exists (FOUND)
- [x] Commit `8c74b62` (Task 1 GREEN) — FOUND
- [x] Commit `142f074` (Task 2 RED) — FOUND
- [x] Commit `dccb0f8` (Task 2 GREEN) — FOUND
- [x] Commit `9bc49e3` (Task 3 RED) — FOUND
- [x] Commit `e8dead4` (Task 3 GREEN) — FOUND
- [x] `python -m pytest tests/dispatch/ tests/tools/ -q` → 39 passed
- [x] AST lint exits 0 against real photophore + thermocline source trees
- [x] `len(list(DispatchSubcode)) == 12` confirmed
- [x] AT-A1 fixture loaded by `test_at_a1_fixture_rejected` (FOUND in test file)
- [x] `grep -rn "json.dumps" python/src/photophore/dispatch/` → 0 matches (DISP-04)
- [x] Full photophore suite: 319/319 tests passing (no Phase 2 regressions)

## Decisions Deferred to Plan 03-03

- **`persisted_fields` / `returned_fields` derivation for forges that omit them** — v0.1 treats absent fields as empty (the forge wrote nothing) which respects policy by construction. If a forge in Plan 03-03 surfaces a case where this rule produces a false negative (forge implicitly wrote a field but didn't declare it), the rule will need extension. Spec patch will follow the THERMO-01 cross-impl-spec-patch pattern.
- **Subprocess fixture for E2E forge tests** — `subprocess_forge(role)` fixture; deferred to Plan 03-03 per the plan split decision in CONTEXT D-05.
- **POLICY-03 end-to-end exercise against a real describe-forge** — Plan 03-03 Test "describe-forge variant that returns a result violating an authored `result_policy`".
- **The `pi-forge` regression replay with the new envelope handling** — Plan 03-02.

## Commits in This Plan

```
e8dead4 feat(03-01): dispatch CLI + AST lint + channel pubkey TOFU fetch (GREEN)
9bc49e3 test(03-01): add failing tests for dispatch CLI + AST lint + channel pubkey fetch (RED)
dccb0f8 feat(03-01): implement 9-step dispatch coordinator + httpx transport + AT-A1 step-1 gate (GREEN)
142f074 test(03-01): add failing tests for 9-step dispatch coordinator + AT-A1 fail-closed (RED)
8c74b62 feat(03-01): implement DispatchError + DispatchSubcode + asyncio.to_thread shim
320e1df test(03-01): add failing tests for DispatchError + DispatchSubcode + asyncio.to_thread shim
```

All commits land directly on `main` in `/Users/dom/Projects/dom/photophore/` (sequential single-executor sibling-repo mode; no worktree isolation; no commits in the thermocline planning hub except this SUMMARY).
