# Phase 4: Hardening, Conformance, and v0.1 Release - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in 04-CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-11
**Phase:** 04-hardening-conformance-and-v0-1-release
**Mode:** `--auto` (single-pass; recommended option auto-selected for each area; no AskUserQuestion calls)
**Areas discussed:** AT-* test placement (D-01) · Cross-impl spec patches (D-02) · ADR scope (D-03) · Property test cadence (D-04) · Ops docs surface (D-05) · Release coordination (D-06) · CLI-06 retrofit (D-07) · CLI-07 retrofit (D-08) · Sensitive/print/logger (D-09) · Plan structure (D-10) · Secure Enclave gap (D-11)

---

## AT-* Negative Test Placement and Coverage Enforcement (D-01)

| Option | Description | Selected |
|--------|-------------|----------|
| A — Per-repo split by AT-letter (AT-C* → thermocline, AT-A* → photophore, AT-E* → seamount); `at_coverage.py` per repo + roll-up | Each spec's negatives live with the spec; filename convention = coverage counter; CI gate per repo + suite-level roll-up | ✓ (recommended default) |
| B — Centralized `seamount/conformance/at_negatives/` for all 17, exercising through the forge | Single test harness; tests reachable through HTTP fixtures only | |
| C — Top-level `at-tests/` package in `thermocline/` planning hub | Suite-wide single location; cross-repo imports required | |

**Auto-selection:** A (recommended default).
**Notes:** Each spec README points readers to its own `tests/at_negative/`; survives test refactors; roll-up `at_coverage_total.py` in thermocline asserts `len(covered) == 17` at suite level.

---

## Phase-3 Cross-Impl Spec Patches SP-3.3-01..03 (D-02)

| Option | Description | Selected |
|--------|-------------|----------|
| A — Ship all three as Thermocline README amendments at v0.3.1 | Follows THERMO-01 cross-impl-spec-patch pattern (Phase 1 → Phase 2 LEARNINGS); single commit; THERMO-07 SUPPORTED_VERSIONS already lists `"0.3.1"` | ✓ (recommended default) |
| B — Leave coordinator-internal (Python-only documentation in `photophore.dispatch` docstrings) | Smaller diff in `thermocline/`; risks every non-Python impl hitting the same reverse-engineering | |

**Auto-selection:** A (recommended default).
**Notes:** SP-3.3-01 = receipt-signature canonicalization with `sig=""` not removed. SP-3.3-02 = `dispatch_signature` pre-fill ordering. SP-3.3-03 = receipt-field `sig` / `bytes_hex` tolerance. All three are wire-level interop; matches THERMO-01 precedent.

---

## ADR Scope, Location, Cross-Linking (D-03)

| Option | Description | Selected |
|--------|-------------|----------|
| A — 7 ADRs split across 3 repos by binding; one-page MADR-lite; README cross-refs with relative paths | Each repo tells its own story; no symlinks; works on GitHub via sibling-repo namespace | ✓ (recommended default) |
| B — All 7 ADRs in `thermocline/docs/adr/`; other repos link to them | Single source; cross-repo discoverability fragile if repos re-org | |
| C — Duplicated ADRs in each repo where the decision shows up | Maximum self-containment per repo; high duplication maintenance cost | |

**Auto-selection:** A (recommended default).
**Notes:** ADR-0001..0005 land in thermocline (Python, Pydantic v2, canonical JSON, BLAKE3, no in-process key material); ADR-0001..0002 land in photophore (trust-store separation, no shadow caching). Seamount inherits via README cross-refs.

---

## Property Test Cadence and Scope (D-04)

| Option | Description | Selected |
|--------|-------------|----------|
| A — Reuse existing 4 property tests with `max_examples=200`; add 1 dispatch-time shadow-uniqueness integration property | CONF-03 says ≥100 cases; existing tests qualify; 200 gives headroom under one-minute CI | ✓ (recommended default) |
| B — Re-do all 4 at `max_examples=1000` for stronger guarantees | More confidence; CI minutes cost ~5x | |
| C — Add cross-suite integration property (e.g., dispatch-time tier-0 escape detection) | Larger scope; needs more design | |

