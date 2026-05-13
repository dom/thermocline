# Thermocline Spec Changelog

This file tracks spec patches discovered during reference-implementation work
(THERMO-01). The Thermocline README at the repo root remains the normative
source of truth; CHANGELOG entries reference clauses or commits where the
patch landed and explain *why* the spec moved.

The reference implementation lives at `thermocline/python/`; the JSON Schema
artifacts under `thermocline/schema/` are the language-agnostic contract that
cross-language ports validate against.

## [0.3.1] - 2026-05-13

### Spec amendments (SP-3.3-01..03 — Phase 3 surfaced; Phase 4 promotes to README)

- **SP-3.3-01 — Receipt-signature canonicalization invariant**: README §"Receipt Signatures" amended with normative paragraph requiring verifiers to canonicalize the envelope with `receipt_signature.sig = ""` (empty string), NOT removed. Eliminates cross-impl reproduction-by-reverse-engineering on the receipt path.
- **SP-3.3-02 — Dispatch_signature pre-fill ordering**: README §"Dispatch Signatures" amended. All non-`sig` fields MUST be populated BEFORE canonicalization+signing.
- **SP-3.3-03 — Receipt field tolerance**: README §"Receipt Signatures" amended. Verifiers SHOULD accept `sig` OR `bytes_hex`; emitters MUST use `sig`.

> Phase 3 03-03-SUMMARY initially classified these as coordinator-internal changes (the spec was right; the coordinator was wrong). Phase 4 reclassifies them as spec clarifications because any non-Python implementation will reverse-engineer the Python coordinator to discover them. Shipping as README amendments is the cross-impl-spec-patch pattern established by THERMO-01.

`SUPPORTED_VERSIONS` in `thermocline-py` already includes `"0.3.1"` (Phase 1).

### Implemented (Phase 1 + Phase 2 inheritance)

## [0.1.0] - 2026-05-13

Suite milestone: first coordinated v0.1.0 release of the Thermocline suite
(thermocline-py + photophore + seamount). Three identically-versioned git
tags land on the same UTC date with the message
`v0.1.0 — coordinated with thermocline v0.1.0 + photophore v0.1.0 + seamount v0.1.0`.

### Added

- `docs/adr/` — 5 MADR-lite ADRs (ADR-0001 Python 3.11; ADR-0002 Pydantic v2;
  ADR-0003 single canonical JSON path; ADR-0004 BLAKE3 with `algo_version`;
  ADR-0005 no in-process key material).
- `docs/install.md`, `docs/ops.md` (placeholder), `docs/quickstart.md`
  (30-min cross-repo walkthrough), `docs/index.md`.
- `scripts/tag-v0.1.0.sh` release coordinator with `--dry-run` mode.
- README §"Architecture Decision Records" linking to local + photophore
  cross-refs.

### Implemented

- **THERMO-01** — Cross-impl spec-patch pattern: discovered Phase 1/2/3
  spec ambiguities are landed as README amendments at the draft version.
  cirdan→thermocline rename (`thermocline@5c0d87c`); `Sensitive[T]` discipline;
  Receipt private constructor invariant; brine-scheme keystore-only constraint.
- **THERMO-02** — JSON Schema artifacts under `thermocline/schema/` for
  task, task_result, job, job_result, error envelopes (Draft 2020-12).
- **THERMO-03..05** — Pydantic v2 envelope models; `model_config = ConfigDict(extra="forbid")`;
  strict validation at the boundary.
- **THERMO-06** — Conformance fixture corpus under `thermocline/conformance/`
  with YAML manifests, surface tags, and `phase:` provenance per fixture.
  Phase 4 backfilled phase tags + added AT-A3, AT-A6, AT-E1..E5 fixtures.
- **THERMO-07** — `SUPPORTED_VERSIONS` lists `0.3.0`, `0.3.1`; rejects
  unknown spec versions at validation time.
- **IDENT-01..05** — `IdentityProvider` Protocol; brine ed25519 reference
  adapter; keystore-only constraint; `Receipt` private constructor;
  separate public-key + seed stores (BL-01).
- **SP-3.3-01..03** — Spec amendments landing in this release: receipt
  canonicalization invariant, dispatch_signature pre-fill ordering, receipt
  field tolerance. See ## [0.3.1] above.

### Deferred to subsequent milestones

- Rust / TypeScript / Swift reference implementations (post-v0.1)
- Job envelopes formal lifecycle (v0.2)
- Hardware-anchored Apple Silicon Secure Enclave keystore (v0.2 — D-11)
- Full MADR (problem/drivers/options/pros-cons) ADR audit pass (post-v0.1)
- Keep-a-Changelog full-spec migration (Changed / Fixed / Security
  subsections) (post-v0.1)
- CI-triggered tagging on release-branch push (post-v0.1)

### Known limitations

