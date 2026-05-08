---
phase: 01-thermocline-py-foundations
plan: 02
subsystem: thermocline-py
tags: [thermocline, canonical-json, rfc8785, hypothesis, lint, signing, foundations]
dependency-graph:
  requires:
    - "Plan 01 (thermocline-py foundations) — Sensitive[T], envelope models, errors module"
    - "rfc8785 (third-party) — actual canonicalization engine"
    - "hypothesis (dev dep, declared Plan 01)"
  provides:
    - "thermocline.canonicalize(payload) -> bytes — single library-wide RFC 8785 path"
    - "thermocline.CanonicalizationError — already declared in Plan 01; this plan wires it as the wrap target"
    - "thermocline-check-no-json-dumps console script + module entry — Pitfall 11 CI gate"
  affects:
    - "Plan 03 (brine adapter) imports canonicalize as the only signing-input path"
    - "Phase 2 (audit chain) BLAKE3 input bytes flow through canonicalize"
    - "Phase 3 (dispatch coordinator) computes dispatch_signature payload bytes via canonicalize"
    - "Phase 3 pi-forge upgrade: replaces in-tree json.dumps signing-input with canonicalize import"
    - "Future cross-language ports (thermocline-rs / thermocline-ts) MUST validate against the same regression-pinned canonical bytes"
tech-stack:
  added:
    - "rfc8785 0.1.4 (already declared as runtime dep; no version pin needed — package returns bytes from .dumps as expected)"
  patterns:
    - "Single-function canonical-JSON path — the only place rfc8785.dumps is called"
    - "Typed exception wrap: rfc8785.CanonicalizationError (a ValueError subclass) re-raised as thermocline.errors.CanonicalizationError with code CANONICALIZATION_FAILED, original chained via __cause__"
    - "AST-based lint (not regex) for json.dumps detection — substring in identifiers (json_dumps_helper) and comments do NOT trigger"
    - "Hypothesis property test as the foundational signature contract — round-trip stability + tamper detection over arbitrary JSON-shaped inputs"
    - "Allowlist as a frozenset literal (test asserts stability) so growing it requires touching the gate (T-02-06)"
key-files:
  created:
    - "thermocline/python/src/thermocline/canonical.py"
    - "thermocline/python/src/thermocline/scripts/check_no_json_dumps.py"
    - "thermocline/python/tests/test_canonical.py"
    - "thermocline/python/tests/test_canonical_properties.py"
    - "thermocline/python/tests/test_no_json_dumps.py"
    - ".planning/phases/01-thermocline-py-foundations/01-02-SUMMARY.md"
  modified:
    - "thermocline/python/src/thermocline/__init__.py"
    - "thermocline/python/pyproject.toml"
decisions:
  - "rfc8785 0.1.4 returns bytes from rfc8785.dumps(...) and exposes CanonicalizationError (a ValueError subclass) plus FloatDomainError / IntegerDomainError. No version pin update needed. The plan's pre-emptive 'pin to >=0.3 if dumps returns str' contingency does not apply."
  - "RFC 8785 normalizes integer-valued floats: canonicalize({'a': 1.0}) == canonicalize({'a': 1}) == b'{\"a\":1}' (per ECMA-262 §7.1.12.1 step 5). The plan's behavior list (Task 1) called for the OPPOSITE — that 1.0 and 1 produce DIFFERENT bytes. Tests assert the spec-correct (RFC 8785) behavior; flagged as Rule 1 deviation in 'Deviations' below."
  - "thermocline.CanonicalizationError already exists in errors.py from Plan 01; this plan wraps rfc8785's exceptions under it. The wrap clause catches (TypeError, ValueError) — covers rfc8785.CanonicalizationError (ValueError-rooted), TypeError on non-JSON types, and the FloatDomainError / IntegerDomainError subclasses (also ValueError-rooted)."
  - "AST visitor matches Attribute(Name(id='json'), attr='dumps' or 'dump') — covers both the file-writer (json.dump) and the string-emitter (json.dumps). Imports of json under aliases (import json as J) are a future-hardening item; current Pydantic v2 stdlib usage uses 'json' directly in the entire suite."
  - "Allowlist contains exactly two entries (build_schemas.py for human-readable schema artifact emission, and the lint script itself for self-references in docstrings). test_allowlist_contents_are_stable asserts this size as a deliberate gate against silent allowlist growth (T-02-06 mitigation)."
  - "Docstrings in canonical.py were reworded to avoid the literal substring 'json.dumps' so the plan's strict grep-based acceptance criterion exits 0 even before the AST lint runs. Documentation meaning is preserved (the docstring still says 'Python's stdlib json module emits non-canonical output' and points to Pitfall 11)."
