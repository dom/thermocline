---
phase: 01-thermocline-py-foundations
verified: 2026-05-09T05:30:00Z
status: pass
score: 5/5 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 3/5
  gaps_closed:
    - "BL-01: Cross-role verification (verifier-only role can verify foreign signatures without holding the signer's seed)"
    - "BL-02: Verifier.verify reads key_scheme from canonical nested location for real envelope shapes"
    - "BL-03: isinstance probe against keyring.backends.fail.Keyring / null.Keyring replaces broken substring heuristic"
    - "BL-04: BrineProvider.generate refuses clobber; rotate() is the explicit replacement path"
  gaps_remaining: []
  regressions: []
gaps: []
human_verification: []
---

# Phase 01: `thermocline-py` Foundations — Re-Verification Report

**Phase Goal:** Establish `thermocline-py` as the foundation library — envelope types, canonical JSON, IdentityProvider Protocol, brine reference adapter, JSON Schema artifacts.
**Verified:** 2026-05-09T05:30:00Z
**Status:** PASS — all five Phase 1 success criteria satisfied
**Re-verification:** Yes — after Plan 01-04 gap closure (3/5 → 5/5).

## Goal Achievement

### Observable Truths (the five Phase 1 success criteria)

| # | Truth (ROADMAP SC) | Status | Evidence |
|---|--------------------|--------|----------|
| SC1 | `pip install -e ./thermocline/python` succeeds; `import thermocline` exposes envelope types, `canonicalize`, `IdentityProvider`, brine adapter | VERIFIED (carried forward from prior report) | Package importable; `from thermocline import BrineProvider, Verifier, Receipt, KeyScheme, IdentityError, SchemeError, Signature` succeeds in re-verification harness. |
| SC2 | Round-trip via thermocline-py only — sign with brine, verify across roles — produces a Receipt; tampering invalidates | **VERIFIED (was FAILED — BL-01 + BL-02 closed)** | Independent harness: cross-role flow with separate signer / verifier `BrineProvider` instances. Signer holds seed for `alice` in `thermocline.signer` keystore namespace; verifier holds ONLY a `register_public_key`-registered verify key in `thermocline.verifier` namespace (`keyring.get_password('thermocline.verifier','alice') is None`). Real Task fixture from `thermocline/conformance/valid/task-pi-100-digits.json` round-trips through `Verifier.verify` with `dispatch_signature.key_scheme='brine'` and produces a `Receipt(envelope_id='a1b2c3d4-0000-4000-8000-000000000001', key_scheme=KeyScheme.BRINE)`. Tampering with `envelope_id` returns `None`. |
| SC3 | JSON Schema files exist; valid fixture validates; invalid fixture fails | VERIFIED (carried forward) | `uv run python -m thermocline.scripts.build_schemas --check` exits 0; conformance fixtures present under `thermocline/conformance/{valid,invalid}/` with full AT-C1..AT-C6 coverage. |
| SC4 | Brine adapter refuses to start if keystore unavailable; canonical-JSON Hypothesis stability test exists | **VERIFIED (was FAILED — BL-03 closed)** | Independent harness: both `keyring.backends.fail.Keyring()` and `keyring.backends.null.Keyring()` (real production classes, both `__name__=='Keyring'`) trigger `KeystoreUnavailableError(code='KEYSTORE_UNAVAILABLE')` via the `isinstance(backend, (_fail_backend.Keyring, _null_backend.Keyring))` probe at `identity.py:351`. Plus `NoKeyringError` path. Plus the in-memory backend is accepted (defends against over-rejection). |
| SC5 | `Receipt` constructible only via `verify` — runtime `TypeError` and `mypy --strict` fail on direct construction | VERIFIED (carried forward) | `_RECEIPT_TOKEN` sentinel pattern at `identity.py:96-138`; `mypy --strict` exits 0 on 11 source files; existing `test_identity_receipt_private.py` covers both gates. |

**Score:** 5/5 truths verified (was 3/5).

### Required Artifacts (BL-* closure focus)

| Artifact | Status | Details |
|----------|--------|---------|
| `thermocline/python/tests/conftest.py` (new) | VERIFIED | `_InMemoryKeyringBackend(KeyringBackend)` real subclass, class name deliberately not `Keyring`. `brine_in_memory_keyring` fixture installs via `keyring.set_keyring`, restores previous backend on teardown. |
| `thermocline/python/tests/test_identity_cross_role.py` (new) | VERIFIED | 6 tests including `test_verifier_only_role_verifies_foreign_signature` (BL-01 headline), `test_pubkey_store_is_consulted_before_seed` (W6 lookup-order invariant), `test_register_public_key_rejects_wrong_length`. |
| `thermocline/python/tests/test_identity_real_envelope.py` (new) | VERIFIED | 13 tests: 6 `_declared_scheme` exhaustive coverage over five envelope types, 3 fallback tests, real Task / TaskResult round-trip, AT-C4 behavioral wiring. |
| `thermocline/python/tests/test_identity_generate_idempotent.py` (new) | VERIFIED | 4 tests covering generate-clobber-refusal, rotate replacement, rotate refusal on missing identity, public-key preservation across rotate. |
| `thermocline/python/src/thermocline/identity.py` (modified) | VERIFIED | Contains `_PUBKEY_PREFIX='pubkey:'`, `register_public_key`, `Verifier._declared_scheme` staticmethod with type-routed lookup, `isinstance(backend, (_fail_backend.Keyring, _null_backend.Keyring))` probe, `generate` clobber check, `rotate` method. |
| `thermocline/python/tests/test_identity_keystore_required.py` (modified) | VERIFIED | Imports real `keyring.backends.fail` and `keyring.backends.null` (replaces synthetic `FailKeyring`/`NullKeyring` look-alikes). New `test_brine_accepts_in_memory_backend_that_is_not_fail_or_null` defends against over-rejection. |
| `thermocline/CHANGELOG.md` (modified) | VERIFIED | New `### Plan 01-04 gap closure (BL-01..BL-04)` subsection under existing `## v0.3.1` — all four BL bullets present with API references (`register_public_key`, `rotate`, `_PUBKEY_PREFIX`, `isinstance` probe). |

