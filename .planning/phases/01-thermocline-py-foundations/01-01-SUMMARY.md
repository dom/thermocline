---
phase: 01-thermocline-py-foundations
plan: 01
subsystem: thermocline-py
tags: [thermocline, library, pydantic, envelope, schema, sensitive, foundations]
dependency-graph:
  requires:
    - "Python 3.11+ runtime"
    - "Pydantic v2 (>=2.7,<3.0)"
    - "Existing pi-forge envelope reference (../seamount/pi-forge/envelope.py — read-only)"
    - "Thermocline spec README.md envelope schemas (§ Schema)"
  provides:
    - "thermocline.Task / TaskResult / Job / JobResult / ErrorEnvelope / ContentBlock — Pydantic v2 envelope models"
    - "thermocline.Sensitive[T] — redacting wrapper for privacy-sensitive content (D-03)"
    - "thermocline.KeyScheme — StrEnum (BRINE / PGP / X509 / NONE) for verifier dispatch"
    - "thermocline.SUPPORTED_VERSIONS = frozenset({0.3.0, 0.3.1}) (THERMO-07)"
    - "thermocline.EnvelopeError + typed subclasses with stable code strings"
    - "thermocline-build-schemas console script with --write / --check modes (D-02)"
    - "thermocline/schema/{task,task_result,job,job_result,error}.schema.json — Draft 2020-12 artifacts"
  affects:
    - "Phase 2 — Photophore imports envelope models, KeyScheme, Sensitive, EnvelopeError from this package."
    - "Phase 3 — Plan 02 (canonical JSON) extends sensitive.py + envelope.py; Plan 03 (IdentityProvider) imports KeyScheme + IdentityError."
    - "Phase 3 — pi-forge upgrade replaces in-tree envelope.py with `from thermocline import ...`."
    - "Phase 3 — describe-forge built directly against thermocline-py."
tech-stack:
  added:
    - "hatchling (build backend)"
    - "pydantic 2.7+ (envelope models)"
    - "pynacl 1.5+ (declared; signing lands Plan 03)"
    - "rfc8785 (declared; canonical JSON ships Plan 02)"
    - "jsonschema 4+ (schema validator in tests)"
    - "keyring 25+ (declared; identity adapter ships Plan 03)"
    - "pytest 8 / pytest-asyncio / hypothesis / mypy 1.10 / ruff 0.5 / pip-audit (dev)"
  patterns:
    - "src layout (src/thermocline/)"
    - "Pydantic v2 ConfigDict(extra='forbid', frozen=True) — strict + immutable models"
    - "Pydantic v2 __get_pydantic_core_schema__ + __get_pydantic_json_schema__ on Sensitive[T]"
    - "field_validator that catches typed exception, re-raises as ValueError so Pydantic wraps cleanly; parse_strict() classmethods recover the typed exception"
    - "generate-and-commit JSON Schema with CI drift check (D-02) — same pattern as protobuf/OpenAPI"
    - "PEP 561 py.typed marker"
key-files:
  created:
    - "thermocline/python/pyproject.toml"
    - "thermocline/python/README.md"
    - "thermocline/python/src/thermocline/__init__.py"
    - "thermocline/python/src/thermocline/version.py"
    - "thermocline/python/src/thermocline/errors.py"
    - "thermocline/python/src/thermocline/schemes.py"
    - "thermocline/python/src/thermocline/sensitive.py"
    - "thermocline/python/src/thermocline/envelope.py"
    - "thermocline/python/src/thermocline/py.typed"
    - "thermocline/python/src/thermocline/scripts/__init__.py"
    - "thermocline/python/src/thermocline/scripts/build_schemas.py"
    - "thermocline/python/tests/__init__.py"
    - "thermocline/python/tests/test_sensitive.py"
    - "thermocline/python/tests/test_envelope.py"
    - "thermocline/python/tests/test_schema_drift.py"
    - "thermocline/schema/task.schema.json"
    - "thermocline/schema/task_result.schema.json"
    - "thermocline/schema/job.schema.json"
    - "thermocline/schema/job_result.schema.json"
    - "thermocline/schema/error.schema.json"
    - ".gitignore"
  modified: []
