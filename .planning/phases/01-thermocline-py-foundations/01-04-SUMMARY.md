---
phase: 01-thermocline-py-foundations
plan: 04
subsystem: identity
tags: [ed25519, brine, keyring, pynacl, identity-provider, verifier, gap-closure]

# Dependency graph
requires:
  - phase: 01-thermocline-py-foundations
    provides: BrineProvider, Verifier, IdentityProvider, conformance fixtures, _minimal_envelope-style flat-dict tests
provides:
  - Cross-role verification (verifier-only role can verify foreign signatures without holding the signer's seed) — BL-01 / IDENT-02
  - Verifier honors the canonical nested location for key_scheme on real Task / TaskResult / Job / JobResult / ErrorEnvelope shapes — BL-02 / IDENT-03 (AT-C4 wired behaviorally)
  - isinstance-based keystore probe rejecting real keyring.backends.fail.Keyring / null.Keyring — BL-03 / IDENT-05 enforced in production
  - Clobber-safe BrineProvider.generate() + explicit BrineProvider.rotate() — BL-04 (data-loss path closed)
  - Shared brine_in_memory_keyring pytest fixture (real KeyringBackend subclass) for BL-* closure tests
affects: [01-thermocline-py-foundations verification, photophore policy-engine dispatch path, seamount/pi-forge brine upgrade, Phase 3 cross-role round-trip integration]

# Tech tracking
tech-stack:
  added: []  # No new third-party deps
  patterns:
    - "Public-key-store-first lookup with seed-store fallback in IdentityProvider.public_key()"
    - "register_public_key API as the only documented path by which a verifier-only role acquires foreign identity material"
    - "@staticmethod _declared_scheme(envelope) — type-routed lookup table over all five envelope discriminator values, with documented top-level fallback for synthetic flat-dict tests"
    - "isinstance probe against keyring.backends.fail.Keyring / null.Keyring — direct class identity, never substring on __name__"
    - "generate() refuses to clobber; rotate() is the only documented seed-replacement path"
    - "Real-conformance-fixture round-trip tests load JSON from disk (Path.resolve().parents[3]) — closes the synthetic-test loophole that masked BL-* defects"

key-files:
  created:
    - thermocline/python/tests/conftest.py
    - thermocline/python/tests/test_identity_cross_role.py
    - thermocline/python/tests/test_identity_real_envelope.py
    - thermocline/python/tests/test_identity_generate_idempotent.py
  modified:
    - thermocline/python/src/thermocline/identity.py
    - thermocline/python/tests/test_identity_keystore_required.py
    - thermocline/python/tests/test_identity_dispatch.py
    - thermocline/CHANGELOG.md

key-decisions:
  - "Public-key entries live in the SAME keystore service as seed entries but under the _PUBKEY_PREFIX = 'pubkey:' namespace; lookup order is load-bearing (public-key store first)."
  - "Verifier._declared_scheme is @staticmethod with an exhaustive type-routed lookup table; documented top-level fallback preserves the existing _minimal_envelope tests so this gap-closure ships zero existing-test churn."
  - "AT-C4 wired with a Signature(scheme=KeyScheme.PGP, ...) — the fixture's _signature_actual_scheme metadata is 'pgp', so the mismatch path actually fires (B4 correction over the original draft, which used KeyScheme.BRINE and would have passed for the wrong reason)."
  - "rotate() does NOT touch the public-key store entry for the same identity; the seed-vs-public-key orthogonality is the BL-01 lookup-order invariant pinned by an explicit test."

patterns-established:
  - "Thermocline cryptographic adapters: ALWAYS test with the real production keyring.backends.fail.Keyring / null.Keyring classes (not hand-rolled look-alikes). Both production classes are named 'Keyring'; substring heuristics on __name__ silently fail open."
  - "Thermocline behavioral verification: ALWAYS load real conformance fixtures from disk in regression tests. Synthetic flat-dict envelopes mask production lookup-path bugs."

requirements-completed: [IDENT-02, IDENT-03, IDENT-05]

# Metrics
duration: 12min
completed: 2026-05-09
---

# Phase 01 Plan 04: BL-01..BL-04 Gap Closure Summary

**Cross-role verification, nested key_scheme lookup, real-class keystore probe, and clobber-safe key generation — closing all four BL-* gaps from the Phase 1 verification report (3/5 → 5/5 must-haves verified).**

## Performance

- **Duration:** ~12 min (722 seconds)
- **Started:** 2026-05-09T04:51:21Z
- **Completed:** 2026-05-09T05:03:23Z
- **Tasks:** 6
- **Files modified:** 8 (4 new, 4 edited)

## Accomplishments

- **BL-01 (cross-role verification):** A `BrineProvider` whose keystore holds ONLY a registered public key for an identity can `verify` signatures produced by a different `BrineProvider` instance whose keystore holds the seed for that identity — Phase 3 SC3 (cross-role round-trip Photophore → pi-forge) is now structurally possible.
- **BL-02 (real envelope round-trip):** `Verifier.verify` reads the declared `key_scheme` from the canonical nested location (`dispatch_signature.key_scheme` for `task`/`job`; `receipt_signature.key_scheme` for `task_result`/`job_result`; `None` for `task_error`/`job_error`). Real Task/TaskResult envelopes from `thermocline/conformance/valid/` round-trip and produce a `Receipt`. AT-C4 is wired behaviorally — the test loads the fixture from disk and constructs a `Signature(scheme=KeyScheme.PGP, ...)` so the declared `'brine'` mismatches the actual `'pgp'`, exactly the surface AT-C4 tests.
- **BL-03 (real-class keystore probe):** `BrineProvider.__init__` rejects `keyring.backends.fail.Keyring` / `keyring.backends.null.Keyring` via `isinstance` against the imported classes — both production classes are named `'Keyring'`, so the previous substring heuristic on `type(backend).__name__` silently failed open. IDENT-05 is enforced in production now.
- **BL-04 (no silent seed clobber):** `generate()` refuses to overwrite an existing seed (raises `IDENTITY_ALREADY_EXISTS`); new `rotate()` is the only documented replacement path. Re-running a setup script no longer destroys the prior signing identity.
- **Test discipline:** new behavioral regression tests load real conformance fixtures from disk, closing the synthetic-test loophole that masked all four BL-* defects.

## Task Commits

Each task was committed atomically; all six commits are on `main`:

1. **Task 1: shared `brine_in_memory_keyring` fixture in `tests/conftest.py`** — `50c2539` (test)
2. **Task 2 (BL-01): separate public-key store + `register_public_key` API** — `f79bc4a` (feat)
3. **Task 3 (BL-02): `Verifier._declared_scheme` reads nested location** — `1788fa2` (feat)
4. **Task 4 (BL-03): `isinstance` probe replaces substring heuristic** — `56f693b` (fix)
5. **Task 5 (BL-04): `generate` refuses clobber, add `rotate()`** — `4fb3938` (feat)
6. **Task 6: CHANGELOG.md records the four BL-\* fixes** — `c0f7631` (docs)

## Files Created/Modified

**Created:**
- `thermocline/python/tests/conftest.py` — shared `brine_in_memory_keyring` fixture wrapping a real `KeyringBackend` subclass (`_InMemoryKeyringBackend`); coexists intentionally with the pre-existing `MagicMock`-based `fake_keyring` fixture in `test_identity_brine_roundtrip.py`.
- `thermocline/python/tests/test_identity_cross_role.py` — six BL-01 tests including the headline cross-role round-trip and the W6 lookup-order invariant pin (`test_pubkey_store_is_consulted_before_seed`).
- `thermocline/python/tests/test_identity_real_envelope.py` — thirteen tests: six `_declared_scheme` tests over all five envelope discriminator values, three fallback tests, three real-envelope round-trip tests (Task / TaskResult / AT-C4), one synthetic-flat-dict test.
- `thermocline/python/tests/test_identity_generate_idempotent.py` — four BL-04 tests including `test_rotate_preserves_registered_public_key_for_same_identity` which depends on the W6 invariant from Task 2.

**Modified:**
- `thermocline/python/src/thermocline/identity.py` — `_PUBKEY_PREFIX` constant; `register_public_key()`; `public_key()` lookup-order rewrite; `Verifier._declared_scheme()` staticmethod + delegation from `Verifier.verify()`; `_fail_backend` / `_null_backend` imports + `isinstance` probe; `generate()` clobber check; new `rotate()`.
- `thermocline/python/tests/test_identity_keystore_required.py` — synthetic `FailKeyring` / `NullKeyring` classes replaced with imports of the real `keyring.backends.fail.Keyring` / `keyring.backends.null.Keyring`; new `test_brine_accepts_in_memory_backend_that_is_not_fail_or_null` defends against over-rejection.
- `thermocline/python/tests/test_identity_dispatch.py` — import updated to include `IdentityError`; new `test_dispatch_falls_back_to_top_level_for_typeless_envelope` regression test.
- `thermocline/CHANGELOG.md` — `Plan 01-04 gap closure (BL-01..BL-04)` subsection appended under existing `## v0.3.1` heading.

## Decisions Made

- **Lookup-order invariant is load-bearing**: when a node holds BOTH a registered public key AND a seed for the same identity, `public_key()` returns the registered foreign public key. This is the W6 invariant and it is what makes Task 5's `test_rotate_preserves_registered_public_key_for_same_identity` pass — `rotate()` replaces the seed but the public-key entry is independent.
- **Top-level `key_scheme` fallback is preserved as the single sanctioned deviation** from the spec's nested layout. Without this, the existing `test_identity_brine_roundtrip._minimal_envelope` tests (whose envelopes carry `type='task'` + top-level `key_scheme='brine'` but NO `dispatch_signature` block) would fail. The fallback is documented in `_declared_scheme`'s docstring and exercised by an explicit B1 test.
- **AT-C4 wired with `KeyScheme.PGP`, not `KeyScheme.BRINE`** (B4 correction over original draft): the fixture's `_signature_actual_scheme` metadata is `'pgp'`, so the test must construct a `Signature(scheme=KeyScheme.PGP, ...)` for the `declared='brine' != actual='pgp'` mismatch path to fire. The original draft used `KeyScheme.BRINE` and would have hit the no-provider-registered branch instead.
- **Task 2 cross-role envelope carries dual-form `key_scheme`** (top-level + nested) so it survives the OLD top-level `Verifier.verify` lookup at Task 2 land-time. After Task 3 lands, both forms continue to work via the new `_declared_scheme` fallback. Same envelope passes under both code paths — zero churn after Task 3.

## Deviations from Plan

### Documentation Reconciliation

**1. [Rule 1 - Spec Drift] CHANGELOG W10 acceptance check is contradictory with the file's actual heading structure**
- **Found during:** Task 6 (CHANGELOG update)
- **Issue:** The plan's W10 closure check requires `grep -c '^### 0.3.1' thermocline/CHANGELOG.md` to return `1`, but the existing CHANGELOG uses a level-2 `## v0.3.1` heading (not `### 0.3.1`). The plan also explicitly says "Do NOT add a new heading" when appending bullets. The two requirements cannot both be literally satisfied.
- **Fix:** Honored the load-bearing intent ("no DUPLICATE 0.3.1 heading") and the literal "do NOT add a new heading" instruction. Appended the four BL-* bullets under the existing `## v0.3.1` section as a new `### Plan 01-04 gap closure (BL-01..BL-04)` subsection (so the entries are clearly attributable to this gap-closure pass without duplicating any existing top-level heading). The level-2 `## v0.3.1` heading remains the single section header for v0.3.1.
- **Files modified:** `thermocline/CHANGELOG.md`
- **Verification:** `grep -c '^## v0.3.1' thermocline/CHANGELOG.md` returns `1` (single v0.3.1 section header — no duplicate). All BL-01/BL-02/BL-03/BL-04 bullets present; `register_public_key`, `rotate`, and `01-VERIFICATION.md` all referenced. The literal `^### 0.3.1` grep returns 0 (the file's heading style is `## v0.3.1`, not `### 0.3.1`).
- **Committed in:** `c0f7631` (Task 6 commit)

**2. [Rule 1 - Bug] mypy `--strict` flagged unused `# type: ignore[no-any-return]` and `Returning Any` errors in `_declared_scheme`**
- **Found during:** Task 3 (BL-02 implementation)
- **Issue:** The plan's pseudo-diff for `_declared_scheme` returned `block.get("key_scheme")` and `envelope.get("key_scheme")` directly. Because the envelope is typed `dict[str, Any]`, `dict.get()` returns `Any`, which mypy `--strict` rejects when the function declares `-> str | None`. The plan's `# type: ignore[no-any-return]` placements were partly unused (mypy could narrow some paths) and partly missing where the casts were actually needed.
- **Fix:** Removed all `# type: ignore[no-any-return]` comments and added explicit `str(scheme)` / `str(top) if top is not None else None` casts at the four return sites. Behaviorally identical (the values are always strings or None at runtime — `key_scheme` is a JSON string), but mypy is satisfied.
- **Files modified:** `thermocline/python/src/thermocline/identity.py`
- **Verification:** `uv run mypy --strict src/thermocline` exits 0; full pytest still passes.
- **Committed in:** `1788fa2` (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (1 documentation reconciliation, 1 typing bug)
**Impact on plan:** Both deviations are mechanical reconciliations, not scope creep. The CHANGELOG fix preserves the load-bearing intent (no duplicate heading). The mypy fix preserves runtime behavior identically. No must-have truth was weakened, no test was relaxed.

## Issues Encountered

None — all tasks landed cleanly in plan order and the four BL-* closure proofs (manual REPL scripts from the plan's `<verification>` block) all printed `OK`.

## Self-Check

### Files exist
- `thermocline/python/tests/conftest.py` — FOUND
- `thermocline/python/tests/test_identity_cross_role.py` — FOUND
- `thermocline/python/tests/test_identity_real_envelope.py` — FOUND
- `thermocline/python/tests/test_identity_generate_idempotent.py` — FOUND
- `thermocline/python/src/thermocline/identity.py` — FOUND (modified)
- `thermocline/python/tests/test_identity_keystore_required.py` — FOUND (modified)
- `thermocline/python/tests/test_identity_dispatch.py` — FOUND (modified)
- `thermocline/CHANGELOG.md` — FOUND (modified)
- `.planning/phases/01-thermocline-py-foundations/01-04-SUMMARY.md` — FOUND (this file)

### Commits exist
- `50c2539` (Task 1) — FOUND
- `f79bc4a` (Task 2 BL-01) — FOUND
- `1788fa2` (Task 3 BL-02) — FOUND
- `56f693b` (Task 4 BL-03) — FOUND
- `4fb3938` (Task 5 BL-04) — FOUND
- `c0f7631` (Task 6 CHANGELOG) — FOUND

### Verification gates
- `uv run python -m pytest -q` (cd thermocline/python) — exits 0; **142 tests pass** (117 prior + 6 cross-role + 13 real_envelope + 1 dispatch + 1 keystore + 4 generate-idempotent = 142)
- `uv run mypy --strict src/thermocline` (cd thermocline/python) — exits 0; no issues found in 11 source files
- `uv run python -m thermocline.scripts.build_schemas --check` — exits 0
- `uv run python -m thermocline.scripts.check_no_json_dumps` — exits 0; "no json.dumps found in library code outside allowlist"
- BL-01 closure proof script — printed `BL-01 OK`
- BL-02 closure proof script (with Path.resolve walk-up to repo root) — printed `BL-02 OK`
- BL-03 closure proof script (real fail.Keyring + null.Keyring) — printed `BL-03 OK`
- BL-04 closure proof script (generate clobber-refusal + rotate replacement) — printed `BL-04 OK`

## Self-Check: PASSED

## TDD Gate Compliance

This plan is `type: execute` (not `type: tdd`), but four of six tasks (Tasks 2-5) carry `tdd="true"` in the plan source. For each, the test-first discipline was followed in spirit (read `<behavior>` first, then implement, then verify) but commits were made in the GREEN+REFACTOR style (one commit per task with both source change and tests landed together) rather than separate RED/GREEN commits. The plan's verification gates (each task's `<acceptance_criteria>` includes the new tests passing AND the full suite remaining regression-clean) were all met for every task.

## Next Phase Readiness

- **Phase 1 SC2 (round-trip via thermocline-py only):** UNBLOCKED. Real Task and TaskResult envelopes round-trip through `Verifier.verify` and produce a Receipt.
- **Phase 1 SC4 (keystore refusal):** UNBLOCKED. The brine adapter rejects real `keyring.backends.fail.Keyring` / `null.Keyring` at startup.
- **Phase 3 SC3 (cross-role round-trip Photophore → pi-forge):** UNBLOCKED. A verifier-only `BrineProvider` instance can verify signatures produced by a separate signer-role instance via the `register_public_key` API.
- **Re-verification:** ready for `/gsd-verify-phase 1` to regenerate the verification report; expected outcome `status: pass`, `score: 5/5 must-haves verified`, `gaps: []`.
- **Phase 2 (Photophore foundations):** can now build on a brine adapter that supports cross-role verification natively, instead of working around the verifier-needs-the-seed defect.

---
*Phase: 01-thermocline-py-foundations*
*Plan: 04 (gap closure for BL-01..BL-04)*
*Completed: 2026-05-09*
