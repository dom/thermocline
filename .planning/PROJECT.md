# Thermocline Suite

## What This Is

The **Thermocline Suite** is the privacy-tiered task-dispatch architecture for distributed AI nodes — a coordinated set of three open specifications and their Python reference implementations. **Thermocline** defines the envelope contract and the role architecture (sovereign node, policy engine, identity provider, forge, memory store). **Photophore** implements the policy-engine role: zero-trust classification, dispatch-time shadow generation, result-policy authoring, and an append-only cryptographically chained audit log. **Seamount** defines the forge role and ships **pi-forge** as the simplest possible compliant forge. The v0.1 milestone for this planning hub is to deliver a complete, working, end-to-end reference implementation of the suite in Python — sovereign node → policy engine → signed envelope → forge → signed result → privacy receipt — with cross-suite conformance fixtures any third-party implementation can run against.

## Core Value

**Reveal only what the receiver needs to know, and nothing else.** Every content block is `local` by default. Transmission is the exception, earned by explicit human-authored trust. Every boundary crossing produces a verifiable, append-only privacy receipt — proof that the originating node applied its declared policy, the receiving node operated only on what the envelope contained, and no tier-0 content crossed the boundary. If everything else fails, this must hold: tier-0 (`local`) content never leaves the sovereign node, and the audit log proves that property.

## Requirements

### Validated

(None yet — ship to validate)

### Active

The v0.1 milestone of this planning hub spans three repos. Each item below is a hypothesis until shipped:

**Thermocline (spec + shared library)**
- [ ] Tighten the v0.3.0-draft spec (cirdan→thermocline patch already landed; subsequent ambiguity fixes as discovered during impl)
- [ ] Publish JSON Schema artifacts for every envelope shape (task, task_result, job, job_result, error) under `thermocline/schema/`
- [ ] Build `thermocline/python/` reference library: envelope types, canonical-JSON, brine ed25519 signing/verifying, IdentityProvider interface + platform-keystore reference adapter, conformance fixtures
- [ ] Package as `thermocline-py` for `pip install` (source at `thermocline/python/`)

**Photophore (policy-engine implementation)**
- [ ] Channel registry with explicit trust ceilings, full lifecycle (PROPOSED → OPEN → SUSPENDED → CLOSED), backed by the platform secure keystore (separate from SQLite by mandate)
- [ ] Three-tier classification with strict priority order (Explicit Tag → Path Rule → Classifier), v0.1 rule-based classifier, conservative `local` default
- [ ] Dispatch-time shadow generation with per-content-type abstraction strategies and three quality tests (irreversibility hard fail; relevance and distinguishability soft warn)
- [ ] `result_policy` authoring on outgoing `task` envelopes
- [ ] Append-only cryptographically chained audit log (Ring 1, SQLite + BLAKE3 with versioned `algo_version`)
- [ ] Privacy receipts: dispatch-signature emission + receipt-signature verification (delegated through `thermocline-py` IdentityProvider)
- [ ] Dispatch coordinator orchestrating the 9-step flow end-to-end
- [ ] CLI: `photophore channel | audit | classify | policy | dispatch`
- [ ] Anchoring hook (interface only — Ring 3 deferred to v0.4)

**Seamount (forge upgrades)**
- [ ] Upgrade `pi-forge` from `key_scheme: none` stubs to real `brine` (ed25519) signing and verification via `thermocline-py`
- [ ] Add a second reference forge that exercises tier-1 shadow handling (pi-forge is tier-2-only by task design); proposed: `describe-forge` that accepts a shadow + relevance and returns a templated description
- [ ] Cross-suite conformance test harness any forge implementation can run

**Suite-wide**
- [ ] End-to-end integration test: Photophore sovereign node → real-brine signed dispatch → upgraded `pi-forge` → verified receipt → audit-log entries
- [ ] Three coordinated v0.1 git tags (one per repo) released together

### Out of Scope

