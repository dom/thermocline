# Project Research Summary

**Project:** Thermocline Suite v0.1 Python reference implementation
**Domain:** Privacy-tiered task-dispatch architecture for distributed AI nodes (envelope spec + policy engine + forge)
**Researched:** 2026-05-05
**Confidence:** HIGH

## Executive Summary

The Thermocline Suite is three co-dependent open specifications (Thermocline · Photophore · Seamount), all currently at v0.3.0-draft, plus their Python reference implementations. This planning hub coordinates v0.1 of the *implementation* milestone — to deliver a complete, working, end-to-end reference impl in Python that proves all three specs are implementable and interoperable. We start from the existing `seamount/pi-forge/` (a Flask-based Thermocline-compliant forge with stubbed crypto) and build out: a shared `thermocline-py` library (envelope types, canonical JSON, brine signing, IdentityProvider interface, JSON Schema artifacts); the full `photophore` Python package (channels, classifier, shadow generator, policy authoring, audit log, dispatch coordinator, CLI); a real-brine upgrade to `pi-forge` plus a second tier-1-shadow-exercising forge (`describe-forge`); and a cross-suite conformance test harness any third-party implementation can run against.

The recommended approach is **Python 3.11+** as the single primary language (matches existing `pi-forge`, aligns with Thermocline's planned `thermocline-py` registry entry, lowest barrier for users to read/extend the reference impl). Critical libraries: Pydantic v2 (envelope types), PyNaCl (ed25519 brine), RFC 8785 / `rfc8785` (canonical JSON for signing input), `python-keyring` (platform keystore), SQLite stdlib (audit log), BLAKE3 (chain hash with versioned `algo_version`), `httpx` (async HTTP transport, only in Photophore's dispatch crate), Flask (forge transport, continuation of pi-forge), `click` (CLI), Hypothesis (property tests for invariants). Sharp separation enforced by CI: `thermocline.{canonical,identity}`, `photophore.{classifier,shadow,policy,audit,channels}` are network-free; only `photophore.dispatch` and forge `server.py` files import HTTP clients.

The dominant risks are subtle privacy regressions: classifier default drift (a future PR accidentally permits `shared` as default), shadow abstraction leakage (schema-valid abstractions that contain identifying detail), audit chain algorithm lock-in (forgetting an `algo_version` field), `json.dumps` for signing input (Python-specific — non-canonical), Pydantic v1 patterns drifting in (`.dict()` produces non-canonical output), and "helpful" log statements that print tier-0 content. Each is mitigated by structural decisions baked into Phase 1: an explicit `default_tier()` function with a Hypothesis invariant, hard-fail irreversibility test as a dispatch gate, versioned audit-entry schema from day 1, single canonical-JSON path through `thermocline.canonical.canonicalize`, Pydantic-v2-only pinning with CI lints, and a `Sensitive[T]` wrapper class for any value that could carry private content.

## Key Findings

### Recommended Stack

Python 3.11+ across all three repos. Pydantic v2 for envelope types (also generates JSON Schema for free). PyNaCl for ed25519 brine signing/verifying. RFC 8785 (`rfc8785` library) for canonical JSON — the only path used for signing input. SQLite stdlib + `blake3` Python binding for audit log with versioned `algo_version="blake3-v1"`. `python-keyring` for platform keystore (trust store + IdentityProvider key material — never co-located with audit log). `httpx` async HTTP for Photophore's dispatch coordinator. Flask continues for forges (`pi-forge`, `describe-forge`). `click` for CLIs. Hypothesis for property tests. `mypy --strict` and `ruff` as CI gates. `uv` recommended for dev environment management.

**Core technologies:**
- **Python 3.11+** — language, sovereign-node binary discipline, ecosystem alignment with existing `pi-forge`
- **Pydantic 2.7+** — envelope types and JSON Schema export
- **PyNaCl 1.5+** — ed25519 brine signatures (mature libsodium bindings)
- **`rfc8785`** — canonical JSON for signing input
- **SQLite (stdlib)** — append-only audit log
- **`python-keyring` 25** — cross-platform secure keystore wrapper

### Expected Features

The three specs enumerate the v0.1 feature set across three layers:

**`thermocline-py` shared library (must have):**
- Pydantic models for task / task_result / job / job_result / error envelopes
- Canonical JSON for signing input
- `IdentityProvider` Protocol + brine reference adapter (PyNaCl + python-keyring)
- JSON Schema artifacts for every envelope shape (under `thermocline/schema/`)
- Conformance fixtures for cross-language verification

