# Roadmap: Thermocline Suite v0.1

## Overview

The journey is from three published specs at v0.3.0-draft (Thermocline · Photophore · Seamount) to a complete, working, end-to-end Python reference implementation of all three — proving the specs are implementable and interoperable. We start from existing scaffolding (`seamount/pi-forge/`, a Flask forge with stubbed crypto) and build outward in concentric rings: Phase 1 ships the `thermocline-py` shared library (envelope types, canonical JSON, brine signing, IdentityProvider Protocol, JSON Schema artifacts) — the foundation every other component depends on. Phase 2 builds Photophore's privacy primitives (channels, classifier, shadow generator, policy authoring) on top of the audit log foundation, all in `photophore/python/`. Phase 3 integrates everything: Photophore's dispatch coordinator drives a real round-trip against the upgraded `pi-forge` (real brine signing) and a new `describe-forge` (the first reference forge that exercises tier-1 shadow handling). Phase 4 hardens the surface with property tests, threat-model negative tests across 17 AT-* surfaces, ADRs, ops docs, and three coordinated v0.1 git tags.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3, 4): Planned milestone work
- Decimal phases (e.g., 2.1): Reserved for urgent insertions only (none planned)

- [x] **Phase 1: `thermocline-py` Foundations** — Shared library (envelope types, canonical JSON, brine, IdentityProvider) + JSON Schema artifacts + spec patches. Lives in `thermocline/python/`. (completed 2026-05-09)
- [x] **Phase 2: Photophore Privacy Primitives + Foundations** — Channels (trust store), audit log (chained), classifier, shadow generator, policy authoring. Lives in `photophore/python/`. (completed 2026-05-10)
- [ ] **Phase 3: Photophore Dispatch + Seamount Upgrade** — End-to-end integration: dispatch coordinator + `pi-forge` real brine + new `describe-forge`. Spans `photophore/` and `seamount/`.
- [ ] **Phase 4: Hardening, Conformance, and v0.1 Release** — Property tests + 17 AT-* negative tests + cross-suite conformance harness + ADRs + ops docs + three coordinated v0.1 git tags.

## Phase Details

### Phase 1: `thermocline-py` Foundations

**Goal**: Establish the foundation library every other suite component depends on. `thermocline-py` defines the envelope types (Pydantic v2), the single canonical-JSON path used for all signature input (RFC 8785), the `IdentityProvider` Protocol with a real PyNaCl-backed brine reference adapter (`python-keyring` for key material), and the JSON Schema artifacts that any third-party impl can validate against. Forever-decisions land here: Pydantic v2 lock-in, canonical-JSON discipline, IdentityProvider returning `Signature` (never `PrivateKey`), `Receipt` constructible only via `verify`.

**Repos**: `thermocline/`

**Depends on**: Nothing (first phase)

**Requirements**:
- THERMO-01, THERMO-02, THERMO-03, THERMO-04, THERMO-05, THERMO-06, THERMO-07
- IDENT-01, IDENT-02, IDENT-03, IDENT-04, IDENT-05

**Success Criteria** (what must be TRUE):
  1. `pip install -e ./thermocline/python` succeeds on a fresh Python 3.11+ environment; importing `thermocline` exposes envelope types, `canonicalize`, `IdentityProvider`, and the brine reference adapter.
  2. A round-trip test using `thermocline-py` only (no Photophore yet) — build a `task` envelope, canonicalize, sign with the brine adapter (real PyNaCl + macOS Keychain), verify the signature — produces a `Receipt` instance; tampering with any envelope byte invalidates verification.
  3. JSON Schema files exist under `thermocline/schema/` for `task`, `task_result`, `job`, `job_result`, `error`; a fixture envelope from `thermocline/conformance/valid/` validates against the corresponding schema; an invalid fixture from `thermocline/conformance/invalid/` fails validation with a structured error.
  4. The IdentityProvider reference adapter, when configured for `brine`, refuses to start if `python-keyring` cannot reach the platform secure keystore (no fall-back to file/env-var storage); a Hypothesis property test asserts canonical-JSON round-trip stability over arbitrary envelope shapes.
  5. `Receipt` cannot be constructed except via `IdentityProvider.verify` returning success — verified by direct attempt (e.g., `Receipt(...)` raises `TypeError`) and by static type-check (`mypy --strict` passes on a deliberate misuse fixture).

**Plans**: 4 plans