decisions:
  - "Pydantic v2 envelope field for the spec's `\"thermocline\": \"<version>\"` JSON key is named `thermocline` on the Python side too (matches the wire field; no alias indirection). This mirrors pi-forge/envelope.py and the spec's JSON examples."
  - "Field validator raises ValueError chain on UnsupportedVersionError so Pydantic v2 wraps cleanly; parse_strict() classmethods walk the ValidationError chain and re-raise the typed exception (THERMO-07). Direct model_validate() callers see ValidationError; forge handlers / conformance tests use parse_strict() for the typed surface."
  - "Internal sub-objects (_Shadow, _TaskBlock, _ResultPolicy, _DispatchSignature, _ReceiptSignature, _Provenance, _Manifest, _JobOutputContract, _JobConstraints, _StepInput, _Step, _JobArtifact, _ErrorBody) carry a single underscore prefix and are intentionally NOT in __all__. Downstream consumers go through the top-level envelope shapes."
  - "ErrorEnvelope.type accepts {task_error, job_error} (matches pi-forge's existing `task_error` shape; the spec README does not yet formalize an error envelope — flagged as a THERMO-01 carry-over to Plan 03 / spec patch tracking)."
  - "Console-script entry point (`thermocline-build-schemas`) is the primary surface for the schema generator; `python -m thermocline.scripts.build_schemas` is the equivalent module entry. Both are documented in pyproject and in build_schemas's docstring."
  - "Sensitive[T] gained a JSON-Schema hook (`__get_pydantic_json_schema__`) so `model_json_schema()` can render Sensitive[bytes] fields. The wire format remains base64 ASCII string. This was a Task 3 deviation (Rule 3) — Pydantic raises PydanticInvalidForJsonSchema for plain validator functions without the hook."
  - "Schema $id chosen as `https://thermocline.spec/schema/v0.3.1/<envelope>.schema.json` per CONTEXT.md D-02. Domain not served at v0.1; stable for future hosting and for cross-language $ref resolution (TS / Rust ports)."
  - "SCHEMA_DIR resolves via `Path(__file__).resolve().parents[4] / 'schema'` from src/thermocline/scripts/build_schemas.py (parents[0]=scripts, [1]=thermocline, [2]=src, [3]=python, [4]=thermocline/ — the spec repo root). Validated end-to-end by --write / --check / drift simulation."
metrics:
  duration: "≈22 minutes from first task commit to summary"
  completed: "2026-05-08"
  tests: "39 passing across 3 files (14 sensitive + 18 envelope + 7 drift)"
  source-loc: "1667 total (8 src .py + 4 tests/scripts .py + pyproject + README)"
  schemas-generated: 5
---

# Phase 1 Plan 01: thermocline-py Foundations Summary

Stand up the `thermocline-py` shared library with the privacy-discipline type system in place from day 1 — Pydantic v2 envelope models for every Thermocline shape, the `Sensitive[T]` redacting wrapper (D-03), the `KeyScheme` enum, `SUPPORTED_VERSIONS`/`UnsupportedVersionError` (THERMO-07), and a generate-and-commit JSON Schema pipeline with a CI drift check (D-02).

## What Shipped

### Public API surface (locked)

The downstream-stable import line — Photophore (Phase 2), Plan 02 (canonical JSON), Plan 03 (IdentityProvider), and Phase 3's pi-forge / describe-forge upgrades all import from this surface:

```python
from thermocline import (
    Task, TaskResult, Job, JobResult, ErrorEnvelope, ContentBlock,
    Sensitive, KeyScheme, SUPPORTED_VERSIONS, EnvelopeError,
)
```

Plus the typed exception subclasses (`UnsupportedVersionError`, `CanonicalizationError`, `IdentityError`, `SchemeError`, `KeystoreUnavailableError`) and the `validate_version` helper.

### Envelope models

Pydantic v2 `BaseModel` subclasses, each with `ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)` — extra fields raise `ValidationError`, models are immutable post-construction, `Sensitive[bytes]` content is type-system-enforced at the boundary:

- `Task` — `type: "task"` request envelope with `task` block + `context: list[ContentBlock]`.
- `TaskResult` — `type: "task_result"` response with `outputs` + `provenance` + `receipt_signature`.
- `Job` — `type: "job"` multi-step manifest envelope (v0.1 ships the type only; full job-handling is v0.2).
- `JobResult` — `type: "job_result"` with `status`, optional `artifact`, `provenance`, `receipt_signature`.
- `ErrorEnvelope` — `type: "task_error"|"job_error"` with nested `error.code` + `error.message`. Mirrors pi-forge's existing `task_error` wire shape.
- `ContentBlock` — context entry with `content: Sensitive[bytes] | None` (D-03) or `shadow: _Shadow | None` (Photophore-generated; thermocline-py round-trips).

Each envelope class exposes a `parse_strict(payload: dict)` classmethod that re-raises the wrapped `UnsupportedVersionError` directly (THERMO-07) so callers can match on the typed exception rather than parsing Pydantic error structures.

### Sensitive[T] redaction wrapper (D-03)

