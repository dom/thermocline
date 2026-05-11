---
gsd_state_version: 1.0
milestone: v0.1
milestone_name: Release
status: executing
stopped_at: Phase 3 context gathered
last_updated: "2026-05-11T08:59:02.703Z"
last_activity: 2026-05-11
progress:
  total_phases: 4
  completed_phases: 2
  total_plans: 10
  completed_plans: 9
  percent: 90
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-05)

**Core value:** Reveal only what the receiver needs to know, and nothing else — every content block is `local` by default, transmission is the exception earned by explicit human-authored trust, and every boundary crossing produces a verifiable, append-only privacy receipt.
**Current focus:** Phase 03 — photophore-dispatch-seamount-upgrade-the-integration-phase

## Current Position

Phase: 03 (photophore-dispatch-seamount-upgrade-the-integration-phase) — EXECUTING
Plan: 2 of 3
Status: Ready to execute
Last activity: 2026-05-11

Progress: [█████████░] 90%

## Repos in Scope

| Repo | Role | Path | v0.1 deliverable |
|------|------|------|------------------|
| `thermocline/` | Spec + shared library + planning hub | `~/Projects/dom/thermocline` | `thermocline-py` library; JSON Schema artifacts; spec patches |
| `photophore/` | Policy engine implementation | `~/Projects/dom/photophore` | `photophore` Python package + CLI |
| `seamount/` | Forge implementations | `~/Projects/dom/seamount` | `pi-forge` real-brine upgrade + new `describe-forge` + conformance harness |

Single planning hub at `thermocline/.planning/`. The `photophore/` and `seamount/` repos do not host their own `.planning/`.

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: —
- Total execution time: —

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| — | — | — | — |

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

### Pending Todos

None yet.

### Blockers/Concerns

- **`describe-forge` design**: Phase 3 needs a small design spike to confirm "shadow → templated description" is substantive enough to exercise tier-1 handling without bloating into an LLM-backed forge. Plan: spike at start of Phase 3.
- **Apple Silicon Secure Enclave**: full coverage needs physical Apple Silicon + developer signing identity. Plan: target macOS 12+ via standard Keychain in Phase 1; add Secure Enclave entry tests in Phase 4.
- **Conformance fixture provenance**: Phase 4 needs canonical conformance fixtures across all three specs. Some can be authored fresh in Phase 1 (`thermocline/conformance/`); others are derived in Phase 3 from real Photophore→forge integration tests, then frozen.

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

Last session: 2026-05-11T03:38:57.758Z
Stopped at: Phase 3 context gathered
Resume file: .planning/phases/03-photophore-dispatch-seamount-upgrade-the-integration-phase/03-CONTEXT.md
