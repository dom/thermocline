# Thermocline Spec Changelog

This file tracks spec patches discovered during reference-implementation work
(THERMO-01). The Thermocline README at the repo root remains the normative
source of truth; CHANGELOG entries reference clauses or commits where the
patch landed and explain *why* the spec moved.

The reference implementation lives at `thermocline/python/`; the JSON Schema
artifacts under `thermocline/schema/` are the language-agnostic contract that
cross-language ports validate against.

## v0.3.1 (in progress — Phase 1)

Discovery phase: implementing `thermocline-py` against the published v0.3.0
spec surfaced the following patches. Each is recorded here and applied in the
reference implementation; the spec body itself moves on a separate, audited
commit cadence (THERMO-01 carry-over).

- **Field rename `cirdan` → `thermocline`** on every envelope. The pre-rename
  corpus (`pi-forge/examples/*`) used `"cirdan": "0.3.0"`; v0.3.1 replaces
  this with `"thermocline": "0.3.1"` to align with the spec name and the
  versioning section. Rename shipped at thermocline@5c0d87c during the
  0.3.0-draft RFC window.
- **`thermocline-py` registry entry**: the in-tree Python package becomes
  the canonical reference implementation. Every cross-language port targets
  the same wire format (canonical-JSON + JSON Schema) and the same
  conformance corpus under `thermocline/conformance/`.
- **Schema artifacts published under `thermocline/schema/`** for `task`,
  `task_result`, `job`, `job_result`, and `error` (Draft 2020-12, generated
  from the Pydantic models, drift-checked by `tests/test_schema_drift.py`).
  These artifacts are the contract a third-party impl validates against —
  the README's prose remains the design intent. (THERMO-02)
- **`Sensitive[T]` discipline** at the type-system level: `ContentBlock.content`
  is `Sensitive[bytes]`, redacting in `repr` and serializing as a base64
  string at the JSON boundary. Belt-and-suspenders defense against Pitfall 4
  (private bytes leaking via `print(envelope)` / `logger.info(envelope)`).
  (D-03 / Phase 1 CONTEXT.md)
- **Receipt private-constructor invariant** (D-01): `Receipt` is constructible
  only by `IdentityProvider.verify` returning success. Direct construction
  raises `TypeError` at runtime AND fails `mypy --strict` (the constructor
  takes a required `_token` parameter typed against a module-private sentinel
  class). Makes "skipped verification" inexpressible at both layers. The
  spec README does not yet name this invariant — promotion to spec is a
  THERMO-01 carry-over for the v0.3.1 spec body update.
- **Brine scheme keystore-only constraint**: the brine reference adapter
  refuses to start when the platform secure keystore is unavailable
  (`KeystoreUnavailableError`); there is no filesystem or env-var fallback
  path (IDENT-05). The spec does not yet formalize the "no fallback"
  property — promotion to spec is a THERMO-01 carry-over.
- **Conformance manifest schema (D-04)**: cross-language fixtures live under
  `thermocline/conformance/` with three-level YAML manifests (top-level +
  `valid/MANIFEST.yaml` + `invalid/MANIFEST.yaml`). Each invalid manifest
  entry declares `surface`, `description`, `expect_error_code`, and `phase`
  (the phase that wires the surface). Phase 1 ships the AT-C1..AT-C6 corpus.
  (THERMO-06)
- **`ErrorEnvelope` shape clarification**: the spec README does not yet
  formalize an error envelope; `pi-forge` uses a `task_error` envelope with
  a nested `error: {code, message}` block. The reference impl ships
  `ErrorEnvelope` with that shape; spec promotion is a THERMO-01 carry-over.

## v0.3.0 (prior — published spec)

Initial spec release. See the repository root `README.md` for the full text
of the published spec. Highlights:

- Five envelope shapes: `task`, `task_result`, `job`, `job_result`, `error`
- Privacy tier system (tier-0 `local`, tier-1 `shadow`, tier-2 `public`)
- Shadow-block contract for tier-1 abstractions
- Companion specifications: Photophore 0.3.0+ (policy engine), Seamount
  0.3.0+ (forge)
