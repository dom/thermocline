---
gsd_state_version: 1.0
milestone: v0.1
milestone_name: Release
status: executing
stopped_at: Phase 4 context gathered
last_updated: "2026-05-12T00:02:56.480Z"
last_activity: 2026-05-12 -- Phase 4 planning complete
progress:
  total_phases: 4
  completed_phases: 3
  total_plans: 12
  completed_plans: 10
  percent: 83
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-11)

**Core value:** Reveal only what the receiver needs to know, and nothing else — every content block is `local` by default, transmission is the exception earned by explicit human-authored trust, and every boundary crossing produces a verifiable, append-only privacy receipt.
**Current focus:** Phase 04 — hardening, conformance, and v0.1 release (ready to plan)

## Current Position

Phase: 4
Plan: Not started
Status: Ready to execute
Last activity: 2026-05-12 -- Phase 4 planning complete

Progress: [██████████] 100%

## Repos in Scope

| Repo | Role | Path | v0.1 deliverable |
|------|------|------|------------------|
| `thermocline/` | Spec + shared library + planning hub | `~/Projects/dom/thermocline` | `thermocline-py` library; JSON Schema artifacts; spec patches |
| `photophore/` | Policy engine implementation | `~/Projects/dom/photophore` | `photophore` Python package + CLI |
| `seamount/` | Forge implementations | `~/Projects/dom/seamount` | `pi-forge` real-brine upgrade + new `describe-forge` + conformance harness |

Single planning hub at `thermocline/.planning/`. The `photophore/` and `seamount/` repos do not host their own `.planning/`.

## Performance Metrics

**Velocity:**

- Total plans completed: 3
- Average duration: —
- Total execution time: —

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| — | — | — | — |
| 03 | 3 | - | - |

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Init: Implement v0.1 Python reference impl for the entire suite (Thermocline + Photophore + Seamount) as one coordinated milestone.
- Init: Single planning hub at `thermocline/.planning/`.
- Init: Python 3.11+ as the v0.1 implementation language; Pydantic v2 envelope types; PyNaCl for brine signing; RFC 8785 (`rfc8785`) for canonical JSON; SQLite stdlib for audit log; `python-keyring` for platform keystore; BLAKE3 chain hashing with versioned `algo_version`.
- Init: `thermocline-py` lives at `thermocline/python/` (subdirectory of spec repo, mirroring `seamount/pi-forge/`).
- Out-of-band before Phase 1: spec patch renaming `cirdan` → `thermocline` JSON schema field shipped at `thermocline@5c0d87c`.
- Phase 3: photophore.dispatch is the only network-IO surface — enforced via AST lint (DISP-05) with allow-list for `dispatch/`, `cli/dispatch_cmds.py`, `cli/channel_cmds.py` (TOFU `--fetch-pubkey-from`). 12-subcode DispatchError family maps to CLI exit code 6.
- Phase 3: AT-A1 fail-closed at dispatch step 1 — envelope missing or mismatched `dispatch_signature.key_scheme` is rejected before any audit-pre/sign/transport. MANIFEST records `phase_wired: 3`.
- Phase 3: cross-suite `forge_conformance` package maps Seamount's 8 conformance + 5 AT-E items (13 total; REQUIREMENTS FORGE-05 text said 12 — implementation aligns with Seamount README normative source).
- Phase 3: three coordinator-internal envelope adaptations surfaced (SP-3.3-01..03 in 03-03 SUMMARY) — strip `receipt_signature.sig` before re-canonicalize for verify; pre-fill all non-sig dispatch_signature fields before signing; accept both `sig` and `bytes_hex` for receipt sig field.

### Pending Todos

None yet.

### Blockers/Concerns

- **[Phase 4] Apple Silicon Secure Enclave**: full coverage needs physical Apple Silicon + developer signing identity. Plan: add Secure Enclave entry tests in Phase 4.
- **[Phase 4] Conformance fixture provenance**: Phase 4 needs canonical conformance fixtures across all three specs. Phase 3 produced the integration corpus; Phase 4 freezes them and adds the remaining 16 AT-* negative tests.
- **[Phase 4 follow-up] Three cross-impl spec patches surfaced in Phase 3** (SP-3.3-01..03): receipt-signature canonicalization invariant (strip `sig` before re-canonicalize), dispatch_signature pre-fill ordering, and `sig`/`bytes_hex` receipt field tolerance. Decide whether to ship as spec README amendments or leave coordinator-internal.

## Deferred Items

Items acknowledged and carried forward to subsequent milestones:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Spec roadmap | Per-step shadow generation for `job` envelopes (Photophore spec v0.2) | Deferred | Init (2026-05-05) |
| Spec roadmap | `result_policy` authoring inside job manifests (Photophore spec v0.2) | Deferred | Init (2026-05-05) |
| Spec roadmap | Ring 2 reconciliation protocol (Photophore spec v0.2) | Deferred | Init (2026-05-05) |
| Spec roadmap | Trust score algorithm; model-based classifier (Photophore spec v0.3) | Deferred | Init (2026-05-05) |
| Spec roadmap | Multi-hop channels; Ring 3 / Arweave anchor (Photophore spec v0.4) | Deferred | Init (2026-05-05) |
| Spec roadmap | Per-content trust overrides (Photophore spec v0.5) | Deferred | Init (2026-05-05) |
| Spec roadmap | Channel negotiation protocol (Photophore spec v1.0) | Deferred | Init (2026-05-05) |
| Languages | Rust / TypeScript / Swift reference impls | Deferred | Init (2026-05-05) |
| Forges | `pi-forge` accepting `job` envelopes | Deferred | Init (2026-05-05) |
| Forges | LLM-backed reference forges | Deferred | Init (2026-05-05) |

## Session Continuity

Last session: 2026-05-11T19:39:42.033Z
Stopped at: Phase 4 context gathered
Resume file: .planning/phases/04-hardening-conformance-and-v0-1-release/04-CONTEXT.md