- Default `python-keyring` macOS Keychain entries are software-backed
  (encrypted at rest, gated by user's login session). Hardware-anchored
  Apple Silicon Secure Enclave entries require a developer signing identity;
  deferred to v0.2. v0.1 threat model is satisfied without Secure Enclave:
  key material never leaves the keystore.
- Linux + Windows ops paths documented best-effort; CI-tested matrix only
  covers ubuntu-latest (non-keystore tests) + macos-latest (keystore tests).
- Conformance fixture filename drift retained: `AT-C1-replayed-envelope.json`
  tests AT-C2 (replay); `AT-C5-unsupported-version.json` tests THERMO-07
  not AT-C5; `AT-A4-audit-log-tampering.json` tests channel MITM not audit
  tamper. Documented in MANIFEST.yaml `notes:` fields; not renamed
  (preserves cross-language port stability per Plan 04-01 Pitfall 3).

## [0.3.0-draft]

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

### Plan 02-03 spec patch (OQ-2 resolution — Phase 2)

- **ResultPolicy public export** (Phase 2 / Plan 02-03 / OQ-2):
  - Renamed `thermocline.envelope._ResultPolicy` → `thermocline.envelope.ResultPolicy` (public class).
  - Added `ResultPolicy` to `thermocline.envelope.__all__` and to `thermocline.__all__`.
  - Backward-compat alias `_ResultPolicy = ResultPolicy` retained in `envelope.py` for at least one minor cycle (v0.3.x); Phase 4 may remove it once all callers have migrated.
  - Photophore (Plan 02-03) authors `result_policy` on issuer-node task envelopes; the API surface is now public, not private.
  - Cross-impl contract: any future thermocline-py port (Rust, TypeScript, Swift) MUST expose `ResultPolicy` as public.
  - Migration: `from thermocline.envelope import _ResultPolicy` → `from thermocline import ResultPolicy`. The private import still works for one minor cycle via the alias.
  - Schema artifacts regenerated via `python -m thermocline.scripts.build_schemas --write` (standard D-02 pipeline); the `$defs` key changed from `_ResultPolicy` to `ResultPolicy` in task/job schema embeds. Verified clean via `--check`.

### Plan 01-04 gap closure (BL-01..BL-04)

Phase 1 verification (`/gsd-verify-phase 1`) reported `status: gaps_found`,
`score: 3/5 must-haves verified`. Plan 01-04 closes the four gaps. See
`.planning/phases/01-thermocline-py-foundations/01-VERIFICATION.md` for the
full report.

- **BL-01** (IDENT-02) — `BrineProvider` separates the public-key store from
  the seed store. New `register_public_key(identity, verify_key)` API;
  `public_key()` consults the public-key store first and falls back to
  seed-derivation only for single-node self-signing flows. A verifier-only
  role can now verify foreign signatures without holding the signer's seed
  (IDENT-02 architectural intent restored; Phase 3 SC3 unblocked).
- **BL-02** (IDENT-03) — `Verifier.verify` reads the declared `key_scheme`
  from the canonical nested location: `dispatch_signature.key_scheme` for
  `task`/`job` envelopes, `receipt_signature.key_scheme` for
  `task_result`/`job_result` envelopes, `None` for `task_error`/`job_error`
  (error envelopes are unsigned by spec). Top-level
  `envelope.get('key_scheme')` is preserved as a tolerated fallback for
  synthetic flat-dict test inputs AND for typed envelopes whose canonical
  nested block is absent or empty. Real Task/TaskResult envelopes from
  `thermocline/conformance/valid/` now round-trip through `Verifier.verify`
  and produce a `Receipt`; AT-C4 is wired behaviorally rather than
  structurally.
- **BL-03** (IDENT-05) — `BrineProvider.__init__` rejects unavailable
  keystores via `isinstance(backend, (keyring.backends.fail.Keyring,
  keyring.backends.null.Keyring))` — direct class identity, not a substring
  match on `type(backend).__name__`. The substring heuristic missed both
  production classes (both are named `'Keyring'`); the adapter falls open
  no longer (IDENT-05 enforced in production).
- **BL-04** — `BrineProvider.generate()` refuses to clobber an existing
  seed (raises `IdentityError(code='IDENTITY_ALREADY_EXISTS')`). New
  `BrineProvider.rotate()` is the only documented path that replaces an
  existing seed. Closes a foreseeable data-loss path: re-running a setup
  script no longer destroys the prior signing identity.

## v0.3.0 (prior — published spec)

Initial spec release. See the repository root `README.md` for the full text
of the published spec. Highlights:

- Five envelope shapes: `task`, `task_result`, `job`, `job_result`, `error`
- Privacy tier system (tier-0 `local`, tier-1 `shadow`, tier-2 `public`)
- Shadow-block contract for tier-1 abstractions
- Companion specifications: Photophore 0.3.0+ (policy engine), Seamount
  0.3.0+ (forge)
