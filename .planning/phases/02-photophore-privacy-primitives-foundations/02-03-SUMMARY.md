---
phase: 02-photophore-privacy-primitives-foundations
plan: "03"
subsystem: privacy-primitives
tags: [photophore, shadow, policy, result-policy, thermocline, hypothesis, uuidv4, pydantic, click, mypy]

# Dependency graph
requires:
  - phase: 01-thermocline-py-foundations
    provides: "ResultPolicy (now public), ContentBlock, Sensitive[T], canonicalize, IdentityProvider"
  - phase: 02-photophore-privacy-primitives-foundations (plan 01)
    provides: "AuditLog, ChannelStore, Channel, photophore.errors base, click CLI groups"
  - phase: 02-photophore-privacy-primitives-foundations (plan 02)
    provides: "classify(), Tier, PhotophoreError hierarchy, photophore classify CLI"
provides:
  - "photophore.shadow: generate(), Shadow, ShadowResult, ContentType (6 types), ShadowIrreversibilityError"
  - "photophore.policy: author(), compare_result_against_policy(), PolicyError"
  - "thermocline.ResultPolicy: public export (OQ-2 spec patch, backward-compat alias)"
  - "photophore policy preview CLI subcommand (CLI-05)"
  - "AT-A2 conformance fixture wired behaviorally via Hypothesis (>=100 cases x 100 inner calls)"
  - "SHADOW-01..06 fully covered; POLICY-01..03 (Phase 2 partial) covered"
affects:
  - "03-dispatch-coordinator: imports generate, author, compare_result_against_policy"
  - "phase-4-hardening: shadow strategy extensions, full POLICY-03 close"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Shadow: frozen dataclass with UUIDv4 shadow_id per call (no caching)"
    - "Closed enum + match for ContentType abstraction dispatch (6 spec types)"
    - "_IRREVERSIBILITY_MIN_SUBSTR_LEN = 8 named constant (8-char threshold)"
    - "ShadowResult(shadow, warnings) frozen dataclass — hard-fail raises, soft-fail collects"
    - "_CEILING_TO_POLICY_TEMPLATE dict maps tier-0/1/2 -> ResultPolicy fields"
    - "POLICY-01 enforced structurally: author() never accesses draft['result_policy']"
    - "Hypothesis property test: outer 100 cases x inner 100 calls = 10,000 unique shadow_ids"
    - "Grep gate targeting only decorator/assignment patterns (not comment mentions)"

key-files:
  created:
    - photophore/python/src/photophore/shadow/_types.py
    - photophore/python/src/photophore/shadow/_strategies.py
    - photophore/python/src/photophore/shadow/_quality.py
    - photophore/python/src/photophore/shadow/_generate.py
    - photophore/python/src/photophore/shadow/__init__.py
    - photophore/python/src/photophore/policy/_author.py
    - photophore/python/src/photophore/policy/__init__.py
    - photophore/python/src/photophore/cli/policy_cmds.py
    - photophore/python/tests/test_shadow_types.py
    - photophore/python/tests/test_shadow_strategies.py
    - photophore/python/tests/test_shadow_quality.py
    - photophore/python/tests/test_shadow_generate.py
    - photophore/python/tests/test_shadow_uniqueness_property.py
    - photophore/python/tests/test_shadow_no_caching.py
    - photophore/python/tests/test_policy_author.py
    - photophore/python/tests/test_policy_violation.py
    - photophore/python/tests/test_cli_policy.py
    - photophore/python/tests/fixtures/task-draft.json
    - photophore/python/tests/fixtures/task-draft-with-injected-policy.json
    - thermocline/conformance/invalid/AT-A2-shadow-correlation.json
  modified:
    - thermocline/python/src/thermocline/envelope.py
    - thermocline/python/src/thermocline/__init__.py
    - thermocline/CHANGELOG.md
    - thermocline/schema/task.schema.json
    - thermocline/schema/job.schema.json
    - photophore/python/src/photophore/errors.py
    - photophore/python/src/photophore/cli/__init__.py
    - thermocline/conformance/invalid/MANIFEST.yaml