**Auto-selection:** A (recommended default).
**Notes:** Classifier-default, audit-chain, canonical-JSON, single-dispatch shadow-uniqueness exist. The new test exercises the full coordinator path: same envelope, dispatched N times, all shadow IDs distinct. Each property file gets a top comment `# CONF-03 invariant: <name>` for the `property_coverage.py` enumeration.

---

## Ops/Install Documentation Surface (D-05)

| Option | Description | Selected |
|--------|-------------|----------|
| A — `docs/install.md` + `docs/ops.md` per repo + cross-repo `thermocline/docs/quickstart.md`; macOS first-class | Separates discovery (README) from depth; 30-min walkthrough has space; Linux/Windows = secondary mention | ✓ (recommended default) |
| B — README-inline only | Simpler; README balloons to 50+ pages for the 30-min walkthrough | |
| C — Separate `thermocline-docs` repo | Cross-repo coordination overhead; defeats per-repo self-containment | |

**Auto-selection:** A (recommended default).
**Notes:** Quickstart lives in thermocline since clone → dispatch crosses all three repos. Each repo's README §"Documentation" cross-links to its own `docs/`. Apple Silicon Secure Enclave documented under §"Known limitations" in `install.md` per D-11.

---

## Release Coordination and CHANGELOG Format (D-06)

| Option | Description | Selected |
|--------|-------------|----------|
| A — `scripts/tag-v0.1.0.sh` helper; same-day atomic tagging; Keep-a-Changelog-lite per repo | Repeatable, auditable; honors "trust never automated" with manual push step | ✓ (recommended default) |
| B — Manual sequential tagging with version pin updates between | More flexibility; error-prone; harder to reproduce | |
| C — CI-triggered tagging on push to release branch | Most automated; defers control away from sovereign | |

**Auto-selection:** A (recommended default).
**Notes:** Script lives in `thermocline/scripts/` (planning hub owns suite-wide tooling). `--dry-run` mode supported. CHANGELOG format per repo: `## [0.1.0] - YYYY-MM-DD` with `Added / Implemented / Deferred / Known limitations` subsections. Tag message records cross-repo coordination.

---

## CLI-06 Retrofit (every CLI subcommand emits audit entry) (D-07)

| Option | Description | Selected |
|--------|-------------|----------|
| A — Literal "every subcommand"; new `cli_invocation` audit-entry kind; args sanitized (file paths → BLAKE3 hash) | Spec text literal; audit log is the proof; inflation cost bounded | ✓ (recommended default) |
| B — Mutating subcommands only (write actions log; reads skip) | Smaller DB; reads "every subcommand" non-literally; needs spec patch | |
| C — Configurable: default mutating-only; flag `--audit-reads` opts in | Sophisticated; over-engineered for v0.1 | |

**Auto-selection:** A (recommended default).
**Notes:** New kind `cli_invocation` extends the audit-kind enum (additive). Decorator `@audit_cli_invocation` on the click group wraps every subcommand. File-path args hashed with BLAKE3 (matches audit chain hash family). Channel/node/envelope IDs recorded verbatim (non-secret identifiers).

---

## CLI-07 Retrofit (classification/policy errors include `(tier, reason)`) (D-08)

| Option | Description | Selected |
|--------|-------------|----------|
| A — Append `(tier=X, reason=Y)` to dispatch, classify, policy error messages | Spec text matches "every CLI error message that involves classification or policy"; 3 subcommands affected | ✓ (recommended default) |
| B — Reason-only (no tier) | Smaller diff; loses the diagnostic value of seeing tier separately | |

**Auto-selection:** A (recommended default).
**Notes:** Implemented via string-formatting tweaks in `photophore.errors.DispatchError.__str__`; snapshot-tested via pytest.