Plans:
- [x] 01-01: Workspace skeleton + `thermocline/python/` package scaffold + envelope types (Pydantic v2) for task / task_result / job / job_result / error + JSON Schema artifact generation under `thermocline/schema/`.
- [x] 01-02: Canonical JSON (`thermocline.canonical.canonicalize` via `rfc8785`) + Hypothesis round-trip stability tests + canonical-JSON CI lint forbidding `json.dumps` outside explicitly non-signing paths.
- [x] 01-03: `IdentityProvider` Protocol + brine reference adapter (PyNaCl + python-keyring) + key-scheme dispatch on verify + `Receipt` value type with private constructor + initial conformance fixture set under `thermocline/conformance/{valid,invalid}/`.
- [x] 01-04: Gap closure for BL-01..BL-04 — separate public-key store on `BrineProvider` (cross-role verify), nested `key_scheme` lookup in `Verifier.verify` for real Task / TaskResult envelopes, `isinstance` keystore probe against real `keyring.backends.fail.Keyring` / `null.Keyring`, and clobber-safe `generate()` + explicit `rotate()`.

---

### Phase 2: Photophore Privacy Primitives + Foundations

**Goal**: Build Photophore's privacy-critical components in isolation. Audit log (the chained, append-only foundation) and channel registry (trust store via platform keystore) land first because every other component writes through them. Classifier, shadow generator, and policy authoring follow as pure functions (no I/O) — testable in isolation, easy to property-test. The CLI ships its non-dispatch surface (channel, audit, classify, policy preview) so users can interact with the engine end-to-end before dispatch arrives.

**Repos**: `photophore/`

**Depends on**: Phase 1 (uses `thermocline-py` envelope types and IdentityProvider Protocol)

**Requirements**:
- CHAN-01, CHAN-02, CHAN-03, CHAN-04, CHAN-05, CHAN-06
- AUDIT-01, AUDIT-02, AUDIT-03, AUDIT-04, AUDIT-05, AUDIT-06, AUDIT-07, AUDIT-08
- CLASS-01, CLASS-02, CLASS-03, CLASS-04, CLASS-05, CLASS-06
- SHADOW-01, SHADOW-02, SHADOW-03, SHADOW-04, SHADOW-05, SHADOW-06
- POLICY-01, POLICY-02, POLICY-03
- CLI-01, CLI-02, CLI-04, CLI-05

**Success Criteria** (what must be TRUE):
  1. User can run `photophore channel new --remote-node <id> --ceiling tier-1 --key-scheme brine` and the channel appears in `photophore channel list` with status PROPOSED; lifecycle transitions advance through OPEN, SUSPENDED, CLOSED with each transition recorded as an audit log entry before reporting success.
  2. The trust store persists across process restarts via `python-keyring` (macOS Keychain) and is demonstrably not present in the SQLite audit database (separate backing stores enforced); `photophore audit query --channel <id>` returns chronologically ordered entries with chain integrity verified over the slice.
  3. `photophore classify <path>` emits `(tier, reason)` per block, where reason is one of `explicit_tag`, `path_rule:<pattern>`, `classifier:<rule>`, `classifier:default`; explicit tags demonstrably override path rules, which override the rule-based classifier; a Hypothesis property test asserts unmatched blocks are always `(LOCAL, ClassifierDefault)`.
  4. Generating a shadow over arbitrary content produces a unique `shadow_id` per call (over `os.urandom`); abstraction strings that fail the irreversibility test are rejected before being returned; per-content-type strategies for document/conversation/credential/file/identity/code each produce schema-valid abstractions per the v0.3 quality table; loading a path-rules config without the mandatory `**` → `local` catch-all is refused with a specific error.
  5. `photophore policy preview --channel <id> --task <draft.json>` shows the `result_policy` derived from channel ceiling + envelope draft; any `result_policy` field present in the input draft is ignored; a fixture confirms tier-0 stripping, tier-1 → shadow replacement, and tier-2 passthrough in the in-memory envelope view.

**Plans**: 3 plans

Plans:
- [x] 02-01: `photophore/python/` package scaffold + `core` types + `audit` (SQLite chained log with `algo_version="blake3-v1"`, append-only triggers, `AnchorTarget` Protocol with no-op default, query/export, `photophore audit` CLI) + `channels` (trust store via `python-keyring`, lifecycle, ceiling rules, `photophore channel` CLI).
- [x] 02-02: `classifier` (explicit tag parser + path-rule engine with mandatory catch-all validation + rule-based v0.1 classifier with explicit `default_tier()`) + `photophore classify` CLI subcommand + Hypothesis property test for default invariant.
- [x] 02-03: `shadow` (per-content-type abstraction strategies + irreversibility hard-fail + relevance/distinguishability soft-warn + UUIDv4 over `os.urandom` shadow IDs) + `policy` (`result_policy` authoring from channel + envelope draft for `task` envelopes only — manifest authoring deferred) + `photophore policy preview` CLI subcommand.

