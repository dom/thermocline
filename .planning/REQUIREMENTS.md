# Requirements: Thermocline Suite v0.1

**Defined:** 2026-05-05
**Core Value:** Reveal only what the receiver needs to know, and nothing else — every content block is `local` by default, transmission is the exception earned by explicit human-authored trust, and every boundary crossing produces a verifiable, append-only privacy receipt.

**Repos in scope:** `thermocline/`, `photophore/`, `seamount/`. Each requirement is tagged with the repo where the work lands.

## v1 Requirements

Requirements for the v0.1 implementation milestone. Each maps to a roadmap phase.

### Thermocline (Spec + `thermocline-py` shared library) — `[thermocline]`

- [ ] **THERMO-01** `[thermocline]` — Spec patch: rename schema version field from `cirdan` to `thermocline` in JSON examples, library registry names (`thermocline-py`/`thermocline-ts`), and changelog. (Already shipped: `thermocline@5c0d87c`.) Add additional spec patches as discovered during implementation.
- [ ] **THERMO-02** `[thermocline]` — Publish JSON Schema artifacts (Draft 2020-12) under `thermocline/schema/` for: `task`, `task_result`, `job`, `job_result`, `error`. Schemas are generated from the same Pydantic models used in `thermocline-py` and validated against the conformance fixture set.
- [ ] **THERMO-03** `[thermocline]` — `thermocline-py` exposes Pydantic v2 models for every envelope shape with strict validation (no extra fields, no missing required fields, type-checked at boundary).
- [ ] **THERMO-04** `[thermocline]` — `thermocline-py` exposes a single canonical-JSON path (`thermocline.canonical.canonicalize`) implementing RFC 8785 / JCS; this is the only path used for signature input across the entire suite.
- [ ] **THERMO-05** `[thermocline]` — `thermocline-py` package metadata (`pyproject.toml`) is publishable as `thermocline-py` to PyPI; pinned to Pydantic v2 only (`pydantic>=2.7,<3.0`); supports Python 3.11+.
- [ ] **THERMO-06** `[thermocline]` — `thermocline-py` exports cross-language conformance fixtures under `thermocline/conformance/{valid,invalid}/` — JSON request/response pairs, each invalid fixture annotated with the AT-* threat-model surface it exercises.
- [ ] **THERMO-07** `[thermocline]` — `thermocline-py` SUPPORTED_VERSIONS includes `"0.3.1"` and rejects any other declared version with a structured error (`UNSUPPORTED_VERSION`).

### Identity Provider — `[thermocline]` (within `thermocline-py`)

- [ ] **IDENT-01** `[thermocline]` — `IdentityProvider` is exposed as a `typing.Protocol` (or ABC) with members `scheme`, `sign`, `verify`, `public_key`, `generate`. The Protocol is the only path through which signing/verification occurs anywhere in the suite.
- [ ] **IDENT-02** `[thermocline]` — Reference adapter implements the `brine` key scheme using PyNaCl (Ed25519) with key material backed by `python-keyring`. The adapter never returns the private key, never copies key material out of the keystore, and never holds key bytes in process memory beyond what `python-keyring` necessarily exposes during the keystore RPC.
- [ ] **IDENT-03** `[thermocline]` — Verifier dispatches on the channel's declared `key_scheme` and refuses to verify a signature whose declared scheme does not match the channel's. v0.1 implements only `brine`; the dispatch path exists for future schemes (`pgp`, `x509`, `none`).
- [ ] **IDENT-04** `[thermocline]` — `Receipt` is a value type constructible only by `IdentityProvider.verify` returning success. There is no public constructor — "skipped verification" cannot be expressed in code.
- [ ] **IDENT-05** `[thermocline]` — Adapter refuses to start when the platform secure keystore is unavailable; it does NOT fall back to file-based or env-var-based key storage.

### Photophore Channels (Trust Store and Lifecycle) — `[photophore]`