---

## Sensitive[T] Retrofit + print( Lint + Privacy-Aware Logger (D-09)

| Option | Description | Selected |
|--------|-------------|----------|
| A — Ship all three together: sweep + AST lint + logging filter; CI gate before pytest | Reinforce each other; lint catches new code; filter catches existing log calls; wrapper makes both detectable | ✓ (recommended default) |
| B — Ship sweep + lint; defer logger filter | Smaller diff; logger filter is the catch-all backstop, value of shipping all three | |

**Auto-selection:** A (recommended default).
**Notes:** `ast_lint_no_print.py` mirrors network-isolation lint structure. `SensitiveFilter` lives at `photophore/python/src/photophore/logging.py` as a `logging.Filter` subclass. Test files and example files exempt from `print(` lint.

---

## Plan Structure (housekeeping) (D-10)

| Option | Description | Selected |
|--------|-------------|----------|
| A — Keep ROADMAP's 2 plans (04-01 machine-verifiable, 04-02 human-readable + release) | Plans cleanly bounded; no Phase 2-style growth pressure | ✓ (recommended default) |
| B — Split into 3 plans (separate release plan) | More granular; one more handoff; current 04-02 release section is small | |

**Auto-selection:** A (recommended default).
**Notes:** 04-02 depends on 04-01 (CI green before tagging). Parallelization is not beneficial since release-coordination needs the CI gates to exist.

---

## Apple Silicon Secure Enclave (STATE.md carry-forward blocker) (D-11)

| Option | Description | Selected |
|--------|-------------|----------|
| A — Document as v0.2 follow-up in `docs/install.md` §"Known limitations"; not a v0.1 blocker | macOS Keychain entries software-encrypted-at-rest; satisfies IDENT-02/IDENT-05; SE is a strengthening | ✓ (recommended default) |
| B — Block v0.1 until SE works | Blocks release indefinitely; outside spec mandate | |
| C — Implement SE before v0.1 | Requires developer signing identity + Apple Silicon hardware in CI; out of scope for v0.1 | |

**Auto-selection:** A (recommended default).
**Notes:** Spec mandate (IDENT-02 / IDENT-05) is "delegate to platform keystore; never copy key material out". Default `python-keyring` macOS Keychain satisfies this. SE is hardware-anchored strengthening, valuable but not a v0.1 gate. STATE.md blocker → move to PROJECT.md "Pending Validations" or v0.2 backlog.

---

## Claude's Discretion

The following are planner / executor discretion (not part of gray-area discussion):

- Exact AT-* test bodies (failure mode is fixed by spec; harness is planner's call; recommended `pytest.mark.at_surface("AT-X<n>")` markers).
- ADR file format details (MADR-lite recommended; exact heading levels are planner's call).
- `tag-v0.1.0.sh` output formatting and `--dry-run` mode.
- Exact hash function for CLI arg sanitization (recommended BLAKE3).
- `docs/index.md` per repo for cross-linking.
- New thermocline CI matrix shape (recommended: mirror photophore CI — ubuntu lint+pytest, macos keystore tests).
- Re-export-vs-duplicate strategy for `tests/at_negative/test_at_a1_*.py` linking to Phase 3's `test_e2e_at_a1_replay.py` (recommended: thin re-export module).

## Deferred Ideas

See 04-CONTEXT.md `<deferred>` section. Summary:

- Hardware-anchored Secure Enclave (v0.2).
- Property tests beyond CONF-03's four (v0.2+).
- Third-party forge conformance certification (post-v0.1).
- Linux/Windows first-class ops docs (v0.2).
- `mypy --strict` on seamount forges (Plan 04-01 decides: extend or exempt).
- MADR-full vs MADR-lite (v0.2+).
- Keep-a-Changelog-full migration (next minor).
- Daemon mode for Photophore (v0.2+).
- CI-triggered releases (post-v0.1).