### Key Link Verification

| From | To | Via | Status |
|------|-----|-----|--------|
| `BrineProvider.public_key` | `python-keyring` | `_PUBKEY_PREFIX + identity` lookup FIRST, seed entry fallback | WIRED — verified by test `test_pubkey_store_is_consulted_before_seed` (returns registered foreign pub even when seed exists for same identity). |
| `Verifier._declared_scheme` | `envelope.py` envelope shapes | Routes `task`/`job` → `dispatch_signature.key_scheme`; `task_result`/`job_result` → `receipt_signature.key_scheme`; `task_error`/`job_error` → None; fallback to top-level for typeless / empty-block envelopes | WIRED — exhaustive test coverage over all five discriminator values plus three fallback paths. |
| `BrineProvider.__init__` | `keyring.backends.fail` / `keyring.backends.null` | `isinstance(backend, (_fail_backend.Keyring, _null_backend.Keyring))` | WIRED — independent harness fired both classes through the probe; both rejected with `KEYSTORE_UNAVAILABLE`. |
| `test_identity_real_envelope.py` | `thermocline/conformance/valid/task-pi-100-digits.json` | `_load_fixture` via `Path(__file__).resolve().parents[3]` | WIRED — harness loaded fixture from disk, reset `dispatch_signature.key_scheme='brine'`, completed round-trip producing Receipt with the fixture's actual `envelope_id`. |
| `test_identity_real_envelope.py` | `thermocline/conformance/invalid/AT-C4-key-scheme-mismatch.json` | Loads fixture, asserts `_signature_actual_scheme=='pgp'`, constructs `Signature(scheme=KeyScheme.PGP, ...)`, calls `Verifier.verify`, asserts `SchemeError(code='UNSUPPORTED_KEY_SCHEME')` | WIRED — AT-C4 is BEHAVIORAL (was structural-only in prior report). |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `BrineProvider.public_key` | `verify_key_bytes` | `keyring.get_password(_PUBKEY_PREFIX + identity)` then seed-derivation fallback | Yes — both paths produce 32-byte Ed25519 verify keys; corruption checks raise IdentityError | FLOWING |
| `Verifier.verify` | `declared` (key_scheme) | `_declared_scheme(envelope)` reads nested dict.get | Yes — exhaustive test coverage over real envelopes confirms scheme correctly extracted from nested location | FLOWING |
| `BrineProvider.sign` | `sig_bytes` | `signing_key.sign(canonical).signature` | Yes — 64 bytes Ed25519 over canonicalized JSON | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full test suite passes | `cd thermocline/python && uv run python -m pytest -q` | 142 passed in 2.96s, exit 0 | PASS |
| mypy --strict clean | `cd thermocline/python && uv run mypy --strict src/thermocline` | Success: no issues found in 11 source files, exit 0 | PASS |
| Schema drift check | `uv run python -m thermocline.scripts.build_schemas --check` | exit 0 | PASS |
| Canonical-JSON lint | `uv run python -m thermocline.scripts.check_no_json_dumps` | "no json.dumps found in library code outside allowlist", exit 0 | PASS |
| BL-01 cross-role round-trip (independent harness) | Custom python script — separate signer + verifier `BrineProvider`, register_public_key, sign, verify | `BL-01 OK: cross-role verification works without seed` + tamper detection returns None | PASS |
| BL-02 real Task envelope (independent harness) | Loads `conformance/valid/task-pi-100-digits.json`, sets nested key_scheme='brine', round-trips | `BL-02 OK: real Task envelope verified, envelope_id=a1b2c3d4-0000-4000-8000-000000000001` | PASS |
| BL-03 fail/null backend rejection (independent harness) | Patches `keyring.get_keyring` to return real `fail.Keyring()` / `null.Keyring()`, asserts `KEYSTORE_UNAVAILABLE` | `BL-03 OK: fail.Keyring rejected` + `BL-03 OK: null.Keyring rejected` | PASS |
| BL-04 generate/rotate (independent harness) | generate twice → `IDENTITY_ALREADY_EXISTS`; rotate replaces seed; rotate on missing → `IDENTITY_NOT_FOUND` | All three sub-checks `OK` | PASS |
| Skipped/xfailed tests | `pytest -v ... grep -E '(SKIPPED|XFAIL|XPASS|FAILED|ERROR)'` | No matches | PASS — no orphan tests |

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| THERMO-01 | Spec patch (`cirdan`→`thermocline`) + CHANGELOG | SATISFIED | `thermocline/CHANGELOG.md` v0.3.1 section + Plan 01-04 subsection. |
| THERMO-02 | JSON Schema artifacts under `thermocline/schema/` | SATISFIED | `build_schemas --check` exit 0 (carried forward). |
| THERMO-03 | Pydantic v2 envelope models, strict validation | SATISFIED | `envelope.py` (carried forward). |
| THERMO-04 | Single canonical-JSON path (`thermocline.canonical.canonicalize`) | SATISFIED | `check_no_json_dumps` exit 0 (carried forward). |
| THERMO-05 | `pyproject.toml` publishable, Pydantic v2 pinned, Python 3.11+ | SATISFIED | (carried forward; mypy --strict still clean). |
| THERMO-06 | Conformance fixtures under `thermocline/conformance/{valid,invalid}/` with AT-* annotations | SATISFIED + AT-C4 now wired BEHAVIORALLY (was structural-only) | `test_identity_real_envelope.test_at_c4_fixture_raises_scheme_error_through_verifier`. |
| THERMO-07 | `SUPPORTED_VERSIONS` includes `"0.3.1"`, rejects others with `UNSUPPORTED_VERSION` | SATISFIED | (carried forward). |
| IDENT-01 | `IdentityProvider` Protocol with locked methods | SATISFIED | `identity.py:147-178` (`@runtime_checkable Protocol`). |
| IDENT-02 | Brine adapter, never returns key material; cross-role works | **NEWLY SATISFIED via BL-01 closure** | `register_public_key` API; verifier-only role verifies without holding seed; `test_verifier_only_role_verifies_foreign_signature`. |
| IDENT-03 | Verifier dispatches on declared key_scheme; refuses mismatch | **NEWLY FULLY SATISFIED via BL-02 closure** | `Verifier._declared_scheme` reads canonical nested location for all five envelope types; AT-C4 behavioral test fires `SchemeError(code='UNSUPPORTED_KEY_SCHEME')`. |
| IDENT-04 | `Receipt` private constructor — no skipped-verify expressible | SATISFIED | `_RECEIPT_TOKEN` sentinel; `test_identity_receipt_private.py` (carried forward). |
| IDENT-05 | Adapter refuses to start without working keystore; no fallback | **NEWLY SATISFIED via BL-03 closure** | `isinstance` probe against real `fail.Keyring` / `null.Keyring`; static-lint test for filesystem-fallback absence; in-memory backend correctly accepted. |

