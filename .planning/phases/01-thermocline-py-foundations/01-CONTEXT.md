# Phase 1: `thermocline-py` Foundations - Context

**Gathered:** 2026-05-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver `thermocline-py` — the shared Python library every other suite component depends on. Lives at `thermocline/python/`, packaged as `thermocline-py` for PyPI. Forever-decisions land here:

- **Pydantic v2 envelope types** for `task`, `task_result`, `job`, `job_result`, `error`
- **Single canonical-JSON path** (`thermocline.canonical.canonicalize` via `rfc8785`) — the only signing-input function across the entire suite
- **`IdentityProvider` Protocol** + brine reference adapter (PyNaCl + `python-keyring`) that never returns `PrivateKey` and refuses to start without keystore
- **`Receipt` value type** constructible only via `IdentityProvider.verify()` returning success
- **JSON Schema artifacts** under `thermocline/schema/` for every envelope shape
- **Conformance fixtures** under `thermocline/conformance/{valid,invalid}/` annotated with the AT-* threat-model surface each invalid fixture exercises
- **`Sensitive[T]` redaction discipline** established at the type-system level so every downstream importer (Photophore, pi-forge, describe-forge, future cross-language impls) inherits redacted-by-default content fields

This phase ships zero network code, zero Photophore policy logic, and zero forge handlers. It establishes the type-and-crypto contracts the rest of the suite builds against.

</domain>

<decisions>
## Implementation Decisions

### Receipt Private-Constructor Mechanism (IDENT-04)

- **D-01:** `Receipt` is a frozen `@dataclass(frozen=True, slots=True)` — **not** a Pydantic model. Construction is gated by a module-private sentinel token in `thermocline.identity`; `IdentityProvider.verify()` is the only function that holds the token. Direct construction (`Receipt(envelope_id="x", ...)`) raises `TypeError` at runtime; `mypy --strict` flags it at type-check time. Receipt never crosses the network — it is an internal verification witness, so loss of Pydantic schema/serialization does not matter.

  **Rationale:** Pydantic `BaseModel` always exposes `__init__`, `model_validate`, AND `model_construct` — three public escape hatches that "skipped verification" could exploit. Frozen dataclass + sentinel closes both static and runtime construction paths in a single, testable mechanism.

  **Acceptance test:** `with pytest.raises(TypeError): Receipt(envelope_id="x", signature_hash="y", verified_at=now, key_scheme=KeyScheme.BRINE)` — direct construction must raise.

### JSON Schema Generation Pipeline (THERMO-02)

- **D-02:** Schemas are **generated from Pydantic models and committed** under `thermocline/schema/`. A single script `thermocline/python/scripts/build_schemas.py` regenerates them; CI runs `python -m thermocline.scripts.build_schemas --check` and fails on drift. Each schema file uses `$id: "https://thermocline.spec/schema/v0.3.1/<envelope>.schema.json"` (placeholder URL — not served at v0.1, but stable identifier for `$ref` resolution).

  **Rationale:** Schemas are public cross-language artifacts; future `thermocline-ts` / `thermocline-rs` impls reference them at stable paths. Generate-on-build makes them ephemeral; hand-authored re-introduces drift. Generate-and-commit with CI drift check is the standard protobuf/OpenAPI pattern — well-understood by Python contributors.

  **Acceptance test:** delete a Pydantic field locally, run `--check`, verify CI exit code is non-zero with a diff message naming the changed file.

### `Sensitive[T]` Wrapper — Land in Phase 1

- **D-03:** `Sensitive[T]` ships in **Phase 1** in a new module `thermocline.sensitive`. Envelope content fields (`ContentBlock.content`, result body bytes) are typed `Sensitive[bytes]` from the first commit. The wrapper has redacting `__repr__` (`<Sensitive: bytes>`) and `__str__`; values are unwrapped via explicit `.reveal()` at use sites; Pydantic v2 custom serializer unwraps to base64 string for `model_dump(mode='json')` so canonical-JSON output is byte-for-byte identical to a non-wrapped impl. The wire format is unchanged — `Sensitive[T]` is a Python-language repr concern only.

  **Rationale:** Pitfall 4 (research/PITFALLS.md) explicitly assigns this discipline to Phase 1. If `thermocline-py` ships with raw `bytes` content, every downstream Python importer (Photophore, pi-forge upgrade in Phase 3, describe-forge in Phase 3) inherits the leak by default and retrofitting later means breaking every import site. Putting it in `thermocline-py` also signals that redaction is suite-wide library hygiene, not Photophore-only policy.

  **Acceptance test:** assert `repr(envelope_with_sensitive_content)` contains no content bytes; assert `canonicalize(envelope.model_dump(mode='json'))` matches a known-good byte sequence (proves wrapper is wire-transparent).

### Conformance Fixture Structure (THERMO-06)