`thermocline.sensitive.Sensitive` — generic privacy-discipline container:

- `__repr__` / `__str__` redact to `<Sensitive: bytes>` (Pitfall 4 — `repr(envelope)` cannot leak content).
- `.reveal()` returns the wrapped value — the only path; explicit unwrap visible in code review.
- Pydantic v2 integration:
  - `__get_pydantic_core_schema__`: validation accepts `bytes` / `bytearray` / base64 `str` / existing `Sensitive`; raises `TypeError` / `ValueError` otherwise.
  - JSON serialization: emits `base64.b64encode(value).decode("ascii")`.
  - `__get_pydantic_json_schema__`: emits `{"type": "string", "contentEncoding": "base64"}` so generated JSON Schema artifacts describe the wire format correctly. (Added during Task 3 as a Rule 3 deviation — see "Deviations" below.)
- `__hash__` + `__eq__` for ergonomic test usage.

Wire format is byte-for-byte identical to a non-wrapped impl that base64-encodes raw bytes. `Sensitive[T]` is a Python-language repr concern only.

### Versioning + error hierarchy

- `SUPPORTED_VERSIONS = frozenset({"0.3.0", "0.3.1"})` per THERMO-07. v0.3.0 is the existing pi-forge baseline; v0.3.1 is this library's target version (the cirdan→thermocline rename, shipped at `thermocline@5c0d87c`).
- `validate_version(declared)` raises `UnsupportedVersionError` with code `"UNSUPPORTED_VERSION"`.
- `EnvelopeError` base class with `code: str` instance attribute and stable per-class default codes:
  - `UnsupportedVersionError` → `UNSUPPORTED_VERSION` (THERMO-07; this plan).
  - `CanonicalizationError` → `CANONICALIZATION_FAILED` (declared for Plan 02).
  - `IdentityError` → `IDENTITY_ERROR` (declared for Plan 03).
  - `SchemeError(IdentityError)` → `UNSUPPORTED_KEY_SCHEME` (declared for Plan 03 / IDENT-03).
  - `KeystoreUnavailableError(IdentityError)` → `KEYSTORE_UNAVAILABLE` (declared for Plan 03 / IDENT-05).

### KeyScheme enum

`KeyScheme(StrEnum)` with `BRINE` / `PGP` / `X509` / `NONE`. Only `BRINE` ships a working adapter in v0.1 (Plan 03); the other members exist for the verifier-dispatch path (THERMO-Constraint 8 — key scheme is declared, not inferred).

### JSON Schema pipeline (D-02)

`thermocline.scripts.build_schemas` — generate-or-check tool:

- `--write` regenerates `thermocline/schema/{task,task_result,job,job_result,error}.schema.json` from the Pydantic models. Output is sorted-keys + indent=2 + trailing newline (deterministic, diff-clean).
- `--check` compares on-disk schemas vs. fresh ones and exits non-zero with a unified diff naming each drifted file (CI gate).
- Console-script entry: `thermocline-build-schemas --check` (declared in `pyproject.toml`).
- Module entry: `python -m thermocline.scripts.build_schemas --check`.

The five committed schemas:

| Schema | $id |
|--------|-----|
| `thermocline/schema/task.schema.json` | `https://thermocline.spec/schema/v0.3.1/task.schema.json` |
| `thermocline/schema/task_result.schema.json` | `https://thermocline.spec/schema/v0.3.1/task_result.schema.json` |
| `thermocline/schema/job.schema.json` | `https://thermocline.spec/schema/v0.3.1/job.schema.json` |
| `thermocline/schema/job_result.schema.json` | `https://thermocline.spec/schema/v0.3.1/job_result.schema.json` |
| `thermocline/schema/error.schema.json` | `https://thermocline.spec/schema/v0.3.1/error.schema.json` |

All five carry `"$schema": "https://json-schema.org/draft/2020-12/schema"` and self-validate via `jsonschema.Draft202012Validator.check_schema`.

`SCHEMA_DIR` resolution chosen: `Path(__file__).resolve().parents[4] / "schema"` — from `src/thermocline/scripts/build_schemas.py` that resolves `parents[0]=scripts`, `parents[1]=thermocline`, `parents[2]=src`, `parents[3]=python`, `parents[4]=thermocline/` (the spec repo root). End-to-end validated by `--write` + `--check` + drift simulation.

## Verification