**`photophore` Python package (must have):**
- Channel registry with full lifecycle, platform keystore backing, immutable per-channel key scheme
- Three-tier classification with strict priority order, rule-based v0.1 classifier, conservative `local` default
- Dispatch-time shadow generation with per-content-type abstraction strategies and three quality tests
- `result_policy` authoring on `task` envelopes
- Append-only chained audit log (BLAKE3, versioned `algo_version`, SQLite triggers enforce append-only)
- Privacy receipts with type-system-enforced verification gate
- Async dispatch coordinator (9-step flow, network-isolated)
- CLI with `channel`, `audit`, `classify`, `policy`, `dispatch` subcommands
- `AnchorTarget` Protocol with no-op default

**`seamount` upgrades (must have):**
- `pi-forge` real brine signing (replaces existing TODO stubs)
- `describe-forge` — second reference forge that exercises tier-1 shadows
- Cross-suite conformance test harness (runnable against any forge)

**Should have / defer:**
- Per-step shadow generation for `job` envelopes (Photophore spec v0.2)
- Trust score algorithm (Photophore spec v0.3)
- Model-based classifier (Photophore spec v0.3, opt-in, local-only)
- Multi-hop channels, Ring 3 / Arweave anchor (Photophore spec v0.4)
- TypeScript client library `thermocline-ts` (cross-language proof, future milestone)

### Architecture Approach

Multi-repo Python workspace with sharply separated packages mirroring the spec roles:

**Major components:**
1. **`thermocline/python/` (the foundation)** — `thermocline` package: envelope (Pydantic), canonical (RFC 8785), identity (Protocol + brine adapter), schemes (key scheme enum + verifier dispatch), conformance (JSON fixtures and harness helpers).
2. **`photophore/python/`** — `photophore` package: core (shared types), channels (trust store via `python-keyring`), classifier (pure rule pipeline), shadow (pure generator + quality tests), policy (pure result_policy authoring), audit (SQLite chained log + AnchorTarget), dispatch (async coordinator, only network-allowed module), cli (click).
3. **`seamount/pi-forge/`** — Flask handler upgraded to use `thermocline-py` for all envelope work (replaces existing stubs). Continues to compute π.
4. **`seamount/describe-forge/`** — new Flask handler that accepts a tier-1 shadow + relevance and returns a templated tier-2 description. Exercises the privacy primitive end-to-end.
5. **`seamount/conformance/`** — standalone `forge_conformance` test harness for any Thermocline-compliant forge.

**Architectural patterns:**
- **Pure-core / imperative-shell**: classifier, shadow, policy are pure; dispatch is the imperative shell.
- **Protocol-boundaried adapters**: `IdentityProvider`, `AnchorTarget`, transport are `typing.Protocol`s.
- **Append-only with hash-chained verification**: each audit entry hashes the canonical bytes of the previous; `algo_version`-tagged.
- **Sensitive-wrapper newtypes**: any tier-0-or-could-be value wrapped in `Sensitive[T]` with redacting `__repr__`.
- **Receipt-as-verification-witness**: `Receipt` constructible only via `IdentityProvider.verify()` — type-system enforced.

### Critical Pitfalls

1. **Classifier default drift** — explicit `default_tier()` function + Hypothesis invariant + CI lint that blocks `Tier.PUBLIC` outside tag/path-rule branches.
2. **Shadow abstraction leakage** — hard-fail irreversibility test gates dispatch; per-content-type strategies per the v0.3 quality table.
3. **Audit chain algorithm lock-in** — `algo_version` field in every entry from day 1; verifier dispatches on it.
4. **`json.dumps` for signing input (Python-specific)** — single canonical path through `thermocline.canonical.canonicalize`; CI lint flags `json.dumps(` in critical paths.
5. **Pydantic v1 patterns drifting in** — pin v2; CI lint flags `.dict()` and `.json()` patterns.
6. **Implicit trust elevation through logging** — `Sensitive[T]` wrapper class + redacting `__repr__` + CI lint forbids `print(`.
7. **Receipt verification skipped** — `Receipt` constructible only via `IdentityProvider.verify()`; type-system enforced.

(See `PITFALLS.md` for the full set — twelve critical pitfalls plus technical-debt patterns, integration gotchas, performance traps, security mistakes, UX pitfalls, and a "looks done but isn't" checklist spanning all three repos.)

## Implications for Roadmap

Coarse granularity (per project config). 4 phases, ~10 plans total, spanning all three repos. v0.1 of the implementation milestone — not v0.1 of any individual spec.

