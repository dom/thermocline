---
phase: 01-thermocline-py-foundations
plan: 03
subsystem: thermocline-py
tags:
  - identity
  - cryptography
  - conformance
  - changelog
  - phase-1
requires:
  - 01-01
  - 01-02
provides:
  - thermocline.IdentityProvider
  - thermocline.BrineProvider
  - thermocline.Verifier
  - thermocline.Signature
  - thermocline.Receipt
  - thermocline.KeystoreUnavailableError
  - thermocline/conformance/
  - thermocline/CHANGELOG.md
affects:
  - thermocline/python/src/thermocline/identity.py
  - thermocline/python/src/thermocline/__init__.py
  - thermocline/python/pyproject.toml
  - README.md
tech_stack_added:
  - PyNaCl (Ed25519 signing)
  - python-keyring (platform secure keystore)
  - PyYAML (conformance manifest parsing — dev only)
  - blake2b (Receipt.signature_hash, stdlib hashlib)
patterns:
  - "Module-private sentinel constructor for verify-only Receipt construction (D-01)"
  - "@runtime_checkable Protocol for cross-implementation duck-typing (IDENT-01)"
  - "Frozen dataclass + redacted __repr__ for cryptographic value types (Pitfall 4)"
  - "Three-level YAML manifest schema for cross-language conformance fixtures (D-04)"
key_files_created:
  - thermocline/python/src/thermocline/identity.py
  - thermocline/python/tests/test_identity.py
  - thermocline/python/tests/test_identity_dispatch.py
  - thermocline/python/tests/test_identity_receipt_private.py
  - thermocline/python/tests/test_identity_brine_roundtrip.py
  - thermocline/python/tests/test_identity_keystore_required.py
  - thermocline/python/tests/test_conformance_fixtures.py
  - thermocline/python/tests/fixtures/receipt_misuse.py
  - thermocline/conformance/MANIFEST.yaml
  - thermocline/conformance/valid/MANIFEST.yaml
  - thermocline/conformance/valid/task-pi-100-digits.json
  - thermocline/conformance/valid/task-result-pi-100-digits.json
  - thermocline/conformance/invalid/MANIFEST.yaml
  - thermocline/conformance/invalid/AT-C1-replayed-envelope.json
  - thermocline/conformance/invalid/AT-C2-tampered-signature.json
  - thermocline/conformance/invalid/AT-C3-leaky-shadow.json
  - thermocline/conformance/invalid/AT-C4-key-scheme-mismatch.json
  - thermocline/conformance/invalid/AT-C5-unsupported-version.json
  - thermocline/conformance/invalid/AT-C6-extra-field.json
  - thermocline/CHANGELOG.md
key_files_modified:
  - thermocline/python/src/thermocline/__init__.py
  - thermocline/python/pyproject.toml
  - README.md
  - .gitignore
decisions:
  - "Receipt.__init__ uses module-private sentinel _ReceiptConstructorToken with required _token parameter (no default) — locks D-01 at runtime AND under mypy --strict"
  - "BrineProvider keystore detection uses dual heuristic: catch NoKeyringError + check backend class name for 'fail'/'null' substrings; the optional set/delete probe (mentioned in plan as fallback) was not needed on macOS Keychain in this environment"
  - "signature_hash recipe is blake2b(canonical_bytes + signature.bytes_, digest_size=32).hex() — documented in BrineProvider.verify docstring and pinned by a known-good vector below"
  - "Conformance manifest schema includes a 'phase' field per fixture so future phases can find their work; AT-C1/C2/C3 are tagged phase: 2 (Photophore wires), AT-C4/C5/C6 wired in Phase 1"
  - "AT-C1/C2/C3/C4 fixtures are *fixture documents* (synthetic underscore-prefixed metadata fields documenting the surface) rather than bare Task envelopes — they're committed for Phase 2/3 to wire behaviorally; AT-C5/C6 are bare Task envelopes triggering the targeted Pydantic error"
  - "uv.lock added to .gitignore — dev-only artifact (CLAUDE.md mandates pip install for end users; uv for development)"
metrics:
  duration_minutes: 35
  tasks_completed: 3
  files_created: 21
  files_modified: 4
  tests_added: 25
  tests_passing: 117
  date_completed: 2026-05-08
---