- [ ] **CHAN-01** `[photophore]` — User can create a channel with a unique ID, local node identity, remote node identity, explicit trust ceiling (`tier-0` / `tier-1` / `tier-2`), key scheme (declared and immutable at creation), creation timestamp, creator identity, and optional description.
- [ ] **CHAN-02** `[photophore]` — Channel state advances through PROPOSED → OPEN → SUSPENDED → CLOSED with explicit user-invoked transitions; CLOSED is terminal and channel IDs are never reused.
- [ ] **CHAN-03** `[photophore]` — Trust ceilings are monotonically decreasing on suspicion: any user can lower a ceiling unilaterally at any time; raising a ceiling requires a deliberate human action recorded as a distinct audit event.
- [ ] **CHAN-04** `[photophore]` — Channel registry is backed by `python-keyring` (Keychain / libsecret / Credential Manager). The trust store is never co-located with the audit log SQLite database and is never synced or backed up to remote storage.
- [ ] **CHAN-05** `[photophore]` — Channel-creation, suspension, ceiling-change, and closure operations each produce a corresponding audit log entry before the operation is reported successful.
- [ ] **CHAN-06** `[photophore]` — Channel state is queryable via `photophore channel list` and `photophore channel show <id>` with both human-readable and JSON output modes.

### Photophore Classification — `[photophore]`

- [ ] **CLASS-01** `[photophore]` — Classification follows strict priority order: Explicit Tag (Priority 1) > Path Rule (Priority 2) > rule-based Classifier (Priority 3); higher priority always wins.
- [ ] **CLASS-02** `[photophore]` — Explicit tags `@photophore:local`, `@photophore:shared`, `@photophore:public` are parsed from content and treated as authoritative tier assignments.
- [ ] **CLASS-03** `[photophore]` — Path rules support glob-style patterns; the rules config MUST end with a `**` → `local` catch-all and Photophore refuses to load any config lacking it.
- [ ] **CLASS-04** `[photophore]` — Rule-based classifier (v0.1) defaults all unmatched content to `local`; positively detects credential patterns, PII patterns, and known sensitive file types, assigning them `local`; never promotes content to `public` from inference alone.
- [ ] **CLASS-05** `[photophore]` — Every classification produces an explanation `(tier, reason)` where reason is one of `explicit_tag`, `path_rule:<pattern>`, `classifier:<rule_name>`, `classifier:default`; explanation is queryable via `photophore classify <input>` as a dry-run.
- [ ] **CLASS-06** `[photophore]` — The default-tier function is implemented as a single explicit named function returning `Tier.LOCAL`; a Hypothesis property test asserts that any `ContentBlock` with no explicit tag and no path-rule match is classified as `(Tier.LOCAL, Reason.CLASSIFIER_DEFAULT)`.

### Photophore Shadow Generation — `[photophore]`

- [ ] **SHADOW-01** `[photophore]` — Shadows are generated only at dispatch time (never at write time); a fresh shadow is produced for every dispatch even of identical source content.
- [ ] **SHADOW-02** `[photophore]` — Shadow contains exactly: `shadow_id` (UUIDv4 over `secrets.token_bytes`/`os.urandom`, unique per dispatch), `content_type` (coarse-grained), `abstraction` (per Photophore v0.3 quality table), `relevance` (float 0.0–1.0), and `tier` (always 1).
- [ ] **SHADOW-03** `[photophore]` — Shadow content_type-specific abstraction strategies implemented per the Photophore v0.3 quality table for: `document`, `conversation`, `credential`, `file`, `identity`, `code`. Each type's abstraction MUST include only listed signals and MUST NOT include prohibited signals.
- [ ] **SHADOW-04** `[photophore]` — Every generated shadow runs the irreversibility test (hard fail — dispatch aborts if the test fails) and the relevance preservation and distinguishability tests (soft fail — dispatch continues with a warning recorded to audit).
- [ ] **SHADOW-05** `[photophore]` — Tier-0 (`local`) content blocks are stripped from outgoing envelopes; tier-1 (`shared`) blocks are replaced with shadows; tier-2 (`public`) blocks pass through unchanged.
- [ ] **SHADOW-06** `[photophore]` — Shadows are never cached, persisted, or referenced after dispatch — each shadow exists only for the lifetime of one dispatch.

### Photophore Result Policy Authoring — `[photophore]`

- [ ] **POLICY-01** `[photophore]` — `result_policy` for outgoing `task` envelopes is authored on the issuer node before signing; any `result_policy` field in the input draft is ignored.
- [ ] **POLICY-02** `[photophore]` — Result policy is derived from channel ceiling, envelope's declared `output_contract` type and destination, and any explicit policy tags on the task's intent.
- [x] **POLICY-03** `[photophore]` — A negative test confirms that envelopes whose received result violates the authored `result_policy` are rejected at the receipt step.

### Photophore Audit Log — `[photophore]`