key-decisions:
  - "OQ-2 resolved: _ResultPolicy renamed to public ResultPolicy in thermocline-py; backward-compat alias retained; CHANGELOG.md records cross-impl contract"
  - "OQ-3 resolved: ShadowResult(shadow, warnings: tuple[str, ...]) frozen dataclass — hard-fail raises ShadowIrreversibilityError, soft-fail populates warnings"
  - "Shadow strategy shape: closed enum + match (6 types); v0.2 extension = add enum member + match arm"
  - "Irreversibility threshold: _IRREVERSIBILITY_MIN_SUBSTR_LEN = 8 chars (4-char produced false positives)"
  - "Credential abstraction uses 'auth-secret of class X' vocabulary to avoid leaking the word 'credential' when source contains it"
  - "POLICY-01 enforced structurally: comment in author() avoids mentioning the forbidden access pattern to keep grep gate clean"
  - "Grep gate for SHADOW-06 targets only decorator/assignment lines (not docstring prose), using ^\s*@lru_cache pattern"

patterns-established:
  - "Shadow type labels avoid vocabulary present in source content (e.g., 'auth-secret of class pem-encoded-key' not 'credential of type private-key')"
  - "Hypothesis inner-loop structure: outer @given(100) x inner range(100) = 10,000 calls proving no content-keyed cache"
  - "D-11 grep gates (no async def, no aiosqlite) co-located with SHADOW-06 grep gate in test_shadow_no_caching.py"
  - "Policy fixture pattern: load JSON draft + author() + compare vs injected = POLICY-01/03 behavioral proof"

requirements-completed:
  - SHADOW-01
  - SHADOW-02
  - SHADOW-03
  - SHADOW-04
  - SHADOW-05
  - SHADOW-06
  - POLICY-01
  - POLICY-02
  - POLICY-03
  - CLI-05

# Metrics
duration: ~65min
completed: "2026-05-10"
---

# Phase 2 Plan 03: Shadow Generator + Policy Authoring Summary

**thermocline.ResultPolicy made public (OQ-2 patch); photophore.shadow.generate() with 8-char irreversibility hard-fail and UUIDv4-per-call no-cache guarantee; photophore.policy.author() ignoring draft policy (POLICY-01); AT-A2 wired behaviorally via Hypothesis 100x100=10,000 shadow_id uniqueness test**

## Performance

- **Duration:** ~65 min
- **Started:** 2026-05-10T00:49:00Z
- **Completed:** 2026-05-10T01:54:06Z
- **Tasks:** 4 (thermocline patch + shadow module + policy module + CLI + AT-A2 fixture)
- **Files modified:** 7 modified, 20 created across thermocline + photophore repos

## Accomplishments

- thermocline-py spec patch: `_ResultPolicy` → public `ResultPolicy`; `__all__` + CHANGELOG.md updated; schema artifacts regenerated; all 142 Phase 1 tests still pass
- `photophore.shadow`: `generate()` with fresh UUIDv4 per call (SHADOW-06), 6 per-type abstraction strategies (closed enum + match), 8-char irreversibility hard-fail, soft-warn quality tests, Hypothesis property test (>=100 cases × 100 inner calls = >=10,000 unique IDs)
- `photophore.policy`: `author()` (POLICY-01 structurally ignores draft, POLICY-02 derives from ceiling), `compare_result_against_policy()` helper (POLICY-03 partial — full wire in Phase 3 dispatch coordinator)
- `photophore policy preview` CLI: `--json` mode emits single JSON document; POLICY-01 visible via `draft_policy_ignored` flag; exit code 5 on channel-not-found
- AT-A2 conformance fixture committed to `thermocline/conformance/invalid/` with MANIFEST.yaml entry (phase 2, behaviorally wired)
- Total: 142 thermocline tests + 278 photophore tests all pass; mypy --strict clean (14 photophore source files)

## Task Commits

Thermocline repo (planning hub):
1. **Task 1: thermocline-py ResultPolicy public export** - `2ea5544` (feat)
2. **Task 4b: AT-A2 conformance fixture + MANIFEST** - `2dc41b5` (feat)

Photophore repo (sibling):
1. **Task 2: shadow module** - `f6356ac` (feat)
2. **Task 3: policy module** - `c4a821b` (feat)
3. **Task 4a: policy preview CLI** - `d030dbd` (feat)