# Phase 01 Plan 03: thermocline-py — Identity, brine adapter, conformance fixtures, spec changelog

**One-liner:** Locked the IdentityProvider Protocol, the verify-only `Receipt` invariant
(runtime + mypy --strict), the brine PyNaCl Ed25519 reference adapter with no-fallback
keystore enforcement, and the cross-language conformance fixture corpus with a
manifest schema future phases extend.

## What This Plan Delivered

- **Public identity primitives** under `thermocline.identity`:
  - `IdentityProvider` (`@runtime_checkable` `typing.Protocol`)
  - `BrineProvider` (Ed25519 + python-keyring reference adapter)
  - `Verifier` (multi-scheme dispatch on signature.scheme)
  - `Signature` (frozen value type, `__repr__` redacts raw bytes)
  - `Receipt` (frozen, sentinel-only construction)
  - `KeystoreUnavailableError`, `IdentityError`, `SchemeError` exceptions
- **Six AT-C conformance fixtures** plus one valid `(request, response)` pair under
  `thermocline/conformance/`, with three-level YAML manifests so any future
  language port can validate against the same corpus.
- **Spec patch tracking** in `thermocline/CHANGELOG.md` documenting eight v0.3.1
  patches discovered during Phase 1.
- **117 passing tests** (+25 from Plan 03), `mypy --strict` clean on `identity.py`,
  D-01 static gate exercising mypy in a subprocess and asserting non-zero exit.

## Tasks

### Task 1 — IdentityProvider Protocol + Receipt sentinel + Verifier dispatch

- Commit: `0688107` (TDD RED) → `0f0cca9` (TDD GREEN)
- Shipped `IdentityProvider`, `Signature`, `Receipt` (with sentinel-based `__init__`),
  `Verifier`, and a `BrineProvider` skeleton.
- Tests cover Protocol membership, signature redaction, runtime sentinel rejection,
  mypy --strict static rejection (subprocess), Verifier scheme-mismatch dispatch.

### Task 2 — Brine reference adapter (PyNaCl + python-keyring + IDENT-05 guard)

- Commit: `0f0cca9` (combined GREEN with Task 1)
- BrineProvider implements `generate` / `sign` / `verify` / `public_key` over PyNaCl
  Ed25519, calls `keyring.get_password` per signature (no in-process key cache),
  catches `NoKeyringError` and the fail/null backend class names at startup, and
  raises `KeystoreUnavailableError` rather than ever falling back.
- **Deviation (acknowledged in continuation prompt):** the dedicated test files
  `tests/test_identity_brine_roundtrip.py` and `tests/test_identity_keystore_required.py`
  named in the plan frontmatter were NOT committed by the Tasks 1-2 executor; the
  existing `test_identity.py` only covered Protocol shape and Signature redaction.
  IDENT-02 (real PyNaCl roundtrip + tamper) and IDENT-05 (keystore-unavailable
  refusal + filesystem-fallback static lint) were uncovered behaviorally. **Resolved
  in Task 3** by writing the two missing test files, with fourteen tests in total.

### Task 3 — Conformance fixtures + spec changelog (this commit)

- Commit: `3b584f2`
- `thermocline/conformance/MANIFEST.yaml` (top-level, schema_version 0.3.1, phases_covered).
- `thermocline/conformance/valid/MANIFEST.yaml` + `task-pi-100-digits.json` +
  `task-result-pi-100-digits.json`. Both fixtures parse via `Task.parse_strict` /
  `TaskResult.parse_strict` AND validate against `thermocline/schema/*.schema.json`.
- `thermocline/conformance/invalid/MANIFEST.yaml` listing all six AT-C surfaces with
  `surface`, `description`, `expect_error_code`, `phase`, `notes` per entry.
- Six AT-C JSON fixtures (one per surface). AT-C5 (unsupported version) and AT-C6
  (extra field) are bare Task envelopes whose targeted mutation triggers the matching
  Pydantic error path; AT-C1, AT-C2, AT-C3, AT-C4 are fixture documents documenting
  the surface for Phase 2/3 to wire behaviorally (each manifest entry's `phase`
  field flags this).