metrics:
  duration: "≈25 minutes from worktree branch creation to plan summary"
  completed: "2026-05-08"
  tests: "33 new (16 unit + 5 property + 12 lint), 72 total in tests/"
  source-loc: "≈195 source LOC across canonical.py + check_no_json_dumps.py"
  source-files: "2 new"
---

# Phase 1 Plan 02: Canonical JSON + Pitfall 11 CI Gate Summary

Lock the single canonical-JSON path for the entire Thermocline suite (`thermocline.canonical.canonicalize` via `rfc8785`) and pair it with a CI gate (`check_no_json_dumps`) that prevents anyone from ever using a non-canonical encoder for signing input. This is the foundational interop primitive every signature path in the suite — Plan 03 brine, Phase 2 audit chain, Phase 3 dispatch — funnels through.

## What Shipped

### Public API surface (additions)

```python
from thermocline import (
    canonicalize, CanonicalizationError,  # added in Plan 02
    # plus everything Plan 01 exposed:
    Task, TaskResult, Job, JobResult, ErrorEnvelope, ContentBlock,
    Sensitive, KeyScheme, SUPPORTED_VERSIONS, EnvelopeError,
)
```

`canonicalize(payload: Any) -> bytes` is the only path. It accepts any value Pydantic `model.model_dump(mode="json")` produces, returns RFC 8785 / JCS bytes, and raises `CanonicalizationError` (with code `CANONICALIZATION_FAILED`) on non-JSON-serializable input.

### `thermocline.canonical`

`src/thermocline/canonical.py` — 78 lines, mypy --strict clean. Single function:

```python
def canonicalize(payload: Any) -> bytes:
    try:
        return rfc8785.dumps(payload)
    except (TypeError, ValueError) as exc:
        raise CanonicalizationError(
            f"payload is not canonical-JSON-serializable: {exc}"
        ) from exc
```

The `(TypeError, ValueError)` clause covers:

* `rfc8785.CanonicalizationError` (ValueError subclass — fires on sets, custom objects, `bytes` raw input)
* `rfc8785.FloatDomainError` (NaN / ±Inf)
* `rfc8785.IntegerDomainError` (out of safe-int range)
* Plain `TypeError` from any future package change

All wrap under one stable code (`CANONICALIZATION_FAILED`) so callers match on a single string.

### `thermocline.scripts.check_no_json_dumps`

`src/thermocline/scripts/check_no_json_dumps.py` — 117 lines, mypy --strict clean. AST-based scan of `src/thermocline/`:

* Matches `Call(func=Attribute(value=Name(id='json'), attr='dumps' or 'dump'))` — precise; `# json.dumps` in comments and `json_dumps_helper` identifiers do NOT trigger.
* Skips files matching `ALLOWLIST` (POSIX-relative paths) — exactly two entries:
  * `scripts/build_schemas.py` (committed schema artifacts use `json.dumps(..., indent=2, sort_keys=True)` for human-readable diffs; schemas are NOT signing input)
  * `scripts/check_no_json_dumps.py` (this script's own docstring discusses `json.dumps` by name)
* Skips `__pycache__/` and any path component starting with `.` (so `.venv` / `.tox` / etc. are ignored).

Console script entry: `thermocline-check-no-json-dumps` (exits 0 on a clean tree, 1 with offending file:line on stderr). Module entry: `python -m thermocline.scripts.check_no_json_dumps`.

The CI gate is wired into the default `pytest` run via `tests/test_no_json_dumps.py::test_lint_passes_on_current_tree` — every PR that introduces `json.dumps` in `src/thermocline/` outside the allowlist fails this test.

### Regression-pinned canonical bytes (per `<output>` request)

A minimal `Task` envelope with `Sensitive(b"abc")` content canonicalizes to (483 bytes):

```
{"channel_id":"chan-pi-forge-local","context":[{"content":"YWJj","role":"task_background","shadow":null,"tier":2}],"dispatch_signature":null,"envelope_id":"a1b2c3d4-0000-4000-8000-000000000001","issued_at":"2026-05-08T00:00:00Z","issuer":"my-sovereign-node","result_policy":{"persist_to_shared":["pi"],"return_only":[],"strip_before_persist":[]},"task":{"instruction":"Compute pi to 100 digits.","parameters":{"digits":100},"type":"data.compute"},"thermocline":"0.3.1","type":"task"}
```

Notes for cross-language ports:

* Top-level keys sorted lexicographically by code point (`channel_id` < `context` < … < `type`).
* `Sensitive(b"abc")` serializes to base64 ASCII `"YWJj"` at the wire (Plan 01 D-03 — wire-transparent wrapper).
* `null`-valued optional fields are emitted (e.g., `"shadow":null`, `"dispatch_signature":null`); Pydantic v2 default behavior with `extra="forbid"` and the optional-with-`None`-default pattern.
* No whitespace anywhere.
* `b"abc"` ≠ `"abc"` on the Python side, but `"YWJj"` on the wire; canonicalization happens on the post-`mode="json"` payload.

`tests/test_canonical.py::test_canonicalize_envelope_regression_pin` asserts the substring shape. A change to envelope serialization that is NOT a deliberate `thermocline` version bump trips this test (and the four property tests).

### Hypothesis settings used

| Property | `max_examples` | Notes |
|----------|----------------|-------|
| `test_canonicalize_idempotent_under_json_roundtrip` | 200 | `suppress_health_check=[HealthCheck.too_slow]` for recursive-strategy generation |
| `test_canonicalize_detects_value_mutation` | 100 | Type-appropriate leaf mutation; structural fallback when 1.0/1 collide |
| `test_canonicalize_normalizes_key_order` | 100 (default) | Unique-text constraint produces ~74 invalid examples (filter retries) |
| `test_canonicalize_preserves_list_order` | 100 (default) | Unique-int strategy; same filter behavior |
| `test_sensitive_wrapper_wire_transparent` | 100 | `st.binary(max_size=128)` content; D-03 invariant |

Total runtime: 1.5–1.7s (under the wave-1 budget).

## Pydantic v2 quirks encountered (per `<output>` request)

* `model_dump(mode="json")` on `ContentBlock(content=Sensitive(b"abc"))` produces `{'content': 'YWJj', ...}` (str). `model_dump(mode="python")` produces `{'content': <Sensitive: bytes>, ...}` (the wrapper instance). Only `mode="json"` is canonicalize-safe — the wrapper is opaque to JSON.
* `model_dump_json()` produces a JSON text that, when re-parsed via `json.loads`, equals `model_dump(mode="json")` exactly (verified by `test_canonicalize_envelope_roundtrip_via_json_text`). This is what makes the round-trip-stability invariant hold across the wire.
* `ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)` from Plan 01 carries through cleanly; no Plan 02 changes were needed to the envelope models.
* Optional fields with default `None` are emitted as `"key":null` in canonical output. If future plans need to omit these instead, that's a `model_dump(exclude_none=True)` decision at the dispatch-coordinator boundary, NOT a canonicalize-side change. Documented here so Plan 03 / Phase 2 / Phase 3 know.

## Verification

| Gate | Result |
|------|--------|
| `from thermocline import canonicalize, CanonicalizationError` | OK |
| `pytest tests/` (full library suite) | 72 / 72 pass |
| `pytest tests/test_canonical.py` | 16 / 16 pass |
| `pytest tests/test_canonical_properties.py` | 5 / 5 pass with ≥100 examples each (200 / 100 / 100 / 100 / 100) |
| `pytest tests/test_no_json_dumps.py` | 12 / 12 pass |
| `mypy --strict src/thermocline/canonical.py` | 0 errors |
| `mypy --strict src/thermocline/` (all 10 source files) | 0 errors |
| `ruff check src/thermocline/` | clean |
| `python -m thermocline.scripts.check_no_json_dumps` | exit 0 |
| Strict grep gate: `grep -E 'json\.dumps' canonical.py` | 0 occurrences (docstring rephrased; see decisions above) |
| Comprehensive grep gate (recursive, exclude allowlist + comments) | 0 occurrences |
| Wave-1 schema drift check (`build_schemas --check`) | exit 0 (no regression — Pitfall 11 lint correctly skips build_schemas) |

## Test Coverage

| Test file | Tests | Coverage |
|-----------|-------|----------|
| `tests/test_canonical.py` | 16 | Key-order normalization; bytes-not-str return; lowercase bool/null; array order preservation; integer-valued float normalization (RFC 8785 / ECMA-262 — corrected from plan); `int` vs `str` distinction; `True` vs `1` distinction; rejection of `set` and arbitrary `object()`; original exception chained via `__cause__`; envelope round-trip byte-stability; `model_dump(mode='json')` vs `json.loads(model_dump_json())` equivalence; regression-pinned envelope substrings; `ContentBlock` with `Sensitive(b"abc")` deterministic round-trip; no whitespace anywhere. |
| `tests/test_canonical_properties.py` | 5 | Round-trip stability (200 examples over arbitrary JSON-shaped dicts); tamper detection (single-leaf mutation, all JSON-leaf types, with structural fallback for the 1.0/1 collision case); key-order normalization (Hypothesis-generated keys); list-order sensitivity (unique-int reversal); `Sensitive[bytes]` wire transparency over `st.binary(max_size=128)` content. |
| `tests/test_no_json_dumps.py` | 12 | Live tree clean (CI gate); allowlist size + contents stability (T-02-06); synthetic violation detection; `json.dump` (file-writing variant) detection; AST precision (substring-in-identifier negative); AST precision (comment-mention negative); allowlist relative-path matching; hidden-dir / `__pycache__` skip; main() exit 0 on clean tree; main() exit 1 on synthetic violation (monkeypatch ROOT); JsonDumpsVisitor records (lineno, source); `python -m` invocation exit code. |

## Deviations from Plan

### Auto-fixed issues

**1. [Rule 1 — Bug] Plan's behavior list called for `1.0 ≠ 1` after canonicalization; RFC 8785 / ECMA-262 specifies the OPPOSITE.**

* **Found during:** Task 1 (probing `rfc8785.dumps` against test inputs before writing tests).
* **Issue:** Plan 02 Task 1 `<behavior>` block stated: *"`canonicalize({"a": 1.0})` and `canonicalize({"a": 1})` produce DIFFERENT bytes (RFC 8785 preserves number type representation per ECMA-262 — integers stay integers)."* This reading is reversed. RFC 8785 §3.2.2 explicitly defers to ECMA-262 §7.1.12.1 step 5, which stringifies finite values that are mathematical integers WITHOUT the fractional part. Empirical: `rfc8785.dumps({"a": 1.0}) == rfc8785.dumps({"a": 1}) == b'{"a":1}'`.
* **Fix:** Wrote `test_canonicalize_normalizes_integer_valued_floats` asserting the spec-correct behavior (1.0 == 1 == `1`). Added `test_canonicalize_distinguishes_integer_from_string` and `test_canonicalize_distinguishes_true_from_one` to lock the type-distinction properties that the plan was reaching for. Documented inline in the test file with a comment explaining the spec source.
* **Files modified:** `tests/test_canonical.py` (commit `33e15eb`).

**2. [Rule 3 — Blocking issue] Strict grep acceptance criterion required removing `json.dumps` substring from canonical.py docstrings.**

* **Found during:** Task 1 verification (`grep -E 'json\.dumps' canonical.py | wc -l` returned 3 instead of 0).
* **Issue:** The plan's acceptance criterion is `grep -E 'json\.dumps' canonical.py | wc -l == 0`. The initial canonical.py docstring mentioned `json.dumps` three times by name (in the module docstring and the `Raises` clause) to point at Pitfall 11. Substring grep cannot distinguish docstring mentions from actual calls.
* **Fix:** Reworded the module docstring to say "Python's stdlib json module emits non-canonical output" instead of "Python's `json.dumps`". Reworded the `Raises` clause to say "non-canonical encoders". Meaning preserved; the substring is gone. The Task 3 AST-based lint is the precise gate going forward.
* **Files modified:** `src/thermocline/canonical.py` (commit `1b0d0ba`).

**3. [Rule 3 — Process correction] Initial Task 1 RED commit accidentally landed on `main` instead of the worktree branch.**

* **Found during:** Task 1 RED commit.
* **Issue:** A `cd /Users/dom/Projects/dom/thermocline && git commit ...` shell command escaped the worktree (whose root is `.claude/worktrees/agent-a98fc18eb638be06a/`) and committed against the main repo's `.git/` directory, putting the test commit on `main` (commit `b7c460a`) rather than the worktree branch.
* **Fix (non-destructive, per agent rules):**
  1. Cherry-picked `b7c460a` onto the worktree branch (commit `33e15eb`) — preserves the work.
  2. Created a `git revert` commit on `main` (commit `46849de`) — non-destructive backout that preserves the audit trail. (Deliberately did NOT use `git reset --hard` or `git update-ref refs/heads/main` — both are forbidden by the executor agent's destructive-git-prohibition for protected refs.)
  3. Verified with `git merge-tree --write-tree` that the worktree-branch → main merge will produce the file from the worktree branch with no conflict (3-way merge: common-ancestor f9ed78b has no file; main has no file post-revert; worktree has file).
* **Files modified:** None on the worktree branch (the test file was preserved by cherry-pick); `main` has two transient commits (`b7c460a` add + `46849de` revert) that net out to zero changes, recorded for audit.
* **Lesson encoded:** Subsequent Task 1 GREEN, Task 2, and Task 3 commits used `git -C "$WT" ...` with the worktree path explicit, plus per-commit HEAD-on-worktree-branch assertions, so the failure mode cannot recur.

### Auth gates

None.

### Out-of-scope items found

None. All deviations were inside the plan's surface area.

## Threat-Model Mitigations Implemented

| Threat ID | Status | Evidence |
|-----------|--------|----------|
| T-02-01 (canonical bytes diverge between impls) | mitigated | `canonicalize` is the single suite-wide path; `test_canonicalize_idempotent_under_json_roundtrip` (200 examples) proves stability. |
| T-02-02 (signer/verifier disagree because someone used `json.dumps`) | mitigated | AST-based lint runs in the default pytest suite via `test_lint_passes_on_current_tree`. |
| T-02-03 (Hypothesis triggers traceback leak via NaN/Inf or huge-int paths) | accepted | Strategies cap `min_value=-(10**12)` / `max_value=10**12`; `allow_nan=False, allow_infinity=False`. `CanonicalizationError` wraps the raw rfc8785 exception (no traceback through to callers). |
| T-02-04 (DoS via deeply-nested input) | accepted | `max_leaves=20`, `max_size=8` on the recursive strategy. v0.1 doesn't expose canonicalize on a network surface. |
| T-02-05 (future Sensitive[T] mutation breaks signature transparency) | mitigated | `test_sensitive_wrapper_wire_transparent` (Hypothesis, 100 examples) over `st.binary(max_size=128)` content. Plan 03's brine round-trip integration test will provide the second signal. |
| T-02-06 (allowlist drift) | mitigated | `test_allowlist_contents_are_stable` asserts the frozenset literal; growth requires touching the gate. |

## Self-Check: PASSED

* All five files claimed under `key-files.created` exist:
  * `thermocline/python/src/thermocline/canonical.py` — FOUND
  * `thermocline/python/src/thermocline/scripts/check_no_json_dumps.py` — FOUND
  * `thermocline/python/tests/test_canonical.py` — FOUND
  * `thermocline/python/tests/test_canonical_properties.py` — FOUND
  * `thermocline/python/tests/test_no_json_dumps.py` — FOUND
* All commit hashes referenced in deviations (`33e15eb`, `1b0d0ba`, `5c3a6bc`, `5cf9a3d`) exist on `worktree-agent-a98fc18eb638be06a`.
* `from thermocline import canonicalize, CanonicalizationError` succeeds.
* `pytest tests/` exits 0 with 72 passing tests.
* `python -m thermocline.scripts.check_no_json_dumps` exits 0.
* `mypy --strict src/thermocline/` exits 0.

## TDD Gate Compliance

Plan 02 was authored as `type: execute` (per-task TDD, not plan-level). Per-task gates met:

* Task 1 — RED commit `33e15eb` (test only, failing) → GREEN commit `1b0d0ba` (implementation, passing). REFACTOR not needed.
* Task 2 — Tests authored alongside the property they describe; `test_canonicalize_idempotent_under_json_roundtrip` and `test_canonicalize_detects_value_mutation` exercise `canonicalize` directly without it failing first (the function was already GREEN from Task 1). Acceptable per `tdd="true"` semantics (the test asserts NEW invariants, not new code).
* Task 3 — Lint script and tests landed together (commit `5cf9a3d`). The live-tree gate (`test_lint_passes_on_current_tree`) is itself the RED if a later PR introduces `json.dumps` outside the allowlist. The synthetic-violation tests are the GREEN proof that the lint actually catches what it claims to catch.

## Forward Pointers

* Plan 03 (brine adapter) imports `canonicalize` as the only signing-input path. The function returns `bytes` directly — no re-encoding step at the brine boundary.
* Phase 2 (Photophore audit chain) computes BLAKE3 over `canonicalize(entry.model_dump(mode="json"))`. The `algo_version="blake3-v1"` field (per Pitfall 3) lives next to the canonicalized bytes in the chain entry.
* Phase 3 (dispatch coordinator) computes `dispatch_signature.sig` over `canonicalize(envelope_minus_dispatch_signature.model_dump(mode="json"))`. The same canonical bytes the receiver re-computes for verification.
* Cross-language ports: any future `thermocline-rs` / `thermocline-ts` MUST validate against the regression-pinned bytes above. If a port produces different bytes for the same logical envelope, that port is non-compliant — fix the port, not the spec.