### Phase 1: Thermocline foundations — `thermocline-py` shared library

**Rationale:** `thermocline-py` is the foundation every other package depends on. Envelope types, canonical JSON, IdentityProvider interface, and JSON Schema artifacts must land first or downstream work has nothing to import. This is also where forever-decisions live (canonical-JSON discipline, Pydantic v2 lock-in, brine adapter that never holds keys in process memory).
**Delivers:** `thermocline/python/` package with envelope types (Pydantic v2), canonical JSON wrapper (`rfc8785`), `IdentityProvider` Protocol + brine reference adapter (PyNaCl + `python-keyring`), key-scheme dispatch logic, JSON Schema artifacts under `thermocline/schema/`, conformance fixtures under `thermocline/conformance/`. Spec patches as discovered. Pinning to Pydantic v2 only with CI lint.
**Addresses:** Pitfalls 4, 9, 11, 12 (helpful logging, IdP holding keys, `json.dumps` for signing, Pydantic v1 drift).
**Avoids:** "Implement the engine first, share types later" trap that creates drift.

### Phase 2: Photophore privacy primitives + foundations

**Rationale:** With `thermocline-py` available, the privacy-critical components can be built in isolation as pure functions (classifier, shadow, policy) plus the audit and channels foundations they all write through. Audit log schema is a forever-decision; getting `algo_version` right early prevents migration pain. Trust store separation from SQLite is a threat-model invariant worth establishing before anything dispatches.
**Delivers:** `photophore/python/photophore/` package: core (shared types), channels (trust store via `python-keyring`, lifecycle, ceiling rules), classifier (tag parser + path rules with mandatory catch-all + rule-based default), shadow (per-content-type abstractions + three quality tests with irreversibility hard-fail), policy (`result_policy` authoring), audit (SQLite chained log with `algo_version="blake3-v1"`, AnchorTarget Protocol with no-op default, query/export). Photophore CLI with `channel`, `audit`, `classify`, `policy preview` subcommands. Hypothesis property tests for classifier default invariant.
**Addresses:** Pitfalls 1, 2, 3, 6, 8 (classifier default drift, shadow leakage, audit lock-in, trust store backup, path-rule catch-all).
**Uses:** `thermocline-py` envelope types and `IdentityProvider` Protocol from Phase 1.

### Phase 3: Photophore dispatch + Seamount upgrade (the integration phase)

**Rationale:** With privacy primitives in place and `thermocline-py` foundations available, the dispatch coordinator integrates everything. Pair it with the Seamount upgrades — `pi-forge` real-brine and the new `describe-forge` — so the integration test isn't a stub-vs-stub charade. End-to-end Photophore → real-brine forge → verified receipt → audit-log entry is the deliverable.
**Delivers:** `photophore.dispatch` async coordinator (the 9-step flow, type-enforced receipt verification, network-isolation contract via CI). `photophore dispatch` CLI subcommand. `seamount/pi-forge/` upgraded to real brine via `thermocline-py` (replaces TODO stubs). `seamount/describe-forge/` — new Flask handler that accepts tier-1 shadows and returns templated tier-2 descriptions. End-to-end integration test exercising the full path.
**Addresses:** Pitfalls 5, 7 (receipt verification skipped, eager classification at write time).
**Implements:** Privacy receipt round-trip; the suite finally talks to itself.

### Phase 4: Hardening, conformance, and v0.1 release

**Rationale:** Validate that the system actually meets the three specs and the three threat models. Hypothesis property tests for invariants. Negative tests for each AT-* surface (Thermocline AT-C1..C6, Photophore AT-A1..A6, Seamount AT-E1..E5 — 17 surfaces total). ADRs documenting the forever-decisions. Cross-suite conformance harness any forge can run. Coordinated v0.1 git tags across all three repos.
**Delivers:** `seamount/conformance/` standalone harness package (`forge_conformance`); Hypothesis property test suite for the four critical invariants; negative tests per AT-* surface (17 total); ADRs (Python as primary language, BLAKE3 with `algo_version`, trust-store separation, no shadow caching, no in-process keys, single canonical JSON path); ops/install docs (clone → first dispatch → audit query → audit export, on macOS, in <30 minutes); CI gates (`ruff`, `mypy --strict`, `pip-audit`, network-isolation lint via custom AST check); coordinated v0.1 git tags on all three repos with CHANGELOGs describing what's implemented vs. deferred.
**Addresses:** Pitfall 10 (negative tests missing) — verification phase.