- **D-04:** Fixtures stay as **clean envelope JSON**. Annotation lives in a YAML manifest per subdirectory:

  ```
  thermocline/conformance/
  ├── valid/
  │   ├── MANIFEST.yaml          # request/response pairs
  │   ├── task-pi-100-digits.json
  │   └── task-result-pi-100-digits.json
  └── invalid/
      ├── MANIFEST.yaml          # surface + expected error code
      ├── AT-C1-replayed-envelope.json
      ├── AT-C3-leaky-shadow.json
      └── AT-C5-unsupported-version.json
  ```

  Filenames encode the AT-* surface for human grep (`ls invalid/AT-C3*`); truth lives in `MANIFEST.yaml` with `{fixture, surface, description, expect_error_code}` per entry. `valid/MANIFEST.yaml` lists `(request, expected_response)` pairs. Phase 4's `forge_conformance` harness walks each manifest, counts AT-* coverage across the 17 surfaces, fails CI if any surface has zero entries.

  **Rationale:** A `_meta` block inside the JSON contaminates the envelope so it no longer parses as a real Thermocline envelope (defeats the test's purpose under strict Pydantic validation). Sidecar `.meta.json` files double the file count and risk drift on rename. Filename-only loses the expected-error-code — every consumer remembers the mapping. Manifest YAML is language-agnostic (TS/Rust impls parse YAML), single-source-of-truth, and directly maps to CONF-02 coverage counting.

  **Phase 1 deliverable:** the manifest schema + at least one fixture per AT-C* surface (Thermocline AT-C1..C6 = 6 surfaces). AT-A* (Photophore) and AT-E* (Seamount) fixtures land in Phases 2/3 alongside their respective implementations.

### Claude's Discretion

The following sub-decisions are not user-facing — Claude (planner + executor) has flexibility within the constraints established above:

- Exact layout of `thermocline/python/scripts/` (single `build_schemas.py` vs. a small CLI module)
- Whether the brine adapter exposes `generate()` as a Protocol method or a separate `keygen` utility (IDENT-01 says yes to Protocol; planner picks the API surface)
- `python-keyring` service-name convention (recommended default: service `"thermocline.brine"`, username = identity ID; revisitable in planning)
- Whether `thermocline-py` ships any CLI utilities (e.g., `python -m thermocline validate-fixture <path>`) — useful for spec-readers but redundant with future Photophore CLI; default to library-only unless planner identifies a strong dev-loop need
- Pydantic model `ConfigDict` options (`extra="forbid"` is required by THERMO-03; everything else is planner discretion)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Specs (source of truth — `thermocline/README.md` is canonical)
- `thermocline/README.md` — Thermocline spec v0.3.0-draft (envelope contract, role architecture, AT-C1..C6 threat model)
- `photophore/README.md` — Photophore spec v0.3.0-draft (relevant only for AT-A* awareness in fixture authorship)
- `seamount/README.md` — Seamount spec v0.3.0-draft (relevant for forge envelope shape — pi-forge upgrade in Phase 3)

### Planning hub (single source of truth for cross-repo planning)
- `thermocline/.planning/PROJECT.md` — Suite-wide project definition, key decisions table, constraints
- `thermocline/.planning/REQUIREMENTS.md` §"Thermocline" + §"Identity Provider" — THERMO-01..07 + IDENT-01..05 (Phase 1 scope)
- `thermocline/.planning/ROADMAP.md` §"Phase 1" — phase goal, success criteria, plan list
- `thermocline/.planning/STATE.md` — current position, accumulated decisions

### Research bundle
- `thermocline/.planning/research/STACK.md` — locked stack (Python 3.11+, Pydantic 2.7+, PyNaCl 1.5+, `rfc8785`, `python-keyring` 25, BLAKE3 0.4+, `mypy --strict`, `ruff`)
- `thermocline/.planning/research/ARCHITECTURE.md` — repo layout, module boundaries, suite-wide diagram
- `thermocline/.planning/research/PITFALLS.md` Pitfall 4 (Sensitive discipline), Pitfall 9 (no in-process keys), Pitfall 11 (json.dumps), Pitfall 12 (Pydantic v1 patterns) — all assigned to Phase 1
- `thermocline/.planning/research/FEATURES.md` — feature scope per repo
- `thermocline/.planning/research/SUMMARY.md` — executive summary of all research

### External standards
- **RFC 8785 (JCS)** — JSON Canonicalization Scheme, the only canonical-JSON path. Implemented via the `rfc8785` Python package.
- **Pydantic v2 documentation** — `model_dump(mode='json')`, custom serializers, `ConfigDict(extra="forbid")`. v2 patterns only; `.dict()` / `.json()` are forbidden by Pitfall 12.
- **PyNaCl documentation** — `nacl.signing.SigningKey`, `nacl.signing.VerifyKey`. Constant-time verification (Pitfall: never compare signature bytes by hand).
- **`python-keyring` 25.x** — backend selection, `get_keyring()`, `keyring.errors.NoKeyringError` for "refuse to start" path (IDENT-05).

### Out-of-band prior work
- Spec patch (`cirdan` → `thermocline` JSON field rename) shipped at commit `thermocline@5c0d87c`. THERMO-01 partial — additional spec patches as discovered land in this phase.

### Reference implementation to learn from
- `seamount/pi-forge/envelope.py` — existing Thermocline envelope handling with stubbed crypto. Phase 1 supersedes this in Phase 3 by upgrading pi-forge to import `thermocline-py`. Read for: `EnvelopeError` patterns, validation idioms, error-envelope shape — useful as a template for what `thermocline-py` should expose more robustly.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`seamount/pi-forge/envelope.py`** — existing validation/serialization patterns (stubbed crypto). Translate the validation discipline into Pydantic v2 models; replace `EnvelopeError` with a properly-typed exception hierarchy in `thermocline.errors`. Pi-forge's `SUPPORTED_VERSIONS = {"0.3.0"}` upgrades to `{"0.3.0", "0.3.1"}` per THERMO-07.
- **`seamount/pi-forge/server.py`** — Flask handler shape (request/response flow, error envelope construction). Informs but does not constrain Phase 1; `thermocline-py` is library-only.
- **`thermocline/conformance/`** (currently empty / not yet created) — Phase 1 creates this directory and seeds it with at least one valid fixture and one fixture per AT-C* surface (6 fixtures minimum).

### Established Patterns
- **Spec-mandated module separation** (per `research/ARCHITECTURE.md`): `thermocline.{envelope, canonical, identity, schemes, version, errors, sensitive, conformance}`. No HTTP imports anywhere in `thermocline.*` — enforced by Phase 4 AST lint, but Phase 1 must respect it from the first commit.
- **Pydantic v2 only**: `pydantic>=2.7,<3.0` pinned in `pyproject.toml`; CI lint flags `.dict(` and `.json()` v1 patterns (Pitfall 12).
- **Versioned hash dispatch**: Phase 2's audit log uses `algo_version`. Phase 1's analog: `KeyScheme` enum + verifier dispatch in `thermocline.identity` (IDENT-03) — implemented for `brine` only, dispatch path exists for `pgp`/`x509`/`none`.

### Integration Points
- **Photophore (Phase 2)** imports `from thermocline import (Task, TaskResult, Job, JobResult, ErrorEnvelope, canonicalize, IdentityProvider, Receipt, KeyScheme, Sensitive)`. Public API surface must stabilize in Phase 1 — breaking changes after Phase 1 cascade across two more phases.
- **pi-forge upgrade (Phase 3)** swaps its in-tree `envelope.py` for `from thermocline import ...`. Phase 1's API must be ergonomic enough that pi-forge's Flask handler stays under ~50 lines after the swap.
- **describe-forge (Phase 3)** — new forge built directly against `thermocline-py`. Its existence is a Phase 1 design constraint: the library API must support a tier-1-shadow-handling forge naturally (no shadow-specific helpers — those live in Photophore — but the envelope types must round-trip a `Shadow` object inside `task.context[]`).

</code_context>

<specifics>
## Specific Ideas

- **Receipt frozen-dataclass example** — see Decisions D-01 above for the canonical sentinel-token pattern. Planner copies this into the `thermocline.identity` module skeleton.
- **Schema `$id` placeholder URL** — `https://thermocline.spec/schema/v0.3.1/<envelope>.schema.json`. Not served at v0.1; spec README can link to GitHub raw URLs for now; URL stays stable for future hosting.
- **Manifest YAML shape** — explicit field set: `fixture` (relative path), `surface` (e.g., `AT-C3`), `description` (one line), `expect_error_code` (matches `thermocline.errors` enum). Valid manifest pairs use `request` + `response` instead of `fixture`.
- **Phase 1 fixture minimum:** one valid `(task, task_result)` pair (template: pi-forge's `examples/task-100-digits.json`) + six invalid fixtures, one per Thermocline AT-C surface (AT-C1..AT-C6). AT-A* and AT-E* fixtures land in their respective phases.

</specifics>

<deferred>
## Deferred Ideas

- **`Sensitive[T]` `logging.Filter`** — research/PITFALLS.md mentions a logging filter that drops fields tagged `sensitive=True`. Phase 1 ships the `Sensitive[T]` type and redacting `__repr__`; the logging filter belongs in Phase 4 (CONF-06) alongside the `print(` lint and the suite-wide ADRs.
- **Apple Silicon Secure Enclave coverage** — STATE.md flags this as a blocker requiring physical hardware + signing identity. Phase 1 targets standard Keychain via `python-keyring`; Secure Enclave specifics deferred to Phase 4 testing.
- **Cross-language `thermocline-ts` / `thermocline-rs`** — out of scope for the v0.1 milestone (PROJECT.md "Out of Scope by project scope"). Schema $id URL chosen with future hosting in mind.
- **`thermocline-py` CLI utilities** (`python -m thermocline keygen`, `validate-fixture`) — Claude's discretion above; default library-only unless planner finds a strong dev-loop need. If added, they belong in Phase 1; if deferred, they fit naturally in Phase 4 ops docs.
- **Spec patches discovered during Phase 1 implementation** — THERMO-01 explicitly invites additional spec patches. Each lands as a separate commit on `thermocline/README.md` (and changelog) in this phase, not deferred.

</deferred>

---

*Phase: 1-thermocline-py-foundations*
*Context gathered: 2026-05-05*