## Public API Surface

```python
# thermocline (after OQ-2 patch)
from thermocline import ResultPolicy  # public since Plan 02-03

# photophore.shadow
from photophore.shadow import (
    generate,                    # generate(content, content_type, relevance=0.5) -> ShadowResult
    Shadow,                      # frozen dataclass: shadow_id, content_type, abstraction, relevance, tier=1
    ShadowResult,               # frozen dataclass: shadow, warnings: tuple[str, ...]
    ContentType,                 # 6-member enum: DOCUMENT/CONVERSATION/CREDENTIAL/FILE/IDENTITY/CODE
    ShadowIrreversibilityError,  # hard-fail exception (dispatch must abort)
    irreversibility_test,        # def irreversibility_test(source_content, abstraction) -> None
    relevance_preservation_test, # def relevance_preservation_test(...) -> list[str]
    distinguishability_test,     # def distinguishability_test(abstraction) -> list[str]
)

# photophore.policy
from photophore.policy import (
    author,                          # def author(channel, envelope_draft) -> ResultPolicy
    compare_result_against_policy,   # def compare_result_against_policy(received, policy) -> bool
    ResultPolicy,                    # re-exported from thermocline
    PolicyError,                     # base exception
)
```

## Files Created/Modified

Thermocline repo:
- `thermocline/python/src/thermocline/envelope.py` — `_ResultPolicy` → `ResultPolicy` (public) + backward-compat alias
- `thermocline/python/src/thermocline/__init__.py` — `ResultPolicy` added to imports + `__all__`
- `thermocline/CHANGELOG.md` — v0.3.1 OQ-2 spec patch entry
- `thermocline/schema/task.schema.json` — `$defs` key `_ResultPolicy` → `ResultPolicy` (D-02 pipeline)
- `thermocline/schema/job.schema.json` — same rename
- `thermocline/conformance/invalid/AT-A2-shadow-correlation.json` — shadow correlation fixture
- `thermocline/conformance/invalid/MANIFEST.yaml` — AT-A2 entry added

Photophore repo (new files):
- `photophore/python/src/photophore/shadow/_types.py` — ContentType, Shadow, ShadowResult
- `photophore/python/src/photophore/shadow/_strategies.py` — 6 per-type strategies + closed match
- `photophore/python/src/photophore/shadow/_quality.py` — irreversibility (hard), relevance + distinguishability (soft)
- `photophore/python/src/photophore/shadow/_generate.py` — generate() orchestrator
- `photophore/python/src/photophore/shadow/__init__.py` — public re-exports
- `photophore/python/src/photophore/policy/_author.py` — author() + compare_result_against_policy()
- `photophore/python/src/photophore/policy/__init__.py` — public re-exports
- `photophore/python/src/photophore/cli/policy_cmds.py` — `policy preview` subcommand
- 8 test files: test_shadow_*.py, test_policy_*.py, test_cli_policy.py
- 2 fixtures: task-draft.json, task-draft-with-injected-policy.json

Photophore repo (modified):
- `photophore/python/src/photophore/errors.py` — ShadowIrreversibilityError + PolicyError added
- `photophore/python/src/photophore/cli/__init__.py` — `photophore.add_command(policy)` added

## Decisions Made

1. **OQ-2 (ResultPolicy public):** Renamed `_ResultPolicy` → `ResultPolicy` in thermocline-py; added to `__all__`; backward-compat alias `_ResultPolicy = ResultPolicy` retained; schema artifacts regenerated via `build_schemas --write` (standard D-02 pipeline; `$defs` key changed in task.schema.json and job.schema.json). Cross-impl contract recorded in CHANGELOG.md v0.3.1.

2. **OQ-3 (shadow soft-fail):** `ShadowResult(shadow: Shadow, warnings: tuple[str, ...])` frozen dataclass. Hard-fail (irreversibility) raises `ShadowIrreversibilityError`; soft-fail (relevance/distinguishability) populates `warnings`. Phase 3 dispatch coordinator records non-empty warnings to audit.