- `thermocline/python/tests/test_conformance_fixtures.py` — 11-test harness
  (manifest well-formedness, valid pair parses + JSON-Schema-validates, AT-C surface
  coverage, AT-C5 raises `UnsupportedVersionError`, AT-C6 raises Pydantic
  `extra_forbidden`, unwired surfaces are phase-tagged).
- `thermocline/python/tests/test_identity_brine_roundtrip.py` — 9 brine round-trip
  tests (folded in to fill the IDENT-02 coverage gap).
- `thermocline/python/tests/test_identity_keystore_required.py` — 5 keystore-required
  tests (folded in to fill the IDENT-05 coverage gap).
- `thermocline/python/pyproject.toml` — `pyyaml>=6.0` added to `[project.optional-dependencies] dev`.
- `thermocline/CHANGELOG.md` — eight v0.3.1 patches recorded (THERMO-01).
- `README.md` — single-line CHANGELOG link near the version banner (no spec body edits).
- `.gitignore` — `uv.lock` excluded (dev-only artifact).

## Critical Implementation Details (for future maintainers)

### Receipt `__init__` shipped signature

```python
def __init__(
    self,
    *,
    envelope_id: str,
    signature_hash: str,
    verified_at: datetime,
    key_scheme: KeyScheme,
    _token: _ReceiptConstructorToken,
) -> None: ...
```

- **All parameters keyword-only** (the leading `*`).
- **`_token` is required** (no default). External callers cannot type-check it
  because `_ReceiptConstructorToken` is module-private — `mypy --strict` rejects
  any direct construction without the token.
- **Runtime gate:** `if _token is not _RECEIPT_TOKEN: raise TypeError(...)`. Even
  passing a foreign object instance is rejected — identity check, not type check.
- **Frozen via `@dataclass(frozen=True, slots=True)`** with `object.__setattr__`
  inside `__init__` (the one acceptable use of that escape hatch in this codebase).

### BrineProvider keystore-availability heuristic

The adapter catches two signals at startup:

1. `NoKeyringError` raised by `keyring.get_keyring()` (rare; some envs raise this).
2. `type(backend).__name__` containing `"fail"` or `"null"` (the more common signal
   when no working backend is present — `keyring` returns `FailKeyring` or
   `NullKeyring` rather than raising).

The probe-write/probe-delete fallback the plan mentioned was not needed in this
environment (macOS Keychain is reliably present in development). If a future
platform needs the active probe, it should land as an additional check inside
`BrineProvider.__init__`, NOT as a fallback path — the no-fallback discipline is
enforced both behaviorally and by the static lint in
`tests/test_identity_keystore_required.py::test_brine_provider_source_has_no_filesystem_fallback`.

### Receipt `signature_hash` recipe + known-good vector

**Recipe:** `blake2b(canonical_bytes + signature.bytes_, digest_size=32).hex()`

**Known-good test vector** (for cross-language port alignment, T-03-07):

| Input | Value |
|---|---|
| envelope (Python dict) | `{"thermocline": "0.3.1", "type": "task", "envelope_id": "vector-001", "issuer": "alice", "key_scheme": "brine"}` |
| canonical bytes (RFC 8785 / JCS, hex) | `7b22656e76656c6f70655f6964223a22766563746f722d303031222c22697373756572223a22616c696365222c226b65795f736368656d65223a226272696e65222c22746865726d6f636c696e65223a22302e332e31222c2274797065223a227461736b227d` |
| canonical bytes (UTF-8 string) | `{"envelope_id":"vector-001","issuer":"alice","key_scheme":"brine","thermocline":"0.3.1","type":"task"}` |
| signature bytes (hex) | `000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f202122232425262728292a2b2c2d2e2f303132333435363738393a3b3c3d3e3f` |
| canonical bytes length | 102 |
| signature bytes length | 64 |
| **`signature_hash` (hex)** | **`717b801d381dce747879966928f6750509365aa8bdb89ebb041b51f76a77c3be`** |

This vector is reproducible via:

```python
import hashlib
from thermocline.canonical import canonicalize
canonical = canonicalize({
    "thermocline": "0.3.1", "type": "task",
    "envelope_id": "vector-001", "issuer": "alice", "key_scheme": "brine",
})
sig = bytes(range(64))
print(hashlib.blake2b(canonical + sig, digest_size=32).hexdigest())
```

Phase 4's conformance harness should pin this vector as a regression check.