| Gate | Result |
|------|--------|
| `pip install -e ".[dev]"` on Python 3.14 (>= 3.11 floor) | OK |
| `from thermocline import Task, TaskResult, Job, JobResult, ErrorEnvelope, ContentBlock, Sensitive, KeyScheme, SUPPORTED_VERSIONS, EnvelopeError` | OK (all 10 names) |
| `pytest tests/` | 39 / 39 pass |
| `mypy --strict src/thermocline/` | 0 errors across 8 source files |
| `ruff check src/thermocline/` | clean |
| `python -m thermocline.scripts.build_schemas --check` | exit 0 |
| Five Draft 2020-12 schema files exist with stable `$id` | OK |
| Drift simulation (corrupt task.schema.json, run --check) | exits non-zero, diff names `task.schema.json` (D-02 acceptance) |
| Pitfall 4 — `repr(model_with_Sensitive_content)` does NOT contain raw bytes | OK |
| Pitfall 11 — no `json.dumps` in library signing-input paths | OK (one schema-emit call documented inline) |
| Pitfall 12 — no `.dict()` / `.json()` v1 patterns | OK |
| No HTTP imports anywhere in `src/` | OK |
| No `print(` calls in library code | OK |

## Test Coverage

| Test file | Tests | What it covers |
|-----------|-------|----------------|
| `tests/test_sensitive.py` | 14 | Redacting `__repr__`/`__str__`; `.reveal()`; equality + hashability; Pydantic validation accepts bytes / bytearray / base64 string / existing Sensitive; rejects unknown types and malformed base64; JSON round-trip preserves bytes; `repr(model)` does NOT leak content (Pitfall 4). |
| `tests/test_envelope.py` | 18 | All 5 envelope classes construct from minimal-valid dicts; JSON round-trip equals original; unknown `thermocline` version raises `ValidationError` and (via `parse_strict`) raises `UnsupportedVersionError` with code `UNSUPPORTED_VERSION` (THERMO-07); parametrized extra-field rejection across all 5 envelopes (THERMO-03); `ContentBlock` redacts in repr; `ContentBlock` round-trips bytes byte-for-byte; `ContentBlock` accepts raw `bytes` via Pydantic validation; `ErrorEnvelope.error.code` is one of the stable string codes. |
| `tests/test_schema_drift.py` | 7 | `--check` against committed schemas exits 0; **drift simulation**: backup-corrupt-restore proves --check exits non-zero with a diff naming the offending file (D-02 acceptance); each on-disk schema validates as Draft 2020-12 with the correct `$id` / `$schema` (parametrized over 5 schemas). |

## Deviations from Plan

### Auto-fixed issues

**1. [Rule 3 — Blocking issue] `Sensitive[T]` needed `__get_pydantic_json_schema__` for build_schemas.py to work**

- **Found during:** Task 3 (running `python -m thermocline.scripts.build_schemas --write` for the first time).
- **Issue:** Pydantic raised `PydanticInvalidForJsonSchema: Cannot generate a JsonSchema for core_schema.PlainValidatorFunctionSchema` because `Sensitive[T]` only declared a core schema, not a JSON schema. Without the hook, `model_json_schema()` fails for any envelope class whose tree contains a `ContentBlock` (i.e., `Task` and `Job`).
- **Fix:** Added a `__get_pydantic_json_schema__` classmethod on `Sensitive` that returns `{"type": "string", "contentEncoding": "base64", "description": "..."}`. The wire format remains base64 ASCII string (matches the existing JSON serializer); the JSON Schema artifact now describes that wire format correctly.
- **Files modified:** `thermocline/python/src/thermocline/sensitive.py` (Task 1 file revisited during Task 3).
- **Tests preserved:** all 14 existing sensitive tests still pass; the new test_schema_drift tests confirm schema generation and drift detection both work.
- **Commit:** `0031ee4` (rolled into the Task 3 GREEN commit; documented in the commit body).

**2. [Rule 3 — Lint cleanup] `json.dumps` Pitfall-11 grep + ruff E501 line-length on the schema-emit call**

- **Found during:** Final overall verification after Task 3.
- **Issue:** The single `json.dumps(...)` in `build_schemas.py` (used to serialize schema artifacts to disk) tripped two coarse checks: the package-wide Pitfall-11 grep `grep -E 'json\.dumps' ... | grep -v '#'` (which counts lines without a `#`), and ruff E501 once an inline noqa comment was added.
- **Fix:** Split `json.dumps(...)` across multiple lines so each line stays under 100 chars; added a `# not a signing path` inline comment on the call line itself so the Pitfall-11 grep treats it as documented.
- **Behavior impact:** zero — `git diff --stat thermocline/schema/` after `--write` is empty (byte-for-byte identical output).
- **Commit:** `477d166` (separate `style(...)` commit so the GREEN behavior commit stays clean).