### Phase Ordering Rationale

- **Phase 1 first** because `thermocline-py` is the foundation everything else depends on. Forever-decisions about canonical JSON, Pydantic v2 lock-in, and the IdentityProvider Protocol shape are easier to get right when there's no pressure to ship downstream features.
- **Phase 2 second** because Photophore's privacy primitives (classifier, shadow, policy) are pure (no I/O) and can be developed without integration overhead. Pairing them with the audit log and channels (which they all write through) avoids "we'll add audit later" drift.
- **Phase 3 third** because dispatch needs both the primitives (Phase 2) and the foundations (Phase 1). The Seamount upgrades are scheduled here too because they share the same `thermocline-py` dependency and the integration test is the natural fit point.
- **Phase 4 last** because hardening and external conformance need a complete system. ADRs benefit from being written *after* the trade-offs were faced. Coordinated v0.1 git tags across three repos require all three repos to be at release-quality together.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1 (canonical JSON):** verify `rfc8785` library handles the full Thermocline envelope shape; property-test for round-trip stability.
- **Phase 1 (brine adapter on Apple Silicon):** verify `python-keyring` works with Secure Enclave entries; may need direct `pyobjc` calls for SE-specific entries.
- **Phase 2 (audit log):** SQLite WAL tuning, BLAKE3 streaming for large scans, chain-archival format. Implementation-time benchmarks.
- **Phase 2 (shadow quality tests):** the irreversibility test heuristics need iteration with real fixtures. Plan time for "leaky abstraction" fixture collection.
- **Phase 3 (`describe-forge` design):** the second forge needs to be substantive enough to exercise tier-1 shadow handling end-to-end while staying as simple as `pi-forge`. Spike a design spike before implementation.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Pydantic v2):** well-documented; standard.
- **Phase 4 (CI gates and ADRs):** standard practice.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Python 3.11+ + Pydantic v2 + PyNaCl + RFC 8785 + SQLite + python-keyring is the canonical sovereign-node Python stack |
| Features | HIGH | Three specs enumerate the v0.1 feature set directly |
| Architecture | HIGH | Package boundaries map to spec roles; pure-core / imperative-shell pattern is well-tested |
| Pitfalls | HIGH | Drawn from three threat models + Python-specific failure modes from existing pi-forge code |

**Overall confidence:** HIGH

### Gaps to Address

- **`describe-forge` design**: needs a small design spike in Phase 3 to validate that "shadow → templated description" is a substantive enough exercise of tier-1 handling without bloating into an LLM-backed forge.
- **Apple Silicon Secure Enclave testing**: needs physical Apple Silicon + developer signing identity for full coverage. Plan: target macOS 12+ via standard Keychain in Phase 2; add Secure Enclave entry tests in Phase 4.
- **Performance baselines**: no benchmarks exist for "dispatches per second" on a typical sovereign node. Plan: add simple `pytest-benchmark` cases in Phase 4; do not optimize prematurely.
- **Conformance fixture provenance**: Phase 4 needs canonical fixtures. Some can be authored fresh; some can be derived from Photophore→pi-forge integration tests in Phase 3 (capture, vet, freeze).

## Sources

### Primary (HIGH confidence)
- `thermocline/README.md` — envelope spec; Identity Provider Interface; threat model AT-C1..C6
- `photophore/README.md` — policy engine spec; design constraints 1-10; threat model AT-A1..A6
- `seamount/README.md` — forge spec; conformance requirements; threat model AT-E1..E5
- `seamount/pi-forge/` working code (Flask, mpmath, envelope.py with brine stubs)

### Secondary (MEDIUM confidence — implementation details)
- Pydantic v2 docs (https://docs.pydantic.dev/)
- PyNaCl docs (https://pynacl.readthedocs.io/)
- RFC 8785 (https://www.rfc-editor.org/rfc/rfc8785) — JSON Canonicalization Scheme
- `python-keyring` docs — for platform coverage matrix
- BLAKE3 spec (https://github.com/BLAKE3-team/BLAKE3)
- "Pure Core, Imperative Shell" (Gary Bernhardt) — applied to privacy-critical components

### Tertiary (LOW confidence — to validate during implementation)
- Specific pinned versions (re-verify at install time)
- Apple Silicon Secure Enclave behavior under various keychain entry attributes (test on real hardware)
- WAL checkpoint thresholds for typical dispatch rates (benchmark in Phase 4)

---
*Research completed: 2026-05-05*
*Ready for roadmap: yes*