3. **Shadow strategy shape:** Closed enum (`ContentType`) + `match content_type:` dispatch in `_generate_abstraction()`. 6 spec-mandated arms (DOCUMENT/CONVERSATION/CREDENTIAL/FILE/IDENTITY/CODE). v0.2 extension path: add enum member + match arm (two localized changes).

4. **Irreversibility threshold:** `_IRREVERSIBILITY_MIN_SUBSTR_LEN = 8` (named constant). 4-char threshold produced false positives on common English words ("at", "of", "in"); 8-char threshold verified clean per 02-RESEARCH §7.

5. **Credential strategy vocabulary:** Changed from "credential of type X" to "auth-secret of class X" to prevent false positives when source content contains the word "credential" (which would cause "credenti" (8 chars) to appear in both source and abstraction).

6. **POLICY-01 structural enforcement:** `author()` comment explicitly states the policy field is not consulted, but uses paraphrase (not the literal access pattern) so the grep gate (`envelope_draft["result_policy"]` / `envelope_draft.get("result_policy")`) stays at 0 matches.

7. **Grep gate precision:** Shadow no-caching grep gate uses `^\s*@lru_cache` (decorator line anchor) not plain `@lru_cache`, so docstring/comment mentions don't trigger false positives. Same pattern applied to POLICY-01 comment rewrite.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Credential abstraction vocabulary caused irreversibility false positive**
- **Found during:** Task 2 (shadow strategies + quality tests)
- **Issue:** `_abstract_credential()` returned `"credential of type generic"` which contains "credenti" (8 chars). Source content `b"credential content"` also contains "credenti". The irreversibility test correctly rejected this — but it was a false positive from poor vocabulary choice.
- **Fix:** Changed credential abstraction labels to "auth-secret of class X" vocabulary. The labels remain spec-compliant ("credential type only" — now expressed as "auth-secret class") and don't overlap with common credential source content.
- **Files modified:** `photophore/python/src/photophore/shadow/_strategies.py`, `photophore/python/tests/test_shadow_strategies.py`, `photophore/python/tests/test_shadow_generate.py`
- **Committed in:** f6356ac (Task 2 commit)

**2. [Rule 1 - Bug] Grep gate matched comment text (false positive)**
- **Found during:** Task 2 (test_shadow_no_caching.py)
- **Issue:** Original grep pattern `@functools\.cache|@lru_cache|_shadow_cache|@cache` also matched module docstrings that document the no-caching contract (e.g., "NO CACHING: no module-level shadow cache, no @lru_cache, no @functools.cache").
- **Fix:** Updated grep pattern to `^\s*@lru_cache|^\s*@functools\.cache|^\s*@cache\b|^\s*_shadow_cache\s*=` — targets decorator application and dict assignment, not prose mentions.
- **Files modified:** `photophore/python/tests/test_shadow_no_caching.py`
- **Committed in:** f6356ac (Task 2 commit)

**3. [Rule 3 - Blocking] CLI test used wrong channel new option flags**
- **Found during:** Task 4 (test_cli_policy.py)
- **Issue:** Test helper `_create_channel()` passed `--local-node` and `--creator-identity` flags that don't exist on `photophore channel new`. The actual CLI uses system defaults for local_node (from env/config).
- **Fix:** Removed non-existent flags from test helper; used only `--remote-node`, `--ceiling`, `--key-scheme` (the actual supported options).
- **Files modified:** `photophore/python/tests/test_cli_policy.py`
- **Committed in:** d030dbd (Task 4 commit)

---

**Total deviations:** 3 auto-fixed (2 Rule 1 bugs, 1 Rule 3 blocking issue)
**Impact on plan:** All fixes necessary for correctness. No scope creep.

## Requirement Crosswalk