## Spec Patches Recorded (THERMO-01)

The full list lives in `thermocline/CHANGELOG.md`. Discoveries during Plan 03:

1. `cirdan` → `thermocline` field rename (already shipped at thermocline@5c0d87c
   during the 0.3.0-draft RFC window — recorded for traceability).
2. `thermocline-py` registry entry — the in-tree Python package becomes the
   canonical reference implementation.
3. JSON Schema artifacts under `thermocline/schema/` (Draft 2020-12, drift-checked).
4. `Sensitive[T]` type-system discipline for `ContentBlock.content`.
5. **Receipt private-constructor invariant** — promoted to a spec patch carry-over
   because the spec README does not yet name the verify-only construction rule.
6. **Brine scheme keystore-only constraint** — promoted to a spec patch carry-over
   because the spec does not yet name the no-fallback property.
7. Conformance manifest schema (D-04) — three-level YAML, surface-keyed,
   phase-tagged.
8. `ErrorEnvelope` shape clarification — `pi-forge`'s `task_error` envelope shape
   shipped in the reference impl pending spec body promotion.

Promoting items 5, 6, and 8 into the spec README itself is a THERMO-01 carry-over
for the v0.3.1 spec body update.

## Counts

- **AT-C fixtures committed:** 6 (AT-C1 through AT-C6) ✓
- **Valid pairs committed:** 1 (pi-100-digits) ✓
- **Phase-1-wired conformance behavioral checks:** 2 (AT-C5 via `Task.parse_strict`,
  AT-C6 via Pydantic `extra_forbidden`); AT-C4 wired separately in
  `test_identity_dispatch.py::test_verifier_rejects_envelope_signature_scheme_mismatch`
- **Phase-1-structural-only conformance fixtures:** 3 (AT-C1, AT-C2, AT-C3 — wired
  in Phase 2 by Photophore audit log + dispatch coordinator)
- **Tests added by Plan 03 across all three tasks:** 25 (Task 1+2: 14;
  Task 3: 11 conformance + 9 brine roundtrip + 5 keystore = 25 net new test files'
  test count)
- **Tests passing total:** 117/117

## Acceptance Criteria

All Plan 01-03 acceptance criteria from PLAN.md verified:

- [x] `class IdentityProvider(Protocol)` AND `@runtime_checkable` in `identity.py`
- [x] `class Receipt` `frozen=True` AND `slots=True` (D-01)
- [x] `_RECEIPT_TOKEN` AND `_ReceiptConstructorToken` sentinel mechanism present
- [x] `class Verifier` AND `def register` AND `_providers` dict
- [x] `class Signature` AND redacted `__repr__`
- [x] `tests/fixtures/receipt_misuse.py` exists with direct `Receipt(`
- [x] `class BrineProvider` AND `import keyring` AND `import nacl.signing` (only in
      identity.py — verified by `test_brine_provider_imports_keyring_only_in_identity_module`)
- [x] `KeystoreUnavailableError` raised at startup when keystore absent (IDENT-05)
- [x] `canonicalize(envelope)` called on signing input (Pitfall 11)
- [x] No `os.environ` / `os.getenv` / `pathlib` / `open(` in identity.py source (IDENT-05)
- [x] `mypy --strict src/thermocline/identity.py` exits 0
- [x] `mypy --strict tests/fixtures/receipt_misuse.py` exits non-zero (D-01 static gate)
- [x] `from thermocline import (IdentityProvider, Verifier, Signature, Receipt, BrineProvider, KeystoreUnavailableError, IdentityError, SchemeError)` succeeds
- [x] `thermocline/conformance/MANIFEST.yaml` exists with `schema_version: "0.3.1"`
- [x] `thermocline/conformance/valid/MANIFEST.yaml` exists with `pairs:`
- [x] `thermocline/conformance/valid/task-pi-100-digits.json` exists and parses
- [x] `thermocline/conformance/valid/task-result-pi-100-digits.json` exists
- [x] `thermocline/conformance/invalid/MANIFEST.yaml` lists all six surfaces
- [x] All six AT-C JSON fixtures exist (`ls AT-C*.json | wc -l == 6`)
- [x] Each AT-C fixture parses as JSON (covered by harness)
- [x] `thermocline/CHANGELOG.md` contains `0.3.1`, `THERMO-01`, `5c0d87c`
- [x] `pyproject.toml` contains `pyyaml`
- [x] `pytest tests/test_conformance_fixtures.py -x` exits 0