All 12 phase requirements SATISFIED. Zero ORPHANED.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none in modified files) | — | TODO/FIXME/PLACEHOLDER scan | — | Clean — no new anti-patterns introduced by Plan 01-04. |

### Decision Coverage (D-01..D-04)

| Decision | Status | Evidence |
|----------|--------|----------|
| D-01 Receipt private constructor | INTACT | `_token: _ReceiptConstructorToken` parameter, sentinel check, mypy + runtime gates. |
| D-02 Schema generation pipeline | INTACT | `build_schemas --check` exit 0; schema artifacts present. |
| D-03 `Sensitive[T]` discipline | INTACT | (carried forward — not touched by Plan 01-04). |
| D-04 Conformance fixture structure | INTACT + AT-C4 wired behaviorally | Three-level YAML manifests; AT-C4 fixture loaded from disk and exercised through `Verifier.verify`. |

### Human Verification Required

None. All BL-* closures verified programmatically through independent harnesses that load real fixtures from disk and exercise the production lookup paths. Phase 1 has no UI / real-time / external-service surface.

### Gaps Summary

No gaps remain. The four blocking issues from the prior verification report (BL-01 cross-role verification structural impossibility; BL-02 nested-key_scheme lookup; BL-03 broken substring keystore probe; BL-04 silent generate clobber) have all been closed by Plan 01-04 with:

- Working production code (verified by `pytest`, `mypy --strict`, schema check, canonical-JSON lint, and four independent harness scripts run by this verifier);
- Behavioral regression tests that load real conformance fixtures from disk, closing the synthetic-test loophole that masked the original defects;
- Architectural invariants pinned by explicit tests (W6 lookup-order, defense-against-over-rejection, public-key preservation across rotate, etc.).

The phase goal is achieved. Phase 3 SC3 (cross-role round-trip Photophore → pi-forge) is structurally unblocked. Phase 2 may build on a brine adapter that natively supports the cross-role and clobber-safe contracts.

---

*Verified: 2026-05-09T05:30:00Z*
*Verifier: Claude (gsd-verifier) — re-verification after Plan 01-04 gap closure*
*Prior report: status=gaps_found, score=3/5 → this report: status=pass, score=5/5*