### Authentication gates

None — this plan is library-only with no network code, no keystore access (deferred to Plan 03), and no external service dependencies.

## Threat-Surface Audit

The threat register's mitigations all landed in code:

- **T-01-01** (information disclosure via repr) — `Sensitive[T]` typed at field level; 3 tests assert no leak.
- **T-01-02** (round-trip tampering) — `model_validate_json(model.model_dump_json()) == model` proven for all 5 envelope shapes.
- **T-01-03** (spoofing via unknown version) — `validate_version` rejects, `UnsupportedVersionError` typed with stable code; 3 tests cover both the wrapped-ValidationError path and the typed `parse_strict` path.
- **T-01-04** (schema drift) — D-02 generate-and-commit + CI `--check`; corrupt-and-restore test proves the drift detector signals.
- **T-01-05** (Sensitive leak via Pydantic) — addressed by both `__repr__` redaction and the JSON-schema hook (the schema emits `contentEncoding: base64`, never the raw bytes).
- **T-01-07** (HTTP imports leaking into library) — `grep -RE 'import requests|import httpx' src/` exits 0.

`T-01-06` (DoS on large payloads) remains accepted-by-design per CONTEXT.md (Phase 4 hardening).

## Threat Flags

None — no new threat surface introduced beyond what the plan's `<threat_model>` already enumerated.

## Spec patches identified for Plan 03 carry-over (THERMO-01)

- The Thermocline spec `README.md` does not yet formalize an `error` envelope shape — pi-forge defines `task_error` ad hoc. We modeled `ErrorEnvelope` after pi-forge's existing wire shape (`type: "task_error"`, nested `error.code` + `error.message`). The committed schema makes the de facto shape explicit. **Recommendation:** add a `### Error Envelope` section to the spec README in Plan 03's spec-patch pass.
- The spec uses `"thermocline": "0.3.0"` as the JSON wire-format version field; we preserved that name on the Python side too (`Task.thermocline: str`). No alias required, but worth documenting in the spec as the canonical Python field name when other languages add reference impls.

## Known Stubs

None — this plan ships no stubs. `Sensitive[T]` Pydantic schema, envelope models, schema generator are all fully wired.

## Self-Check: PASSED

Files claimed:
- `thermocline/python/pyproject.toml` — FOUND
- `thermocline/python/README.md` — FOUND
- `thermocline/python/src/thermocline/__init__.py` — FOUND
- `thermocline/python/src/thermocline/version.py` — FOUND
- `thermocline/python/src/thermocline/errors.py` — FOUND
- `thermocline/python/src/thermocline/schemes.py` — FOUND
- `thermocline/python/src/thermocline/sensitive.py` — FOUND
- `thermocline/python/src/thermocline/envelope.py` — FOUND
- `thermocline/python/src/thermocline/py.typed` — FOUND
- `thermocline/python/src/thermocline/scripts/__init__.py` — FOUND
- `thermocline/python/src/thermocline/scripts/build_schemas.py` — FOUND
- `thermocline/python/tests/__init__.py` — FOUND
- `thermocline/python/tests/test_sensitive.py` — FOUND
- `thermocline/python/tests/test_envelope.py` — FOUND
- `thermocline/python/tests/test_schema_drift.py` — FOUND
- `thermocline/schema/task.schema.json` — FOUND
- `thermocline/schema/task_result.schema.json` — FOUND
- `thermocline/schema/job.schema.json` — FOUND
- `thermocline/schema/job_result.schema.json` — FOUND
- `thermocline/schema/error.schema.json` — FOUND
- `.gitignore` — FOUND

Commits claimed (in order):
- `fef2795` feat(01-01): scaffold thermocline-py package + Sensitive[T] wrapper — FOUND
- `1229c40` test(01-01): add failing tests for Pydantic envelope models (TDD RED) — FOUND
- `619ccb4` feat(01-01): implement Pydantic v2 envelope models (TDD GREEN) — FOUND
- `0031ee4` feat(01-01): JSON Schema drift-check pipeline + committed schemas — FOUND
- `477d166` style(01-01): satisfy ruff E501 + Pitfall-11 grep on json.dumps line — FOUND

## TDD Gate Compliance

Plan 01-01 contains a TDD-marked task (Task 2). Gate sequence:

- RED: `1229c40` test(01-01): add failing tests for Pydantic envelope models — **PRESENT**
- GREEN: `619ccb4` feat(01-01): implement Pydantic v2 envelope models — **PRESENT** (after RED)
- REFACTOR: not separately needed; the GREEN commit produced clean code (mypy strict + ruff clean).

TDD gate compliance: PASSED.