## Deviations from Plan

### [Rule 2 — Missing critical functionality] IDENT-02 / IDENT-05 behavioral test gap

**Found during:** Task 3 readiness review (continuation context).

**Issue:** The Tasks 1-2 executor committed `tests/test_identity.py`,
`tests/test_identity_dispatch.py`, `tests/test_identity_receipt_private.py`, and
`tests/fixtures/receipt_misuse.py` covering Protocol shape + dispatch + D-01, but
did NOT commit the dedicated `tests/test_identity_brine_roundtrip.py` and
`tests/test_identity_keystore_required.py` files named in the plan frontmatter.
This left IDENT-02 (real PyNaCl Ed25519 round-trip + tamper detection +
canonical-input check + no-key-leaking-method-name check) and IDENT-05
(`KeystoreUnavailableError` on no-keyring + fail/null backend + filesystem-fallback
static lint + keyring-imports-only-in-identity static lint) uncovered behaviorally.
The implementation in `identity.py` was correct; the tests proving it were absent.

**Fix:** Folded both test files into Task 3 with fourteen total tests covering
every IDENT-02 and IDENT-05 behavior listed in the plan's `<behavior>` section.
The continuation prompt explicitly authorized this resolution.

**Files added:**
- `thermocline/python/tests/test_identity_brine_roundtrip.py` (9 tests)
- `thermocline/python/tests/test_identity_keystore_required.py` (5 tests)

**Commit:** `3b584f2`

### [Rule 2 — Missing critical functionality] uv.lock not in .gitignore

**Found during:** Pre-commit `git status` review for Task 3.

**Issue:** Running `uv pip install -e .[dev]` created `thermocline/python/uv.lock`,
which appeared as untracked. The CLAUDE.md tech-stack guidance says **uv for
development, `pip install` for end users** — i.e., the lock file is a dev-only
artifact and should not ship to PyPI or be committed.

**Fix:** Added `uv.lock` to the project-root `.gitignore` with a comment pointing
back to the CLAUDE.md guidance. No code change.

**Commit:** `3b584f2`

### Other deviations

None. The plan executed as written modulo the IDENT-02/05 gap noted above.

## TDD Gate Compliance

This plan is `type: execute` (not plan-level `type: tdd`), but Tasks 1 and 2 carried
`tdd="true"`. Verified in the git log:

- Task 1 RED gate: `0688107 test(01-03): add failing tests for IdentityProvider Protocol + Receipt sentinel + Verifier dispatch (TDD RED)` ✓
- Task 1+2 GREEN gate: `0f0cca9 feat(01-03): implement IdentityProvider Protocol + Receipt sentinel + Verifier + brine adapter (TDD GREEN)` ✓
- Task 3: `feat` (not TDD-gated per plan) ✓

## Verification Run

```
$ cd thermocline/python && uv run python -m pytest -q
117 passed in 3.18s

$ uv run python -m mypy --strict src/thermocline/identity.py
Success: no issues found in 1 source file
```

## Public API Surface (locked)

```python
from thermocline import (
    # Envelope shapes (from Plan 01)
    Task, TaskResult, Job, JobResult, ErrorEnvelope, ContentBlock,
    # Privacy primitive (Plan 01)
    Sensitive,
    # Key-scheme enum (Plan 01)
    KeyScheme,
    # Version registry (Plan 01)
    SUPPORTED_VERSIONS,
    # Canonical JSON (Plan 02)
    canonicalize,
    # Identity primitives (Plan 03 — this plan)
    IdentityProvider, BrineProvider, Verifier, Signature, Receipt,
    # Exceptions (Plan 01 + Plan 03)
    EnvelopeError, UnsupportedVersionError, CanonicalizationError,
    IdentityError, SchemeError, KeystoreUnavailableError,
)
```

Phase 2 imports this surface and proceeds without restructuring it.

## Self-Check

## Self-Check: PASSED

All 22 created/modified files present; all 3 plan-relevant commits present in git log:

- 0688107 (Task 1 RED)
- 0f0cca9 (Tasks 1+2 GREEN)
- 3b584f2 (Task 3)