---

### Phase 3: Photophore Dispatch + Seamount Upgrade (the integration phase)

**Goal**: Integrate everything into a real, working privacy-receipt round trip. Photophore's dispatch coordinator runs the 9-step flow end-to-end. `pi-forge` is upgraded from `key_scheme="none"` stubs to real `brine` signing/verifying via `thermocline-py`. A new `describe-forge` is added to actually exercise tier-1 shadow handling (since `pi-forge` is tier-2-only by task design). The integration test is Photophore → upgraded `pi-forge` AND Photophore → `describe-forge` → verified receipts → audit-log entries — proving all three specs hang together.

**Repos**: `photophore/`, `seamount/`

**Depends on**: Phase 1 (`thermocline-py`) and Phase 2 (Photophore primitives)

**Requirements**:
- DISP-01, DISP-02, DISP-03, DISP-04, DISP-05, DISP-06
- CLI-03
- FORGE-01, FORGE-02, FORGE-03, FORGE-04, FORGE-05

**Success Criteria** (what must be TRUE):
  1. User can run `photophore dispatch --channel <id> --task <draft.json>` and the system executes the full 9-step flow: resolve channel → classify → shadow → policy → audit-pre → sign → send → verify-receipt → audit-post; on success the user sees a receipt summary including the verified signature hash; the audit log shows two entries (pre-dispatch, receipt) with a verified chain link.
  2. A test forge that returns a forged receipt signature causes the dispatch to fail with `DispatchError.RECEIPT_INVALID`; no audit log entry references the forged receipt; an integration test exercises this path. A pre-dispatch audit write failure (induced via a poisoned audit DB) aborts the dispatch before signing.
  3. `pi-forge` with `FORGE_KEY_SCHEME=brine` signs receipts with real PyNaCl using a key from its own platform keystore entry; Photophore (with its own brine adapter and the forge's public key registered) verifies these receipts successfully; running `pi-forge`'s existing `examples/task-100-digits.json` end-to-end through Photophore produces an equivalent (modulo IDs/timestamps) `task_result` envelope.
  4. `describe-forge` accepts a `task` envelope with at least one tier-1 shadow in `context[]`, returns a tier-2 templated description referencing the shadow's content_type and relevance, and returns a real-brine-signed receipt; an end-to-end Photophore → describe-forge dispatch where the source content is `tier=1` produces a shadow on the wire and a verified description in the result.
  5. The network-isolation contract is enforced as a CI gate (custom AST lint): `photophore.{classifier,shadow,policy,audit,channels,core}` and `thermocline.{envelope,canonical,identity,schemes}` have no transitive HTTP imports; only `photophore.dispatch` and the forge `server.py` files import `httpx`/`requests`/`flask`. Lint fails the build on violation.

**Plans**: 3 plans
**Phase Mode:** standard

Plans:
- [ ] 03-01: `photophore.dispatch` async coordinator (9-step flow with type-enforced receipt verification gate, canonical-JSON via `thermocline-py`, audit-pre/audit-post hard-fail semantics, POLICY-03 partial-closure wire-in, AT-A1 behavioral wire-in) + `photophore dispatch` CLI subcommand (exit code 6 family, 12 DispatchError subcodes per CONTEXT D-03) + custom AST lint enforcing the network-isolation contract (DISP-05). Photophore-only.
- [ ] 03-02: Upgrade `seamount/pi-forge/` to use `thermocline-py` for envelope handling + real `brine` signing/verifying (retires `envelope.py:_verify_brine` stub at lines 87–99 and `envelope.py:_sign_receipt` stub at lines 139–165; keeps `key_scheme="none"` as a configurable dev-mode option via `FORGE_KEY_SCHEME=none`) + add `seamount/describe-forge/` (Flask handler returning the normative templated description per CONTEXT D-02; tier-1-required; mixed-tier ignore-inline). Both forges ship `init` subcommand + `GET /pubkey` endpoint + per-forge keystore namespace (`seamount.piforge` / `seamount.describeforge`) per CONTEXT D-01. Seamount-only.
- [ ] 03-03: End-to-end integration tests (Photophore → pi-forge + Photophore → describe-forge happy paths over real HTTP via `subprocess_forge` fixture; forged-receipt + poisoned-audit + policy-violated negative tests; AT-A1 fixture replay over real HTTP) + cross-suite conformance harness `seamount/conformance/forge_conformance/` mapped to the Seamount 12-item checklist (FORGE-04, FORGE-05) + CI workflow wiring (matrix step `forge: [pi-forge, describe-forge]` in both `photophore/` and `seamount/` CI). Cross-cutting.

Plan split decision (03-CONTEXT.md D-05): split for repo-boundary cleanness and balanced plan size (Phase 2 LEARNINGS noted 02-03 grew uncomfortably large; this split prevents recurrence). 03-01 and 03-02 touch different repos with no shared file edits and run in parallel (wave 0); 03-03 depends on both and runs in wave 1.

---

### Phase 4: Hardening, Conformance, and v0.1 Release

**Goal**: Validate that the suite actually meets all three specs and all three threat models. Hypothesis property tests for the four critical invariants (≥100 cases each). Negative tests for each AT-* surface across all three specs (17 surfaces total: Thermocline AT-C1..C6, Photophore AT-A1..A6, Seamount AT-E1..E5). Cross-suite conformance test harness any forge can run, mapped to the Seamount conformance checklist. ADRs document the forever-decisions. Ops/install docs walk a user through the full lifecycle. Three coordinated v0.1 git tags.

**Repos**: `thermocline/`, `photophore/`, `seamount/` (all three)

**Depends on**: Phase 3

**Requirements**:
- CLI-06, CLI-07
- CONF-01, CONF-02, CONF-03, CONF-04, CONF-05, CONF-06, CONF-07, CONF-08

**Success Criteria** (what must be TRUE):
  1. CI is green on a clean clone of all three repos: `ruff check`, `mypy --strict`, `pip-audit`, custom AST lint enforcing the network-isolation contract, `pytest`, and `forge_conformance` against `pi-forge` and `describe-forge`.
  2. Hypothesis property tests cover the four critical invariants with ≥100 cases each: classifier default fallthrough is `LOCAL`, audit chain integrity (any single-byte tamper invalidates the chain), canonical-JSON round-trip stability, shadow ID uniqueness across dispatches of identical content.
  3. At least one negative test exists per AT-* threat-model surface (Thermocline AT-C1..C6, Photophore AT-A1..A6, Seamount AT-E1..E5 = 17 surfaces total); each test documents which surface it exercises and what failure mode it asserts; CI counts AT-* coverage and fails if any surface has zero coverage.
  4. ADRs (one page or less each, cross-linked from each repo's README) exist for: Python as primary language, Pydantic v2 lock-in, BLAKE3 with `algo_version` chain, single canonical JSON path (`thermocline.canonical.canonicalize`), trust-store separation from audit log, no shadow caching, no in-process key material; the "looks done but isn't" checklist from PITFALLS.md is verified end-to-end across all three repos.
  5. Install/ops docs walk a new user from `git clone` → first dispatch → audit query → audit export on macOS in under 30 minutes; three coordinated v0.1 git tags exist (`thermocline v0.1.0`, `photophore v0.1.0`, `seamount v0.1.0`) each with a CHANGELOG describing what's implemented vs. what's deferred (jobs, model classifier, trust score, Ring 2/3, multi-hop, channel negotiation, non-Python impls).

**Plans**: 2 plans

Plans:
- [ ] 04-01: Hypothesis property test suite for the four invariants + 17 AT-* negative tests with CI-counted coverage + `seamount/conformance/` standalone harness package + CI gates (`ruff`, `mypy --strict`, `pip-audit`, custom AST network-isolation lint) wired into all three repos' workflows.
- [ ] 04-02: ADR documents in `thermocline/docs/adr/`, `photophore/docs/adr/`, `seamount/docs/adr/` + `Sensitive[T]` audit across content-bearing types + `print(` lint + `logging` redacting filter + ops/install documentation in each repo's README + three coordinated v0.1 git tags with CHANGELOGs.

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. `thermocline-py` Foundations | 4/4 | Complete   | 2026-05-09 |
| 2. Photophore Privacy Primitives + Foundations | 3/3 | Complete   | 2026-05-10 |
| 3. Photophore Dispatch + Seamount Upgrade | 0/3 | Not started | - |
| 4. Hardening, Conformance, and v0.1 Release | 0/2 | Not started | - |

**Coverage:** 67 of 67 v1 requirements mapped to phases ✓
**Repos:** thermocline · photophore · seamount (cross-repo work tagged per-requirement in REQUIREMENTS.md)

## Out-of-band

Already shipped before Phase 1 began:
- `thermocline@5c0d87c` — spec patch renaming `cirdan` → `thermocline` schema field (THERMO-01 partial; spec correction).