| Req ID | Evidence File | Test Name |
|--------|---------------|-----------|
| SHADOW-01 | test_shadow_generate.py | TestGenerateTwoCallsDistinctIds::test_two_calls_identical_input_produce_distinct_ids |
| SHADOW-02 | test_shadow_uniqueness_property.py | test_shadow_id_uniqueness (Hypothesis 100 outer × 100 inner) |
| SHADOW-03 | test_shadow_strategies.py | TestDocumentStrategy, TestCredentialStrategy, TestCodeStrategy, ... (6 strategy classes) |
| SHADOW-04 hard-fail | test_shadow_quality.py | TestIrreversibilityTestHardFail::test_raises_on_leaked_substring |
| SHADOW-04 soft-warn | test_shadow_quality.py | TestRelevancePreservationTestSoftWarn, TestDistinguishabilityTestSoftWarn |
| SHADOW-05 | test_cli_policy.py | TestPolicyPreviewJsonMode::test_preview_tier1_json (shadow_refs in return_only) |
| SHADOW-06 | test_shadow_no_caching.py | TestNoCachingGrepGate + TestNoCachingBehavioral |
| POLICY-01 | test_policy_author.py | TestAuthorPolicy01IgnoresDraftPolicy::test_injected_policy_is_ignored |
| POLICY-02 | test_policy_author.py | TestAuthorTier0/Tier1/Tier2 ceiling → policy derivation |
| POLICY-03 (partial) | test_policy_violation.py | TestPolicy03InjectedPolicyFixture::test_injected_policy_vs_authored_policy |
| CLI-05 | test_cli_policy.py | Full test class suite (10 tests) |

**POLICY-03 note:** Phase 2 ships the `compare_result_against_policy()` helper + violating fixture. Full closure requires Phase 3 dispatch coordinator (Plan 03-01) to call the helper at step 9 (verify-receipt then compare). Plan 03-01 MUST list POLICY-03 in its requirements frontmatter.

## POLICY-03 (Phase 2 partial) Scope

`compare_result_against_policy(envelope, policy) -> bool` helper is shipped and tested. The helper:
- Returns `False` when `persisted_fields` violates `strip_before_persist` (any or specific fields)
- Returns `False` when `returned_fields` exceed `return_only ∪ persist_to_shared`
- Returns `False` when `persisted_fields` exceed `persist_to_shared`
- Returns `True` when all rules are satisfied

Full POLICY-03 (receipt-step rejection) is Phase 3 scope — Plan 03-01 dispatch coordinator, step 9.

## Known Stubs

None — all implemented functionality is wired to real behavior. The v0.1 abstraction strategies are intentionally minimal templates (not stubs) — Phase 4 may add corpus-statistical heuristics.

## Threat Flags

No new network endpoints, auth paths, or file access patterns introduced beyond what the plan's threat model anticipated. All T-02-24..T-02-34 threats mitigated as designed.

## Next Phase Readiness

Phase 3 dispatch coordinator (Plan 03-01) can now:
```python
from photophore.shadow import generate, ContentType, ShadowResult
from photophore.policy import author, compare_result_against_policy
from thermocline import ResultPolicy
```

Phase 3 must:
1. Add `POLICY-03` to plan 03-01 requirements frontmatter (partial closure completes there)
2. Call `compare_result_against_policy(received_result, authored_policy)` at dispatch step 9
3. Record non-empty `ShadowResult.warnings` to the audit log (soft-fail wire, SHADOW-04)
4. Wire `shadow.generate()` as dispatch step 3 for tier-1 ContentBlocks

## Self-Check

## Self-Check: PASSED

### Files verified:
- FOUND: thermocline/python/src/thermocline/envelope.py (class ResultPolicy)
- FOUND: photophore/python/src/photophore/shadow/__init__.py
- FOUND: photophore/python/src/photophore/policy/__init__.py
- FOUND: photophore/python/src/photophore/cli/policy_cmds.py
- FOUND: thermocline/conformance/invalid/AT-A2-shadow-correlation.json
- FOUND: .planning/phases/02-photophore-privacy-primitives-foundations/02-03-SUMMARY.md

### Commits verified:
- 2ea5544: feat(02-03): expose ResultPolicy publicly in thermocline-py (OQ-2 spec patch)
- f6356ac: feat(02-03): shadow module (photophore repo)
- c4a821b: feat(02-03): policy module (photophore repo)
- d030dbd: feat(02-03): policy preview CLI (photophore repo)
- 2dc41b5: feat(02-03): AT-A2 conformance fixture + MANIFEST

### Test suite results:
- thermocline: 142/142 passed
- photophore: 278/278 passed
- mypy --strict: clean (14 photophore source files + 2 thermocline files)