**By spec roadmap (deferred to subsequent milestones, not v0.1):**
- Per-step shadow generation for `job` envelopes (Photophore spec v0.2)
- Result-policy authoring inside job manifests (Photophore spec v0.2)
- Ring 2 reconciliation protocol (Photophore spec v0.2)
- Model-based classifier (Photophore spec v0.3 — opt-in, local-only)
- Trust score algorithm (Photophore spec v0.3)
- Multi-hop channels and membrane chaining (Photophore spec v0.4)
- Ring 3 blockchain anchor / Arweave reference impl (Photophore spec v0.4)
- Per-content trust overrides beyond explicit tags (Photophore spec v0.5)
- Channel negotiation protocol (Photophore spec v1.0)

**By design — forever:**
- Automatic trust escalation, channel auto-opening, or any non-human trust decision (Thermocline + Photophore design constraint)
- Cloud or remote inference for content classification (sovereign-node-only constraint)
- Trust-store remote sync, cloud backup, or any remote access path (Photophore design mandate)
- Audit-log delete/edit APIs (audit log is the proof; archival is the only "cleanup")
- Caching of generated shadows across dispatches (defeats AT-C3 / AT-A2 mitigations)
- Permissive default tier for unmatched content (conservative `local` is the privacy guarantee)
- In-process key material in any suite implementation (delegation to platform keystore, every signature)
- Eager classification at content-write time (Thermocline mandate: dispatch-time only)

**By project scope:**
- Receiver-side enforcement of policy (forge concern; Seamount/forge spec covers it, but Photophore does not enforce on the receiver)
- Multi-tenant gateway operation (Photophore is a single-node engine)
- GUI / web frontend (CLI-first; future milestone)
- Languages other than Python in v0.1 (Rust, TypeScript, Swift impls are deferred to a future milestone after the Python reference impl is validated)

## Context

- **Three companion specs at v0.3.0-draft**: Thermocline (envelope), Photophore (policy engine), Seamount (forge). All RFC, MIT licensed, seeking feedback. The reference Python implementations are part of validating the specs.
- **`pi-forge` already exists** at `seamount/pi-forge/` — Flask-based, computes π to N digits, Thermocline-compliant *except* that `brine` (ed25519) signing/verifying is stubbed. It's a tier-2-only forge by task design. v0.1 work upgrades it to real signing and adds a second forge that exercises tier-1 shadows.
- **Five roles in Thermocline** (composable; one machine can play several): Sovereign Node · Policy Engine · Identity Provider · Forge · Memory Store. Photophore implements Policy Engine; pi-forge implements Forge; the IdentityProvider is shared library code in `thermocline-py`.
- **Three pillars of Photophore**: Channel Store (who do I trust, what may they receive?) ↔ Trust Score (how is that trust performing?) ↔ Audit Log (what did I actually do?). Audit log is first-class infrastructure, not supporting.
- **Privacy receipts** are the cryptographic round-trip proof: dispatch signature + receipt signature together prove the originating node applied its policy and the receiver operated only on what the envelope contained. Both signatures are recorded in the audit log.
- **Threat models** spans three specs: Thermocline AT-C1..C6 (envelope-layer attacks), Photophore AT-A1..A6 (policy-engine attacks), Seamount AT-E1..E5 (forge attacks). v0.1 conformance tests exercise each surface.
- **The "Last Moat" thesis** (non-normative Photophore appendix): in a world where anything can be generated, human relationships are the only remaining moat. The suite exists to make trust expressible, auditable, and worth having.

## Constraints