- [ ] **AUDIT-01** `[photophore]` — Audit log is append-only — no API exists to delete or modify entries; SQLite triggers enforce append-only behavior; archival is performed by closing the current chain and starting a new chain (the archive remains).
- [ ] **AUDIT-02** `[photophore]` — Each audit entry contains an `algo_version` field (`"blake3-v1"`); verifier code reads this field and dispatches to the appropriate hash function. v0.1 implements only `blake3-v1` but the field and dispatch path are present from day 1.
- [ ] **AUDIT-03** `[photophore]` — Each entry includes a `prev_hash` field equal to the BLAKE3 hash of the canonical-JSON serialization (`thermocline.canonical.canonicalize`) of the previous entry, forming a chain that detects tampering.
- [ ] **AUDIT-04** `[photophore]` — For each dispatched `task` envelope, the audit log records: timestamp, channel ID, remote node ID, envelope ID, tier of each context block, shadow IDs and abstractions generated, classification reason for each block, dispatch signature hash, and (after receipt) receipt signature hash plus result-persist decisions.
- [ ] **AUDIT-05** `[photophore]` — Audit log is queryable by channel, node, tier, date range, shadow ID, envelope ID, and receipt status via `photophore audit query` with both human-readable and JSON Lines output.
- [ ] **AUDIT-06** `[photophore]` — Audit log is exportable as JSON Lines plus a chain-head proof via `photophore audit export`; export format includes `algo_version` so future verifiers can re-validate.
- [ ] **AUDIT-07** `[photophore]` — An `AnchorTarget` Protocol is defined for Ring 3 (blockchain) anchoring; v0.1 ships only the Protocol plus a no-op default implementation; a smoke test confirms dispatch flow works with no-op anchor selected.
- [ ] **AUDIT-08** `[photophore]` — Chain integrity is verifiable on read — querying audit entries verifies the chain over the returned slice and refuses to return entries whose `prev_hash` does not match.

### Photophore Dispatch and Privacy Receipts — `[photophore]`

- [x] **DISP-01** `[photophore]` — The dispatch coordinator orchestrates the full 9-step flow: resolve channel → classify each block → generate shadows / strip tier-0 → author result_policy → write pre-dispatch audit entry → delegate signing to identity provider → send envelope (transport) → verify receipt signature → write receipt audit entry.
- [x] **DISP-02** `[photophore]` — If the pre-dispatch audit write fails, the envelope is not signed and not sent; the dispatch returns `DispatchError.AUDIT_FAILED` and no partial state is observable.
- [x] **DISP-03** `[photophore]` — Receipt signature verification occurs before the receipt is appended to the audit log; if verification fails, the dispatch returns an error and no audit entry referencing the (invalid) receipt is appended; an integration test exercises this with a forged receipt.
- [x] **DISP-04** `[photophore]` — Signing input is canonical-JSON via `thermocline.canonical.canonicalize`; the same envelope produces the same canonical bytes regardless of map ordering or whitespace; a Hypothesis property test asserts canonical-JSON round-trip stability over arbitrary envelope shapes.
- [x] **DISP-05** `[photophore]` — The dispatch module is the only module in `photophore` permitted to perform network I/O (`httpx`); enforced at CI via custom AST lint forbidding `httpx`/`requests`/`aiohttp` imports in `photophore.{classifier,shadow,policy,audit,channels,core}` and in `thermocline.{envelope,canonical,identity,schemes}`.
- [x] **DISP-06** `[photophore]` — Dispatch coordinator is async (`asyncio` + `httpx`); SQLite writes go through `asyncio.to_thread` (or `aiosqlite`) to avoid blocking the event loop.

### Photophore CLI — `[photophore]`

- [ ] **CLI-01** `[photophore]` — `photophore channel` subcommand supports `new`, `list`, `show`, `suspend`, `close`, `set-ceiling` with both human-readable and JSON output.
- [ ] **CLI-02** `[photophore]` — `photophore audit` subcommand supports `query` (with all spec-mandated filters), `export`, `verify` (chain integrity verification of a specified range).
- [x] **CLI-03** `[photophore]` — `photophore dispatch` accepts a Thermocline `task` envelope draft, channel ID, and dispatches per the full 9-step flow.
- [ ] **CLI-04** `[photophore]` — `photophore classify` performs dry-run classification of a path or content blob, prints `(tier, reason)` for each block without dispatching.
- [ ] **CLI-05** `[photophore]` — `photophore policy preview` shows the `result_policy` that would be authored for a given channel + envelope draft, without dispatching.
- [ ] **CLI-06** `[photophore]` — Every CLI subcommand emits an audit log entry recording the operation invoked and its outcome (success/failure); verified by integration test grep over audit DB.
- [ ] **CLI-07** `[photophore]` — Every CLI error message that involves classification or policy includes the relevant `(tier, reason)` so the user can diagnose why a dispatch was blocked or a tier was assigned.