- **Spec compliance**: Implementations MUST conform to Thermocline 0.3.0+, Photophore 0.3.0+, and Seamount 0.3.0+. The READMEs are the source of truth; deviations require spec amendment in the respective repo.
- **Language — Python 3.11+**: aligns with `pi-forge` (existing reference impl) and Thermocline's planned `thermocline-py` registry entry. Single-language reference impl reduces cross-impl drift; later languages (Rust, TypeScript, Swift) are deferred.
- **Tech — sovereign-node-only**: Photophore classifier and trust store run entirely on the sovereign node. No cloud inference for classification, ever. No remote sync of the trust store, ever.
- **Tech — storage**: audit log is append-only SQLite with cryptographic chaining (`algo_version`-tagged BLAKE3, each entry hashes the previous). Trust store backed by the platform secure keystore (Keychain on macOS, libsecret on Linux, Credential Manager on Windows) — never co-located with the audit log.
- **Tech — keys**: no implementation in the suite manages keys directly. All signing/verifying is delegated to the IdentityProvider interface defined in `thermocline-py` and backed by the platform keystore. Reference adapter never copies key material out of the keystore.
- **Tech — wire format**: `thermocline-py` envelope serialization for *signing input* uses canonical JSON (RFC 8785 / JCS). Non-canonical JSON for signing is a known break-the-signature bug class.
- **Compatibility**: macOS first-class (Apple Silicon Secure Enclave where available); Linux secondary (libsecret with D-Bus session); Windows secondary (Credential Manager).
- **Security — classifier asymmetry**: false negatives (private content stays private) are acceptable; false positives (private content classified as safe) are never acceptable. Classifier defaults all unmatched content to `local`.
- **Security — trust ceiling monotonicity**: ceilings may be lowered unilaterally at any time; raised only by deliberate human act, recorded as a distinct audit event.
- **Security — issuer-authored result policy**: forge cannot modify or escalate. v0.1 covers `task` envelopes; `manifest`-embedded policies are v0.2.
- **Security — audit log immutability**: append-only by construction (SQLite trigger enforced); no delete API; archival starts a new chain — the archive remains.
- **Single planning hub**: this `.planning/` directory in `thermocline/` is the single source of truth for planning across all three repos. Photophore and Seamount repos do not host their own `.planning/`.
- **License**: MIT across all three repos.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Implement v0.1 Python reference for the entire suite (Thermocline + Photophore + Seamount) as one coordinated milestone | The three specs are co-dependent; staggered impls would drift. One coordinated push validates all three specs together. | — Pending |
| Single planning hub at `thermocline/.planning/` (not per-repo) | User directive. Avoids three GSD instances; keeps cross-repo work-item dependencies legible. | ✓ Good |
| Python 3.11+ as the v0.1 implementation language | Matches `pi-forge` (existing reference) and Thermocline's planned `thermocline-py` entry; lowest barrier for users to read/extend the reference impl. Other languages deferred. | ✓ Good |
| `thermocline-py` shared library lives at `thermocline/python/` (subdirectory of spec repo, mirroring `seamount/pi-forge/`) | Spec changes can land with library changes in the same commit/PR. Avoids fourth repo and separate release cycle. Packageable as `thermocline-py` on PyPI. | ✓ Good |
| Spec patch (cirdan→thermocline JSON field rename) committed in-place at v0.3.0-draft | Pre-release RFC; pi-forge already used `thermocline` as the field. Patch aligns the spec with reference impl and the spec's own Versioning prose. | ✓ Good (committed thermocline@5c0d87c) |
| Use BLAKE3 with versioned `algo_version="blake3-v1"` for the audit log chain | Faster than SHA-256, modern; the version tag prevents future migration lock-in. | — Pending |
| Use PyNaCl (libsodium) for ed25519 brine signing in `thermocline-py` | Mature, audited libsodium bindings; smaller surface than `cryptography` for our needs (signing only). | — Pending |
| Use Pydantic v2 for envelope types in `thermocline-py` | Fast, ergonomic, generates JSON Schema for free, idiomatic Python type-checking | — Pending |
| Use `keyring` (Python) for platform keystore access | Cross-platform wrapper for Keychain / libsecret / Credential Manager, mature. | — Pending |
| `pi-forge` upgrade and a new tier-1-shadow-exercising forge ship together in Phase 3 | The existing `pi-forge` is tier-2-only; a second forge is needed to actually exercise the privacy primitive end-to-end. | ✓ Done (Phase 3) |
| Trust is never automated — Photophore only suggests, the human always decides | Foundational design constraint (Photophore Constraint 2; Thermocline role separation). Not negotiable. | ✓ Good |
| Zero-trust default — every content block starts as `local`, no permissive default exists | Foundational design constraint (Photophore Constraint 1). Privacy guarantee depends on this asymmetry. | ✓ Good |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-11 — Phase 3 complete: photophore.dispatch 9-step coordinator + AT-A1 fail-closed, pi-forge real brine + describe-forge tier-1, forge_conformance harness mapped to Seamount 13-item checklist, CI gates wired across photophore + seamount; 362 tests passing; 23/23 must-haves verified.*