### Seamount Forge Upgrades — `[seamount]`

- [x] **FORGE-01** `[seamount]` — `pi-forge` is upgraded to use `thermocline-py` for all envelope handling — replaces the in-tree `pi-forge/envelope.py` stubs. `key_scheme="brine"` works end-to-end with real PyNaCl signing/verifying via `thermocline-py`.
- [x] **FORGE-02** `[seamount]` — `pi-forge` retains all current task-handling behavior (compute π, statelessness, structured error envelopes); regression-tested by replaying the existing `pi-forge/examples/` fixtures and asserting outputs.
- [x] **FORGE-03** `[seamount]` — A second reference forge (`describe-forge`) is added at `seamount/describe-forge/`. It accepts a `task` envelope with at least one tier-1 shadow in `context[]` and returns a tier-2 templated description like `"This forge received a shadow of type 'document' with relevance 0.85."` Statelessness, structured error envelopes, and receipt signing match `pi-forge` patterns.
- [x] **FORGE-04** `[seamount]` — A cross-suite conformance test harness (`seamount/conformance/`) is published as a runnable Python package (`forge_conformance`) that POSTs envelopes from `thermocline/conformance/` fixtures to a target URL and validates responses against `thermocline/schema/` JSON Schemas, verifying receipt signatures.
- [x] **FORGE-05** `[seamount]` — The conformance harness explicitly maps results to the Seamount conformance checklist (12 items) and emits a structured pass/fail report; CI runs it against `pi-forge` and `describe-forge` on every PR.

### Cross-Suite Hardening and Conformance — `[suite-wide]`

- [ ] **CONF-01** `[suite-wide]` — Conformance test suite passes against `pi-forge` and `describe-forge` for both happy-path and rejection cases.
- [ ] **CONF-02** `[suite-wide]` — At least one negative test exists per AT-* threat-model surface across all three specs: Thermocline AT-C1..C6, Photophore AT-A1..A6, Seamount AT-E1..E5 — 17 surfaces total. Each test documents which surface it exercises.
- [ ] **CONF-03** `[suite-wide]` — Hypothesis property tests cover: classifier default invariant (always `LOCAL` for unmatched), audit chain integrity (any single-byte tamper invalidates), canonical-JSON round-trip stability, shadow ID uniqueness across dispatches of identical content. Each property runs at least 100 generated cases.
- [ ] **CONF-04** `[suite-wide]` — CI gates: `ruff check` (linting), `mypy --strict` (type checking), `pip-audit` (vulnerability scan), custom AST lint enforcing the network-isolation contract (no HTTP imports in classifier/audit/shadow/policy/channels/identity/canonical/envelope), `pytest` (unit + integration), `forge_conformance` against pi-forge and describe-forge.
- [ ] **CONF-05** `[suite-wide]` — Architecture Decision Records (`docs/adr/` in each repo where relevant): Python as primary language, Pydantic v2 lock-in, BLAKE3 with `algo_version` chain, single canonical JSON path, trust-store separation from audit log, no shadow caching, no in-process key material in identity adapter.
- [ ] **CONF-06** `[suite-wide]` — Privacy-critical content types use a `Sensitive[T]` wrapper class with redacting `__repr__`/`__str__`; CI lint forbids `print(` in library code paths; logging uses a privacy-aware filter that drops fields tagged `sensitive=True`.
- [ ] **CONF-07** `[suite-wide]` — Install and ops documentation walks a new user from clone → first dispatch → audit query → audit export on macOS in under 30 minutes; documents platform keystore prerequisites; documents the chain-archival rotation procedure.
- [ ] **CONF-08** `[suite-wide]` — Three coordinated v0.1 git tags exist on `thermocline`, `photophore`, and `seamount`, each with a CHANGELOG describing what's implemented vs. what's deferred (jobs, model classifier, trust score, Ring 2/3, multi-hop, channel negotiation).

## v2 Requirements

Deferred to subsequent milestones (Photophore spec v0.2, v0.3, v0.4, v0.5, v1.0).

### Jobs (Photophore spec v0.2)
- **JOB-01** `[photophore]` — Per-step shadow generation for `job` envelopes (6-step manifest authorship sequence)
- **JOB-02** `[photophore]` — `result_policy` authoring inside the `manifest` block for jobs
- **JOB-03** `[photophore]` — Per-step classification explanations recorded in audit log
- **JOB-04** `[seamount]` — pi-forge / describe-forge / new forges accept `job` envelopes (Seamount Job Execution Engine compliance)

### Federation (Photophore spec v0.2)
- **RING2-01** `[photophore]` — Ring 2 reconciliation protocol — two nodes optionally cross-post audit entries

### Trust Score and Model Classifier (Photophore spec v0.3)
- **SCORE-01** `[photophore]` — Trust score algorithm (six input signals, decay function, threshold table)
- **MODEL-01** `[photophore]` — Model-based classifier (local-only, opt-in, ≤4B params, default-local below confidence threshold)

### Multi-hop and Anchoring (Photophore spec v0.4)
- **HOP-01** `[photophore]` — Multi-hop channels and membrane chaining
- **RING3-01** `[photophore]` — Ring 3 blockchain adapter (chain-agnostic) with Arweave reference implementation

### Granular Trust (Photophore spec v0.5)
- **OVR-01** `[photophore]` — Per-content trust overrides beyond explicit tag system

### Channel Negotiation (Photophore spec v1.0)
- **NEG-01** `[photophore]` — Channel negotiation protocol with cryptographic commitment on both sides

### Cross-Language Implementations (future suite milestone)
- **TS-01** `[thermocline]` — `thermocline-ts` TypeScript reference library
- **RUST-01** `[thermocline / photophore]` — Rust reference implementation (sovereign-node binary)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Receiver-side enforcement of policy | Forge concern; Seamount conformance covers it. Photophore does not enforce on the receiver. |
| Direct key management in any suite component | Spec mandates IdP delegation. `thermocline-py` adapter delegates to platform keystore per signature; Photophore and forges never hold keys. |
| Automatic trust escalation, channel auto-opening, or any non-human trust decision | Foundational design constraint across all three specs. Forever. |
| Cloud or remote inference for content classification | Foundational sovereign-node constraint. Forever. |
| Trust store remote sync, cloud backup, or any remote access path | Foundational design mandate. Forever. |
| Audit log delete/edit APIs | Audit log is the proof; archival starts a new chain; archives remain. Forever. |
| Caching of generated shadows across dispatches | Defeats per-dispatch shadow ID uniqueness; enables AT-C3 / AT-A2. |
| Permissive default tier for unmatched content | Privacy guarantee depends on `local` default. |
| In-process key material in any identity adapter | Defeats the delegation guarantee. Reference adapter calls keystore per signature. |
| Eager classification at content-write time with cached results | Spec mandate: classification runs at dispatch time, every dispatch. |
| GUI / web frontend | Out of scope for v0.1; CLI-first; possible future milestone. |
| Multi-tenant gateway operation | Photophore is a single-node engine. Beyond v0.1's design center. |
| Languages other than Python in v0.1 | Rust, TypeScript, Swift implementations deferred to a future milestone after Python reference is validated. |
| `pi-forge` accepting `job` envelopes | Pi-forge stays task-only in v0.1; job support deferred to a later milestone. |
| `describe-forge` becoming an LLM-backed forge | `describe-forge` stays templated and deterministic in v0.1; LLM-backed forges are a future milestone. |

## Traceability

Which phases cover which requirements. Updated by ROADMAP.md (4 phases, ~10 plans).

| Requirement | Phase | Status |
|-------------|-------|--------|
| THERMO-01..07 | Phase 1 | Pending (THERMO-01 partial: cirdan rename shipped @5c0d87c) |
| IDENT-01..05 | Phase 1 | Pending |
| CHAN-01..06 | Phase 2 | Pending |
| AUDIT-01..08 | Phase 2 | Pending |
| CLASS-01..06 | Phase 2 | Pending |
| SHADOW-01..06 | Phase 2 | Pending |
| POLICY-01..03 | Phase 2 | Pending |
| CLI-01, CLI-02, CLI-04, CLI-05 | Phase 2 | Pending |
| DISP-01..06 | Phase 3 | Pending |
| CLI-03 | Phase 3 | Complete |
| FORGE-01..05 | Phase 3 | Pending |
| CLI-06, CLI-07 | Phase 4 | Pending |
| CONF-01..08 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 67 total (7 THERMO + 5 IDENT + 6 CHAN + 6 CLASS + 6 SHADOW + 3 POLICY + 8 AUDIT + 6 DISP + 7 CLI + 5 FORGE + 8 CONF)

- Mapped to phases: 67
- Unmapped: 0

---
*Requirements defined: 2026-05-05*
*Last updated: 2026-05-05 after suite-wide initialization*
