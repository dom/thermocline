# Phase 4: Hardening, Conformance, and v0.1 Release — Research

**Researched:** 2026-05-11
**Domain:** Cross-repo hardening, threat-model coverage, release engineering, ADR/docs production for a privacy-tiered Python reference implementation suite
**Confidence:** HIGH on file paths and existing code shape (verified via direct read); HIGH on AT-* failure modes (read from normative spec READMEs); HIGH on test infrastructure (read source); MEDIUM on tag-script edge cases (BSD vs GNU `sed`); HIGH on CHANGELOG/ADR formats (CITED + standard).

## Summary

Phase 4 is a freeze-and-validate phase. The architecture is built; what remains is to: (a) write 16 new threat-model negative tests across three repos, (b) bump four existing property tests to `max_examples=200` and add a fifth dispatch-integrated one, (c) wire CI gates (including a new `print(` AST lint and per-repo `at_coverage.py`), (d) retrofit `CLI_INVOKED` audit entries to every photophore subcommand (the enum slot already exists in `core.py` line 87), (e) write 7 ADRs, install/ops docs, and a coordinated release script, and (f) ship three Thermocline README amendments (SP-3.3-01..03) for the wire-level findings Phase 3 surfaced.

**Primary recommendation:** Plan 04-01 is mechanically large but well-bounded — 16 negative tests + 1 property test + 5 lint/coverage scripts + 3 CI workflow edits. Sequence it as: (1) `KNOWN_EVENT_TYPES` + audit `CLI_INVOKED` payload wiring (already-stubbed enum slot), (2) tools (`at_coverage.py`, `ast_lint_no_print.py`, `property_coverage.py`) so CI failure modes line up with test work, (3) AT-* negative tests in three repos, (4) property test bumps, (5) CI workflow edits. Plan 04-02's release script depends on Plan 04-01 being green, so 04-02 runs strictly after 04-01.

## ⚠ CONTEXT.md CONFLICTS

**CONFLICT-01: Thermocline source path discrepancy.** CONTEXT.md `<decisions>` D-01 (line 44) and `<code_context>` (lines 358, 360) say `thermocline/python/tests/at_negative/`. The actual layout is `/Users/dom/Projects/dom/thermocline/thermocline/python/tests/` — there is a nested `thermocline/` directory because the repo is named `thermocline` and the library is also `thermocline`. The planner must use `thermocline/thermocline/python/tests/at_negative/` (relative to the repo root). All other CONTEXT.md path references to the thermocline source code have the same one-segment elision. This is a documentation-level inconsistency; the work itself is unaffected once the planner notes the doubled path.

**CONFLICT-02: SP-3.3-01..03 are spec changes per D-02, but Phase 3's 03-03 SUMMARY calls them coordinator-internal.** 03-03-SUMMARY.md §"Cross-Impl Spec Patches Surfaced" line 342 states: *"These three patches are coordinator changes, not spec changes (the spec was right; the coordinator was wrong). No update needed to thermocline-py spec README."* CONTEXT D-02 (line 56) reverses this: ship as Thermocline README amendments. The planner should treat D-02 as the binding decision (gathered later, post-discussion), but the ADR or amendment text must acknowledge the reversal so a reader of both documents understands why. Recommended approach: amend the README with the three normative paragraphs from D-02; in the v0.3.1 CHANGELOG entry, note "Phase 3 surfaced these as coordinator bugs; Phase 4 reclassifies them as spec clarifications because any non-Python impl will encounter the same questions."

**CONFLICT-03: Plan 04-01's print-lint scope (D-09) says forges are in scope.** D-09 (line 211) says the lint covers `seamount/{pi-forge,describe-forge}/` excluding `cli/`. The forges have NO `cli/` directory — they use flat module layout (`pi_forge/__main__.py`, `describe_forge/__main__.py`). Both `__main__.py` files use `print()` extensively for `init` subcommand output (file creation reports, "Keypair already exists" messages) AND for the `PIFORGE_READY port=...` line that subprocess fixtures in Phase 3 grep for. Both `server.py` files print startup banners. Recommendation: extend the allow-list to include `seamount/pi-forge/pi_forge/__main__.py`, `seamount/pi-forge/server.py`, `seamount/describe-forge/describe_forge/__main__.py`, `seamount/describe-forge/server.py`. These are CLI/startup paths analogous to photophore's `cli/` directory. Documenting the exception in the lint file's allow-list is preferable to converting forge prints to `click.echo` (forges are not click-based).

## Project Constraints (from CLAUDE.md)

The project CLAUDE.md mandates the following — research recommendations honor these:

- Python 3.11+ across all three repos. [VERIFIED: pyproject.toml `requires-python = ">=3.11"` in all packages]
- Pydantic v2 envelope types (`>=2.7,<3.0`). [VERIFIED: thermocline pyproject]
- PyNaCl 1.5+ for ed25519. [VERIFIED]
- BLAKE3 with `algo_version="blake3-v1"`. [VERIFIED: audit chain uses ALGO_VERSION_DEFAULT in `_chain.py`]
- RFC 8785 canonical JSON via `thermocline.canonical.canonicalize` is the only signing input path; `json.dumps` forbidden in library code (allow-listed exceptions: `build_schemas.py`, `check_no_json_dumps.py`). [VERIFIED: AST lint exists at `thermocline/python/src/thermocline/scripts/check_no_json_dumps.py`]
- python-keyring is the only key store; NO file/env fallback. [VERIFIED: `IDENT-05` test exists]
- Audit log append-only via SQLite triggers; never co-located with trust store. [VERIFIED: AUDIT-01]
- IdentityProvider Protocol is the only signing/verifying path; never `bytes` of key material in process. [VERIFIED]
- macOS first-class; Linux secondary (libsecret); Windows secondary (Credential Manager).
- License MIT across all three repos.

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Per-repo AT-* test split by letter. Thermocline AT-C1..C6 → `thermocline/thermocline/python/tests/at_negative/` (path corrected per CONFLICT-01). Photophore AT-A1..A6 → `photophore/python/tests/at_negative/` (AT-A1 is a re-export of the Phase 3 integration test). Seamount AT-E1..E5 → `seamount/conformance/at_negative/`. Filename convention: `test_at_<letter><number>_<one_word_failure>.py`. Each file docstring opens with `AT-X<n>: <failure mode>`. `tools/at_coverage.py` per repo scans `tests/at_negative/test_at_*.py` and asserts the expected AT-ID set. `thermocline/tools/at_coverage_total.py` rolls up all three subsets and asserts `len(covered) == 17`. `pytest.mark.at_surface("AT-X<n>")` markers per Claude's-discretion section.
- **D-02:** Ship SP-3.3-01..03 as Thermocline README amendments at v0.3.1. Single commit `spec(0.3.1): clarify signature canonicalization invariants (SP-3.3-01..03)` in `thermocline/`. `SUPPORTED_VERSIONS` already includes `"0.3.1"` (verified in `thermocline/python/src/thermocline/version.py` line 16).
- **D-03:** 7 ADRs across 3 repos in `docs/adr/`. One-page MADR-lite. README cross-references via relative paths (no symlinks). Cross-repo paths use `../<repo>/docs/adr/ADR-XXXX-name.md` (works because repos live as siblings on dev box AND on GitHub when in the same namespace).
- **D-04:** Reuse 4 existing property tests at `max_examples=200`. Add 1 dispatch-integrated property test at `photophore/python/tests/integration/test_property_dispatch_shadow_uniqueness.py`. All four files get `# CONF-03 invariant: <name>` top-of-file comment. `tools/property_coverage.py` (per repo OR shared) enumerates and asserts 4/4 plus `max_examples >= 200`.
- **D-05:** `docs/install.md` + `docs/ops.md` per repo + `thermocline/docs/quickstart.md` for cross-repo 30-minute flow. macOS first-class.
- **D-06:** `thermocline/scripts/tag-v0.1.0.sh` helper. Same-day atomic tagging. Keep-a-Changelog-lite per repo. `--dry-run` mode (Claude's discretion).
- **D-07:** New `cli_invocation` audit-entry kind (`AuditEventType.CLI_INVOKED` — verified, already in enum). Args sanitized via BLAKE3 file-content hash. Every subcommand wraps in try/finally via `@audit_cli_invocation` decorator on the `photophore` click group.
- **D-08:** Append `(tier=X, reason=Y)` to dispatch / classify / policy error messages. String-formatting tweaks only; no API change.
- **D-09:** Sweep `Sensitive[T]` + new `print(` AST lint + `SensitiveFilter` logging filter — ship all three together.
- **D-10:** Keep ROADMAP's 2 plans; do NOT split. 04-02 depends on 04-01. No parallelization.
- **D-11:** Apple Silicon Secure Enclave → v0.2 follow-up. Documented as known limitation in `install.md`. STATE.md blocker resolved.

### Claude's Discretion

- Exact AT-* test bodies — pytest parametrized fixtures + `pytest.mark.at_surface("AT-X<n>")` markers recommended.
- ADR file format details — MADR-lite (Context / Decision / Consequences / Status).
- `tag-v0.1.0.sh` UX — `--dry-run` mode recommended.
- CLI args sanitization — BLAKE3 (matches audit chain hash family).
- `docs/index.md` per repo cross-linking install/ops/quickstart.
- CI matrix for thermocline's new CI mirrors photophore's split (ubuntu lint+pytest; macos keystore tests).
- AT-A1 re-export: thin re-export module in `tests/at_negative/` pointing at `tests/integration/test_e2e_at_a1_replay.py`.

### Deferred Ideas (OUT OF SCOPE)

- Apple Silicon Secure Enclave hardware-anchored keystore entries (v0.2).
- Property tests beyond the four CONF-03 invariants.
- Linux / Windows first-class ops docs.
- Third-party forge conformance certification.
- `mypy --strict` on seamount forges (planner may extend; otherwise document exemption — CONFLICT-04 detail below).
- MADR-full ADRs.
- CHANGELOG migration to full Keep-a-Changelog.
- Daemon mode for Photophore.
- Automated CI tagging on push to release branch.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CLI-06 | Every CLI subcommand emits an audit log entry recording the operation invoked and its outcome (success/failure); verified by integration test grep over audit DB. | D-07; `AuditEventType.CLI_INVOKED` already in `core.py` line 87. `@audit_cli_invocation` decorator wraps `photophore` click group. |
| CLI-07 | Every CLI error message that involves classification or policy includes `(tier, reason)`. | D-08; string-formatting tweaks in `dispatch_cmds.py` line 89-96 + `classify_cmds.py` + `policy_cmds.py`; no API change. |
| CONF-01 | Conformance test suite passes against `pi-forge` and `describe-forge`. | Already passes per Phase 3 SUMMARY (`PASS=7 FAIL=0 SKIP=6`). Phase 4 flips AT-E1..E5 from SKIP to PASS by wiring negative tests. |
| CONF-02 | At least one negative test per AT-* surface (17 total). | See `## AT-* Surface Inventory` below. AT-A1 already wired Phase 3. 16 new tests in Phase 4. |
| CONF-03 | Hypothesis property tests for 4 invariants, ≥100 cases each. | See `## Property Test Inventory` below. 3 of 4 tests exist at `max_examples=100`; canonical test already at 200. Bump three, add one dispatch-integrated. |
| CONF-04 | CI gates: ruff, mypy --strict, pip-audit, AST network-isolation lint, pytest, forge_conformance. | See `## CI Gate Inventory` below. New gates: `at_coverage.py`, `property_coverage.py`, `ast_lint_no_print.py`. Thermocline has NO existing CI workflow — Plan 04-01 creates `thermocline/.github/workflows/ci.yml`. |
| CONF-05 | 7 ADRs in `docs/adr/`. | See `## ADR Landings` below. D-03 distributes across 3 repos. |
| CONF-06 | `Sensitive[T]` wrapper + `print(` lint + privacy-aware logging filter. | See `## Sensitive[T] Sweep` + `## print( Lint Scope` + `## SensitiveFilter Logging` below. |
| CONF-07 | Install + ops docs walking clone → first dispatch → audit query → audit export on macOS in under 30 minutes. | See `## Ops Docs Scope` below. |
| CONF-08 | Three coordinated v0.1 git tags with CHANGELOG (implemented vs deferred). | See `## Release Script + CHANGELOGs` below. |


## Architectural Responsibility Map

Phase 4 is entirely meta — it produces validation, documentation, and release artifacts atop the implementation. There is no new runtime data flow. The map records which repo each Phase 4 artifact lives in.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| AT-C* negative tests | thermocline (spec repo) | — | AT-C* surfaces are defined in `thermocline/README.md` §"Attack Surfaces"; tests live with the spec. |
| AT-A* negative tests | photophore (impl repo) | — | AT-A* surfaces are defined in `photophore/README.md`; AT-A1 already wired via `photophore/python/tests/integration/test_e2e_at_a1_replay.py`. |
| AT-E* negative tests | seamount (forge repo) | — | AT-E* surfaces are defined in `seamount/README.md`. Tests live in `seamount/conformance/at_negative/` (the conformance package is the cross-forge harness; AT-E* is a forge-host concern, not a single-forge concern). |
| Property tests (4 existing) | photophore (3) + thermocline (1) | — | Existing test homes (see file paths). |
| Property test (1 new, dispatch-integrated) | photophore | — | Reuses Phase 3 `subprocess_forge` fixture. |
| `cli_invocation` audit retrofit | photophore | — | `photophore.audit` + `photophore.cli` are the only modules involved. |
| `Sensitive[T]` sweep | thermocline (envelope) + photophore (audit, shadow) | — | Sensitive lives in thermocline; consumers are in both repos. |
| `print(` AST lint | All three repos (shared tool) | — | The check runs against all source trees; tool can be one shared file or three identical copies. Recommendation: three identical files (no shared dependency tree). |
| `SensitiveFilter` logging filter | photophore | — | Owns the only library logger that processes envelope payloads. |
| ADRs | thermocline (5) + photophore (2) + seamount (0) | — | D-03 distribution (verified count: 5+2=7). |
| Install docs | All three repos | — | Each repo's `docs/install.md`. |
| Ops docs | thermocline (empty) + photophore + seamount/* | — | Most ops surface lives in photophore (chain archival, channel ops). |
| Quickstart (30-min cross-repo flow) | thermocline | — | The walkthrough crosses all three; thermocline is the planning hub and the natural home. |
| Release script | thermocline | — | Per D-06; thermocline is the planning hub. |
| CHANGELOGs | All three repos | — | thermocline already has `thermocline/CHANGELOG.md` (extend with `## [0.1.0]` AND `## [0.3.1]` for spec patches). photophore + seamount get new files. |
| CI workflows | All three repos | — | photophore + seamount have existing workflows (extend). thermocline has NO `.github/` directory — Plan 04-01 creates it. |
| SP-3.3-01..03 spec amendments | thermocline | — | The README is the normative source; the amendments land in the README. |

## Standard Stack

All versions verified in pyproject.toml files. No new runtime libraries land in Phase 4.

### Core (already installed; reused)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pytest` | >=8.0 | Test runner | Phase 1-3 standard. |
| `hypothesis` | >=6.0 | Property testing | Phase 1 introduced; 4 existing tests bump to `max_examples=200`. [VERIFIED: photophore + thermocline pyprojects include `hypothesis>=6.0` in dev deps] |
| `ruff` | >=0.5 | Lint + format | Existing CI gate. |
| `mypy` | >=1.10 | `--strict` type check | Existing CI gate on photophore + thermocline; NOT on seamount forges. |
| `pip-audit` | latest | Vulnerability scan | Existing CI gate. |
| `blake3` | >=1.0.8 | Audit chain hash + CLI arg-path hash (D-07) | Reused for CLI arg sanitization. [CITED: D-07 line 245 Claude's-discretion picks BLAKE3 over SHA-256 to match audit chain family.] |
| `keyring` | >=25.0 | Platform keystore | Used in ops docs install steps. |
| `click` | >=8.3 | CLI framework | `@audit_cli_invocation` decorator attaches to existing click group. |

### Tooling (new in Phase 4)
| Library / Tool | Purpose | Notes |
|----------------|---------|-------|
| `tag-v0.1.0.sh` | bash | Release coordination per D-06. macOS uses BSD `sed`/`grep` by default — use POSIX-portable patterns OR detect `gsed`/`ggrep` and fall back gracefully. |
| `tools/at_coverage.py` | per-repo | Globs `tests/at_negative/test_at_*.py`, parses AT-IDs from filenames, asserts expected set. Mirror `ast_lint_network_isolation.py` invocation pattern. |
| `tools/at_coverage_total.py` | thermocline only | Imports/re-runs all three subsets, asserts union has 17 elements. |
| `tools/ast_lint_no_print.py` | per-repo (or shared) | AST visitor pattern from `ast_lint_network_isolation.py` (lines 56-86). Forbids `print(` in protected paths; allow-list mirrors PROTECTED_FRAGMENTS/ALLOWED_FRAGMENTS pattern. |
| `tools/property_coverage.py` | per-repo (or thermocline only — single roll-up) | Scans the four CONF-03 files for `# CONF-03 invariant:` comments AND parses `max_examples=N` literal, asserts `N >= 200`. |

### What NOT to Use (carry-forward; Phase 4 enforces)
| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `print(` in library code | Pitfall 4 / CONF-06 | `click.echo` in CLI paths; `logging` with `SensitiveFilter` elsewhere; `print` allowed only in test files, example files, allow-listed forge entrypoints. |
| `json.dumps` for signing input | Pitfall 11 | `thermocline.canonical.canonicalize` (existing AST lint enforces). |
| `pickle` anywhere | Deserialization vulnerability surface | JSON via Pydantic. |
| `dotenv` / env-var-based key material | IDENT-05 | `IdentityProvider` interface; reference adapter calls keystore per signature. |
| Symlinks for cross-repo ADR refs | D-03 | Relative paths (`../<repo>/docs/adr/...`). |
| `random.random()` for shadow IDs | AT-A2 | `secrets.token_bytes` / UUIDv4 over `os.urandom` (already in place). |
| `sed -i` without `''` empty string argument | macOS BSD sed quirk | Use Python helper inside `tag-v0.1.0.sh` for any in-place edits, OR detect `gsed`. Better: read-only operations (`grep` for CHANGELOG heading; emit error if absent). |


## AT-* Surface Inventory (17 surfaces)

Each row gives the spec-defined failure mode, the recommended test file path (per D-01), the assertion shape, and fixture status. **Existing fixtures** in `thermocline/thermocline/conformance/invalid/`: AT-A1, AT-A2, AT-A4, AT-A5, AT-C1, AT-C2, AT-C3, AT-C4, AT-C5, AT-C6. **Missing fixtures** (Phase 4 creates them): AT-A3, AT-A6, AT-E1, AT-E2, AT-E3, AT-E4, AT-E5. All Phase 4 new fixtures get `phase: 4` in `thermocline/thermocline/conformance/MANIFEST.yaml`.

### Thermocline AT-C* → `thermocline/thermocline/python/tests/at_negative/`

| AT-ID | Failure mode (from `thermocline/README.md`) | Test file | Fixture | Assertion |
|-------|----------|-----------|---------|-----------|
| AT-C1 | Envelope tampering in transit — dispatch signature MUST cover canonical envelope; any field modification invalidates the sig. | `test_at_c1_envelope_tampering.py` | `invalid/AT-C1-replayed-envelope.json` exists (note: this fixture is misnamed for replay — AT-C1 in the spec is tampering, NOT replay; AT-C2 in spec is replay. **VERIFY** which fixture maps to which surface.) | Mutate any field of a valid envelope; `Verifier.verify()` returns `None` (sig invalid). |
| AT-C2 | Envelope replay — `envelope_id` MUST be UUID; receiver MAY maintain replay cache. | `test_at_c2_envelope_replay.py` | `invalid/AT-C2-tampered-signature.json` exists (see AT-C1 note re: misnaming). | Send same `envelope_id` twice through `dispatch_async`; second dispatch is rejected at audit-log dedupe layer. Currently AUDIT layer does not enforce dedupe — VERIFY. If unenforced, the test asserts the spec MAY-clause and skips with rationale. |
| AT-C3 | Shadow inference — shadow IDs MUST be unique per dispatch. | `test_at_c3_shadow_correlation.py` | `invalid/AT-C3-leaky-shadow.json` exists. | Generate N shadows of identical content; assert N distinct `shadow_id` values. (Overlaps with property test but lives here for AT coverage.) |
| AT-C4 | Forged dispatch signature — verifier dispatches on declared `key_scheme` and fails on mismatch. | `test_at_c4_forged_dispatch_sig.py` | `invalid/AT-C4-key-scheme-mismatch.json` exists. | Parse envelope where signature is over different bytes than canonical; `Verifier.verify` returns `None`. |
| AT-C5 | Result policy escalation — `result_policy` is part of signed envelope; forge cannot modify. | `test_at_c5_result_policy_escalation.py` | `invalid/AT-C5-unsupported-version.json` exists (misnamed — version is THERMO-07, not AT-C5). **FIXTURE CONFLICT**: rename or add new fixture `invalid/AT-C5-result-policy-modified.json` showing a forge-modified `result_policy` that breaks the sig. | Verifier rejects envelope whose post-sign `result_policy` differs from canonical input. |
| AT-C6 | Key compromise — out-of-scope for code test; mitigation is hardware-backed keystore. | `test_at_c6_key_compromise.py` | `invalid/AT-C6-extra-field.json` exists (misnamed). | Document-only test that asserts (a) `IDENT-05` keystore-required test exists at `test_identity_keystore_required.py`, (b) key rotation is supported (`BrineProvider.rotate()` per Phase 1 BL-04). Marker: `pytest.mark.documents_only`. |

**Critical finding on AT-C fixture naming:** The existing fixtures in `invalid/` use `_at_c_surface` keys that don't match their filenames. AT-C1 fixture content is replay (`a1b2c3d4-...` reused envelope_id) but file is named `replayed-envelope` — yet AT-C1 in spec is *tampering*, not replay. **Plan 04-01 must reconcile fixture names with spec surface IDs OR add new fixtures with corrected names** (THERMO-06 obligation: each invalid fixture annotated with its AT-* surface; mismatched fixtures violate this). Recommended: keep existing files (don't break the existing MANIFEST), and either (a) rename fixtures in a single coordinated commit OR (b) acknowledge in MANIFEST that the existing `_at_c_surface` key inside the JSON file is the authoritative tag, the filename is human-friendly.

### Photophore AT-A* → `photophore/python/tests/at_negative/`

| AT-ID | Failure mode (from `photophore/README.md`) | Test file | Fixture | Assertion |
|-------|----------|-----------|---------|-----------|
| AT-A1 | Compromised sovereign node — terminal threat; structural defenses (audit immutability, key rotation, channel suspension). **Wired Phase 3.** | `test_at_a1_compromised_sovereign.py` | `invalid/AT-A1-channel-impersonation.json` (Phase 3 wired). | Re-export module pattern: `from ..integration.test_e2e_at_a1_replay import test_at_a1_replay_via_real_http`. Source test stays in `integration/`; `at_coverage.py` filename-scan sees `test_at_a1_*.py`. |
| AT-A2 | Shadow inference — shadow IDs MUST be unique per dispatch. | `test_at_a2_shadow_correlation.py` | `invalid/AT-A2-shadow-correlation.json` exists. | Property-test overlap: assert that `shadow.generate()` called 100× with identical content produces 100 distinct shadow_ids. Re-export from `test_shadow_uniqueness_property.py` OR thin wrapper. |
| AT-A3 | Classifier evasion — default to `local` for unmatched; explicit tag + path rule override. | `test_at_a3_classifier_evasion.py` | **MISSING — create `invalid/AT-A3-classifier-evasion.json`** with content crafted to look benign but containing a credential-like substring. | Assert `classify(crafted_content) == (Tier.LOCAL, "classifier:default")` OR `(Tier.LOCAL, "classifier:credential_pattern")` — never `SHARED`/`PUBLIC`. |
| AT-A4 | Channel MITM — envelope-level integrity via signatures; transport layer separate. | `test_at_a4_channel_mitm.py` | `invalid/AT-A4-audit-log-tampering.json` exists (misnamed — AT-A4 in spec is MITM, AT-A6 is audit tampering). | Tamper bytes in transit; verify rejects. Reuse forged-receipt test pattern. |
| AT-A5 | Trust store tampering — backed by platform keystore; audit log independently records dispatches. | `test_at_a5_trust_store_tampering.py` | `invalid/AT-A5-trust-store-colocation.json` exists. | Modify channel `ceiling` directly in the platform keystore (test fixture uses ephemeral keystore namespace); assert that audit log + trust-store discrepancy is detectable. May skip with rationale if v0.1 doesn't ship a tamper-detector. |
| AT-A6 | Audit log manipulation — chained hashes invalidate on tamper. | `test_at_a6_audit_log_tamper.py` | **MISSING — create `invalid/AT-A6-audit-log-tampering.json`.** Also covered by existing property test `test_audit_chain_property.py`. | Re-export from `test_audit_chain_property.py` OR direct: tamper a payload byte; `verify_chain()` returns `(False, broken_at)`. |

**Critical finding on AT-A fixture naming:** AT-A4 fixture file is `AT-A4-audit-log-tampering.json` but the spec says AT-A4 is MITM and AT-A6 is audit-log tampering. Either the fixture is mislabeled (and should be renamed to `AT-A6-...`) or the JSON's `_at_surface` key is what matters. Plan 04-01 must reconcile.

### Seamount AT-E* → `seamount/conformance/at_negative/`

The conformance harness at `seamount/conformance/forge_conformance/_harness.py` lines 321-336 marks all AT-E* as `skip` with "Phase 4 sweep" notes. Phase 4 wires real tests.

| AT-ID | Failure mode (from `seamount/README.md`) | Test file | Fixture | Assertion |
|-------|----------|-----------|---------|-----------|
| AT-E1 | Malicious envelope payloads — strict schema validation, size limits, reject unknown fields. | `test_at_e1_malicious_payload.py` | **MISSING — create `invalid/AT-E1-malicious-payload.json`** with intentionally malformed JSON, oversized field, or unknown top-level key. | POST to live forge; assert HTTP 400/422 with structured error code (`MALFORMED_ENVELOPE`). |
| AT-E2 | Resource exhaustion (DoS) — per-envelope size limits, per-task timeouts. | `test_at_e2_resource_exhaustion.py` | **MISSING — `invalid/AT-E2-resource-exhaustion.json`** with task asking for 10M digits of π. | POST `digits=10_000_000` to pi-forge; assert HTTP 400 OR timeout response within configured limit. Verify pi-forge has a size limit (read `pi-forge/server.py`). If no limit currently exists, this test exposes the gap — surface as Phase 4 fix in pi-forge. |
| AT-E3 | Tool escape / shell breakout — L2/L3 isolation, deny network, fs jail. | `test_at_e3_tool_escape.py` | **MISSING — `invalid/AT-E3-tool-escape.json`**. | For v0.1 there is no `shell`/plugin tool surface in either forge. Test asserts (a) pi-forge processes only `data.compute` task type, (b) describe-forge processes only `description.generate`, (c) any other task type returns `UNSUPPORTED_TASK_TYPE`. Marker: `pytest.mark.documents_only`. |
| AT-E4 | Forge impersonation — verify receipt sig against registered forge public key. | `test_at_e4_forge_impersonation.py` | **MISSING — `invalid/AT-E4-forge-impersonation.json`**. | Reuse Phase 3 `test_e2e_forged_receipt.py` pattern: spawn impersonator Flask app with different key; dispatch through Photophore; assert `DispatchError.RECEIPT_INVALID`. May re-export. |
| AT-E5 | Timing side channels — coarse-grain logs, avoid exposing fine-grained timing. | `test_at_e5_timing_side_channel.py` | **MISSING — `invalid/AT-E5-timing-side-channel.json`** (likely an empty/marker fixture). | `pytest.mark.documents_only`. Out-of-band timing harness is deferred (per Phase 3 SUMMARY line 478-481). Assert (a) `pi-forge/server.py` does NOT log per-request timing at granularity finer than seconds, (b) describe-forge returns deterministic output independent of input size. Document-only. |

**AT-E* fixtures land in `thermocline/thermocline/conformance/invalid/`** (matches Phase 1-3 convention; the conformance corpus is repo-level), with `phase: 4` MANIFEST entries.

### MANIFEST.yaml backfill (per CONTEXT carry-forward)

Existing MANIFEST.yaml at `thermocline/thermocline/conformance/MANIFEST.yaml` lines 19-25 lists only Phase 1 (AT-C1..C6) and Phase 3 (AT-A1). It does NOT enumerate AT-A2, AT-A4, AT-A5 (which have fixtures!) under any phase. Plan 04-01 must:

1. Add `phase: 2` entries for AT-A2, AT-A4, AT-A5 (these fixtures exist from Phase 2 but were never indexed). [Check 02-LEARNINGS for whether this is a Phase 2 oversight.]
2. Add `phase: 4` entries for AT-A3, AT-A6 (new fixtures).
3. Add `phase: 4` entries for AT-E1..E5 (new fixtures).
4. Each entry: `at_surface`, `phase`, `phase_wired`, `wired_test_path`, `wired_assertion`, `expect_error_code`, `notes`.


## Property Test Inventory (CONF-03)

Four invariants × `max_examples=200` per D-04 + one new dispatch-integrated property.

| # | Invariant | File | Current `max_examples` | Action |
|---|-----------|------|------------------------|--------|
| 1 | Classifier default fallthrough → `LOCAL` | `photophore/python/tests/test_classifier_default_property.py` | 100 (verified lines 19, 32) | Bump to 200 on both `@settings()` decorators. |
| 2 | Audit chain integrity (single-byte tamper invalidates) | `photophore/python/tests/test_audit_chain_property.py` | 100 (verified lines 58, 104) | Bump to 200 on both `@settings()` decorators. Note: existing test uses `args=integers(2,15).flatmap(...)` for 105 unique pairs — bumping to 200 examples will reuse pairs (acceptable; Hypothesis handles this). |
| 3 | Canonical-JSON round-trip stability | `thermocline/thermocline/python/tests/test_canonical_properties.py` | 200 (verified line 72) on Property 1; **100 on Properties 2, 5** (lines 93, 168) | Property 1 already at 200. Bump Properties 2 and 5 to 200. Property 3 + 4 have no `@settings()` decorator (rely on Hypothesis default of 100); add explicit `@settings(max_examples=200)`. |
| 4 | Shadow ID uniqueness | `photophore/python/tests/test_shadow_uniqueness_property.py` | 100 (verified line 22) | Bump to 200. Note: this test has 100 outer × 100 inner = 10,000 generate() calls; bumping outer to 200 = 20,000 inner calls — verify CI duration stays under 1 minute (Phase 2 LEARNINGS noted current runtime well under 1 minute). |
| 5 (new) | Dispatch-time shadow uniqueness (CONF-03 + AT-A2 + AT-C3 dispatch-integrated) | `photophore/python/tests/integration/test_property_dispatch_shadow_uniqueness.py` | — (new file) | Create. Reuse `subprocess_forge` fixture from `photophore/python/tests/integration/conftest.py`. Same source task envelope, dispatch N times through `dispatch_async()` against pi-forge; collect `outcome.envelope_id` and shadow_ids from intercepted pre-dispatch audit entries; assert all distinct. Recommended N: 200 outer × 1 inner (the dispatch IS the test). Marker: `pytest.mark.integration`. |

**Top-of-file comment for all five files:** `# CONF-03 invariant: <name>` so `tools/property_coverage.py` enumerates them.

**`property_coverage.py` implementation hint:** AST-parse each file; look for `# CONF-03 invariant:` line-comment OR module docstring containing `CONF-03 invariant`; for each `@settings(max_examples=N)` call, assert `N >= 200`. Single tool in `thermocline/tools/property_coverage.py` that scans all three repos (relies on sibling-clone layout) OR three tools (planner picks). Recommendation: one tool in thermocline, like `at_coverage_total.py` — keeps the cross-repo "this is a 4-of-4 invariant suite" property visible.

## CI Gate Inventory

### Existing gates (Phase 1-3)

**photophore (`photophore/.github/workflows/ci.yml`):**
- Job `lint-and-test` (ubuntu-latest):
  - `python tools/ast_lint_network_isolation.py python/src/ ../thermocline/thermocline/python/src/`
  - `pytest tests/ --ignore=tests/integration -q`
- Job `integration-and-conformance` (macos-latest, matrix `forge: [pi-forge, describe-forge]`):
  - `pytest tests/integration/ -xvs`
  - init + serve forge + `forge_conformance`

**seamount (`seamount/.github/workflows/ci.yml`):**
- `forge-unit-tests` (matrix forge × macos): `pytest tests/ -q` per forge
- `conformance` (matrix forge × macos): init + serve forge + `forge_conformance`
- `forge-conformance-harness-tests` (macos): `pytest tests/` for the conformance package itself

**thermocline: NO `.github/workflows/` exists** — Plan 04-01 creates `thermocline/.github/workflows/ci.yml` from scratch.

### Missing gates Phase 4 adds (per CONF-04)

CONTEXT D-09 + `<specifics>` line 394-404 enumerate the final gate list. Status of each:

| # | Gate | thermocline | photophore | seamount | Notes |
|---|------|-------------|------------|----------|-------|
| 1 | `ruff check` | NEEDS NEW WORKFLOW | EXISTS (implicit; ruff in dev deps but not in workflow file — VERIFY)** | MISSING from workflow | Add to all three. |
| 2 | `mypy --strict` | NEEDS NEW WORKFLOW (config in pyproject) | MISSING from workflow (config in pyproject) | MISSING (no mypy config in forge pyprojects) | **CONFLICT-04**: per `<specifics>` line 397, Plan 04-01 either adds `[tool.mypy] strict = true` to `seamount/pi-forge/pyproject.toml` + `seamount/describe-forge/pyproject.toml` OR documents exemption. Recommend: extend strict to forges (typed type-check is the only way to catch envelope-shape regressions); the forges are small (~5-10 source files each). If strict fails widely, document exemption in `seamount/docs/adr/` (no ADR yet — moves to v0.2). |
| 3 | `pip-audit` | NEEDS NEW WORKFLOW | MISSING from workflow (in dev deps) | MISSING | Add to all three. |
| 4 | Network-isolation AST lint | EXISTS in photophore tools, scans both repos | EXISTS | N/A | Plan 04-01 thermocline CI calls the photophore-relative lint OR ports it to `thermocline/tools/ast_lint_network_isolation.py`. Recommendation: COPY to `thermocline/tools/` so thermocline CI is self-contained. |
| 5 | `print(` AST lint (NEW) | NEW FILE | NEW FILE | NEW FILE | Three identical files OR one shared. Recommendation: three identical files; less coupling. |
| 6 | canonical-JSON no-`json.dumps` lint | EXISTS at `thermocline/thermocline/python/src/thermocline/scripts/check_no_json_dumps.py` | N/A | N/A | thermocline CI must invoke `thermocline-check-no-json-dumps` console script. |
| 7 | `at_coverage.py` (NEW) | NEW FILE — AT-C* coverage | NEW FILE — AT-A* coverage | NEW FILE — AT-E* coverage | Per D-01. |
| 8 | `at_coverage_total.py` (NEW) | NEW FILE — 17/17 union | — | — | thermocline-only roll-up. |
| 9 | `property_coverage.py` (NEW) | NEW FILE (recommended cross-repo) | — | — | Scans all three repos. |
| 10 | `pytest` | NEEDS NEW WORKFLOW | EXISTS | EXISTS | Existing pytest invocations cover. |
| 11 | `forge_conformance` against pi-forge + describe-forge | N/A | EXISTS (integration-and-conformance job) | EXISTS (conformance job) | No change. |

**Recommended Plan 04-01 task ordering for CI:**
1. Create `thermocline/.github/workflows/ci.yml` mirroring photophore shape.
2. Add new gates to all three workflows in same commit (atomic CI matrix change).
3. Order gates: **structural/lint gates BEFORE pytest** so missing-AT-coverage / print-lint failures surface as clear errors, not as pytest failures.

### CI YAML pattern Phase 4 should follow (mirror photophore CI shape)

```yaml
# thermocline/.github/workflows/ci.yml (NEW per Plan 04-01)
name: thermocline CI
on: [push, pull_request]
jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.11"}
      - name: Install
        working-directory: thermocline/python
        run: pip install -e .[dev]
      - name: Ruff
        working-directory: thermocline/python
        run: ruff check .
      - name: Mypy --strict
        working-directory: thermocline/python
        run: mypy --strict src/
      - name: Pip-audit
        run: pip-audit
      - name: Canonical-JSON lint (Pitfall 11)
        working-directory: thermocline/python
        run: thermocline-check-no-json-dumps
      - name: Print lint (CONF-06)
        run: python tools/ast_lint_no_print.py thermocline/python/src/
      - name: AT coverage (thermocline = AT-C*)
        run: python tools/at_coverage.py
      - name: AT coverage total (17/17)
        run: python tools/at_coverage_total.py
      - name: Property coverage (4 CONF-03 invariants @ max_examples=200)
        run: python tools/property_coverage.py
      - name: Pytest
        working-directory: thermocline/python
        run: pytest -q
  # macos-keystore job for tests that touch python-keyring (mirror photophore)
  keystore-tests:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.11"}
      - name: Install
        working-directory: thermocline/python
        run: pip install -e .[dev]
      - name: Pytest (keystore-tagged)
        working-directory: thermocline/python
        run: pytest -m keystore -q   # mark identity tests with @pytest.mark.keystore
```

## ADR Landings (D-03)

Seven forever-decisions in MADR-lite (Context · Decision · Consequences · Status). All seven decisions are documented somewhere already — RESEARCH only confirms source material exists.

| ADR | Repo | Path | Source material |
|-----|------|------|----------------|
| ADR-0001: Python 3.11 as primary language | thermocline | `thermocline/docs/adr/ADR-0001-python-3-11-as-primary-language.md` | PROJECT.md Key Decisions table line 108; CLAUDE.md "Language — Python 3.11+" |
| ADR-0002: Pydantic v2 lock-in | thermocline | `thermocline/docs/adr/ADR-0002-pydantic-v2-lock-in.md` | PROJECT.md Key Decisions line 113; pyproject.toml `pydantic>=2.7,<3.0` pin |
| ADR-0003: Single canonical JSON path | thermocline | `thermocline/docs/adr/ADR-0003-single-canonical-json-path.md` | THERMO-04; PITFALLS.md Pitfall 11; existing AST lint at `check_no_json_dumps.py` |
| ADR-0004: BLAKE3 with `algo_version` chain | thermocline | `thermocline/docs/adr/ADR-0004-blake3-with-algo-version.md` | AUDIT-02; PROJECT.md line 111; `_chain.py` `ALGO_VERSION_DEFAULT` |
| ADR-0005: No in-process key material | thermocline | `thermocline/docs/adr/ADR-0005-no-in-process-key-material.md` | IDENT-02, IDENT-05; CLAUDE.md "Tech — keys"; Phase 1 BL-03 (keystore-required test) |
| ADR-0001: Trust-store separation from audit log | photophore | `photophore/docs/adr/ADR-0001-trust-store-separation-from-audit-log.md` | CHAN-04; Phase 2 D-04 three-store model; existing test `test_channels_separation.py` |
| ADR-0002: No shadow caching | photophore | `photophore/docs/adr/ADR-0002-no-shadow-caching.md` | SHADOW-06; AT-A2/AT-C3; Phase 2 `test_shadow_no_caching.py` (verified existing) |

**Cross-references from each README:**
- `thermocline/README.md` adds §"Architecture Decision Records" linking to `thermocline/docs/adr/` (5 ADRs).
- `photophore/README.md` adds §"Architecture Decision Records" linking to `photophore/docs/adr/` (2 ADRs) + cross-ref `[ADR-0005](../thermocline/docs/adr/ADR-0005-no-in-process-key-material.md)` + `[ADR-0003](../thermocline/docs/adr/ADR-0003-single-canonical-json-path.md)` (used by photophore.audit + photophore.dispatch).
- `seamount/README.md` adds §"Architecture Decision Records" linking to relevant thermocline ADRs (ADR-0001 Python language, ADR-0003 canonical JSON, ADR-0005 no in-process key material). Seamount has no ADRs of its own per D-03.

**`docs/adr/index.md`** per repo: one-line bulleted list of ADRs with status. Generated by hand (no tool).


## Ops Docs Scope (CONF-07; D-05)

### `thermocline/docs/quickstart.md` — the 30-minute walkthrough

Canonical command sequence (verified against existing CLI surface in `photophore/python/src/photophore/cli/` and forge entrypoints):

```bash
# 1. Clone (assumes ~/Projects/dom/ — same as dev box; same as ADR cross-refs assume)
cd ~/Projects/dom
git clone https://github.com/graywhale/thermocline.git
git clone https://github.com/graywhale/photophore.git
git clone https://github.com/graywhale/seamount.git

# 2. Install (Python 3.11+ assumed; uv recommended; pip works)
cd thermocline/thermocline/python && pip install -e .[dev]
cd ../../../photophore/python && pip install -e .[dev]
cd ../../seamount/pi-forge && pip install -e .[dev]
cd ../describe-forge && pip install -e .[dev]
cd ../conformance && pip install -e .[dev]

# 3. Initialize sovereign-node + forge keystores (first time only)
python -m pi_forge init --keyring-service seamount.piforge
python -m describe_forge init --keyring-service seamount.describeforge
# Sovereign node's keypair created lazily by `photophore channel new`

# 4. Start a forge
python -m pi_forge serve --keyring-service seamount.piforge --port 5117 &
# Wait for "PIFORGE_READY port=5117"

# 5. Create a channel (TOFU pubkey fetch from running forge)
photophore channel new \
  --remote-node pi-forge-local \
  --ceiling tier-2 \
  --key-scheme brine \
  --fetch-pubkey-from http://localhost:5117

# 6. Dispatch a task
photophore dispatch \
  --channel <CHANNEL_ID_FROM_STEP_5> \
  --task examples/task-pi-100-digits.json \
  --forge-url http://localhost:5117

# 7. Query audit log
photophore audit query --channel <CHANNEL_ID>

# 8. Export audit log
photophore audit export > audit.jsonl
```

**Time budget:** install 12 min (cold pip install with dep resolution), keystore init 1 min (per-forge prompts for Keychain), channel new 2 min (TOFU fetch + pubkey verification), dispatch 1 min, audit query 1 min, audit export <1 min. Total ~17 min on clean macOS box with Python 3.11. Buffer for first-prompt Keychain "Allow / Always Allow / Deny" dialogs ~5 min. **Target hit: under 30 minutes.**

**macOS first-prompt gotchas to document:**
- First `pi-forge init` triggers Keychain prompt "pi-forge wants to access seamount.piforge". User must click "Always Allow" for the subsequent dispatch to work without re-prompting.
- Subsequent `photophore channel new` triggers another Keychain prompt for `thermocline.brine` service. Same pattern.
- On macOS, the Python process MUST be signed (Homebrew Python or pyenv-installed Python is fine; system Python 2.7-derived signatures may interfere). Document this if a user reports re-prompts on every dispatch.

**Section structure for `thermocline/docs/quickstart.md`:**
1. Prerequisites (Python 3.11+, macOS 12+ recommended)
2. Clone (sibling-clone layout matters for editable install paths)
3. Install (uv-recommended; pip alternative)
4. First-time keystore setup (per-forge, sovereign)
5. Start a forge (with `PIFORGE_READY` marker)
6. Create a channel (TOFU explanation + Keychain prompt)
7. Dispatch a task (happy path)
8. Inspect the audit log (query + export)
9. Cleanup (channel close, optional)
10. Next steps (link to per-repo docs/install.md, docs/ops.md, ADRs)

### Per-repo `docs/install.md` (D-05)

Each `docs/install.md` is shorter (~200-300 lines): system requirements, pip install command, keystore prerequisites, Apple Silicon Secure Enclave known-limitation note, first-run smoke test.

### Per-repo `docs/ops.md` (D-05)

- `thermocline/docs/ops.md` — empty/placeholder (library has no ops surface).
- `photophore/docs/ops.md` — chain archival (`photophore audit archive --reason "..."` — VERIFY this command exists; if not, surface as Phase 4 implementation gap), audit verify (`photophore audit verify`), channel ceiling rotation (`photophore channel set-ceiling`), channel close.
- `seamount/pi-forge/docs/install.md` — keystore init walkthrough.
- `seamount/describe-forge/docs/install.md` — keystore init + tier-1 shadow contract reminder.
- `seamount/conformance/docs/install.md` — running the harness against an arbitrary forge URL.

**VERIFY before plan:** `photophore audit archive` command — searched `audit_cmds.py`; need to confirm.

## `cli_invocation` Audit Retrofit (D-07)

### Audit enum slot status
- `AuditEventType.CLI_INVOKED = "cli.invoked"` already in `photophore/python/src/photophore/core.py` line 87. [VERIFIED]
- Already in `KNOWN_EVENT_TYPES` frozenset at line 102. [VERIFIED]
- Docstring at line 64-65 says "Phase 4 wires every CLI subcommand to emit one". The slot was intentionally pre-shipped.

### Helper function shape (new in Plan 04-01)

In `photophore/python/src/photophore/audit/__init__.py` or a new helper module:

```python
def append_cli_invocation(
    audit_log: AuditLog,
    *,
    subcommand: str,
    args: dict[str, str],
    outcome: str,  # "success" | "failure"
    exit_code: int,
    ts: str,
) -> AuditEntry:
    return audit_log.append(
        event_type=AuditEventType.CLI_INVOKED,
        channel_id=None,  # CLI invocations are pre-channel-resolution
        envelope_id=None,
        payload={
            "subcommand": subcommand,
            "args": args,
            "outcome": outcome,
            "exit_code": exit_code,
        },
        timestamp=ts,
    )
```

### `@audit_cli_invocation` decorator (new in Plan 04-01)

Wraps the click group declared in `photophore/python/src/photophore/cli/__init__.py`. Pattern:

```python
import functools
from datetime import datetime, timezone
import hashlib
import click
from pathlib import Path
import blake3
from ..audit import AuditLog, append_cli_invocation

def _sanitize_args(params: dict) -> dict[str, str]:
    """Hash file paths via BLAKE3; pass through ids/flags; never log content."""
    out = {}
    for k, v in params.items():
        if v is None:
            continue
        if isinstance(v, Path) or (isinstance(v, str) and Path(v).is_file()):
            try:
                content = Path(v).read_bytes()
                out[k] = f"blake3:{blake3.blake3(content).hexdigest()}"
            except OSError:
                out[k] = f"blake3:unreadable"
        else:
            out[k] = str(v)
    return out

def audit_cli_invocation(subcommand_name: str):
    def decorator(fn):
        @functools.wraps(fn)
        @click.pass_context
        def wrapped(ctx: click.Context, *args, **kwargs):
            ts = datetime.now(tz=timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
            outcome = "success"
            exit_code = 0
            try:
                return fn(ctx, *args, **kwargs)
            except SystemExit as e:
                outcome = "failure"
                exit_code = e.code if isinstance(e.code, int) else 1
                raise
            except Exception:
                outcome = "failure"
                exit_code = 1
                raise
            finally:
                try:
                    audit_log = AuditLog(ctx.obj["audit_db"])
                    append_cli_invocation(
                        audit_log,
                        subcommand=subcommand_name,
                        args=_sanitize_args(kwargs),
                        outcome=outcome,
                        exit_code=exit_code,
                        ts=ts,
                    )
                except Exception:
                    # Best-effort: failure-to-audit-the-audit must not change the user's exit.
                    pass
        return wrapped
    return decorator
```

**Where to apply:** every leaf click command in `audit_cmds.py`, `channel_cmds.py`, `classify_cmds.py`, `policy_cmds.py`, `dispatch_cmds.py`. Decoration order matters: `@click.command(...)` outermost, `@audit_cli_invocation("name")` inside, `@click.pass_context` innermost (or use `@click.pass_context` already inside the decorator as shown). VERIFY: click decorator stacking with custom decorators — tested pattern in click docs.

**Integration test for CLI-06 verification:** invoke each subcommand via `click.testing.CliRunner`, then query the audit DB and assert one `CLI_INVOKED` entry per invocation. Path: `photophore/python/tests/test_cli_invocation_audit.py`.


## CLI-07 Error Message Retrofit (D-08)

Three error paths:

| Subcommand | File | Current error | Phase 4 augmentation |
|------------|------|---------------|---------------------|
| `photophore dispatch` | `photophore/python/src/photophore/cli/dispatch_cmds.py` lines 89-96 | `f"error: dispatch failed ({exc.subcode}) at step {exc.stage}: {exc}. retryable: {str(exc.retryable).lower()}.{audit_note}"` | Append `(tier=X, reason=Y)` for `DispatchSubcode.POLICY_VIOLATED` and `DispatchSubcode.CLASSIFICATION_FAILED` cases. Requires plumbing tier/reason into `DispatchError` constructor — either as a new optional field OR as a structured message. Recommendation: add `blocked_block: BlockedBlock \| None = None` field where `BlockedBlock = NamedTuple("BlockedBlock", [("path", str), ("tier", str), ("reason", str)])`. |
| `photophore classify` | `photophore/python/src/photophore/cli/classify_cmds.py` | Per Phase 2 CLI-04 already emits `(tier, reason)` for successful classification. Error path (e.g., malformed rules YAML → `RulesConfigError`) does NOT. | Add `(tier, reason)` to `RulesConfigError`'s message when the failing rule has identifiable tier (most rules have one). |
| `photophore policy preview` | `photophore/python/src/photophore/cli/policy_cmds.py` | Emits the authored policy. When authoring would block (tier-0 channel with tier-1 content), the dry-run shows the policy. Error path may not surface tier/reason cleanly. | Augment `PolicyError` message with the offending block's `(tier, reason)`. |

**Test pattern:** pytest snapshot tests on CLI error output. Path: `photophore/python/tests/test_cli_error_messages.py` (NEW). Use `CliRunner.invoke()` + `assert "(tier=" in result.output`.

## `Sensitive[T]` Sweep (CONF-06 / D-09)

### Already wrapped (verified)
- `thermocline.envelope.ContentBlock.content: Sensitive[bytes] | None` (line 80) ✓
- `thermocline.canonical.canonicalize` accepts `Sensitive` via Pydantic core schema integration (`sensitive.py` line 75-132). ✓

### NOT wrapped — needs audit + decision per field

| Module | Field | Currently | Decision |
|--------|-------|-----------|----------|
| `thermocline.envelope._Shadow.abstraction` (line 65) | `str` | NOT wrapped | **Keep unwrapped.** Per Photophore quality table, abstractions ARE the wire-visible signal; wrapping would imply they should be redacted, but the whole point of an abstraction is to be visible on the wire. Document this distinction in ADR-0002 (no-shadow-caching) OR in a comment. |
| `thermocline.envelope._TaskBlock.instruction` (line 90) | `str` | NOT wrapped | **VERIFY.** Task instruction text could carry private content if the user puts it there. Spec is silent. Recommendation: leave unwrapped for v0.1 (the instruction is meant to be on the wire to the forge), document the decision in CHANGELOG ("Known limitation: `task.instruction` is wire-visible; users SHOULD avoid embedding private content."). |
| `thermocline.envelope._TaskBlock.parameters` (line 91) | `dict[str, Any]` | NOT wrapped | Same as instruction. |
| `thermocline.envelope.TaskResult.outputs` (line 259) | `dict[str, Any]` | NOT wrapped | Forge-produced; not user-input. Leave unwrapped. |
| `photophore.audit._types.AuditEntry.payload` (line 53) | `dict[str, Any]` | NOT wrapped | Payload is *intentionally* on disk; it's the proof. Leave unwrapped. BUT: ensure no `Sensitive[bytes]` ever leaks INTO the payload — payload should contain hashes/IDs/timestamps only. Add a runtime assertion at `AuditLog.append`: walk payload dict, raise if any value is a `Sensitive` instance. |
| `photophore.shadow._types.Shadow.shadow_id` | `str` (UUID) | NOT wrapped | Identifier, not content. Leave unwrapped. |
| `photophore.shadow._types.Shadow.abstraction` | `str` | NOT wrapped | Same as `_Shadow.abstraction`. Wire-visible. |
| `photophore.shadow._types.Shadow.content_type` | `str` | NOT wrapped | Coarse-grained label. |
| `photophore.shadow._types.Shadow.relevance` | `float` | NOT wrapped | Wire-visible. |
| `photophore.policy._author` ResultPolicy fields | `list[str]` | NOT wrapped | Output-field names, not content. |

### New test: `Sensitive[T]` redaction round-trip

Path: `photophore/python/tests/test_sensitive_redaction.py` (NEW) + `thermocline/thermocline/python/tests/test_sensitive_redaction.py` (already exists as `test_sensitive.py` — VERIFY scope). Enumerate Pydantic models with `Sensitive[*]` fields; assert `repr(model)` contains `<Sensitive: bytes>` for each.

### Runtime guard for audit payload
Add to `AuditLog.append` body in `_store.py`:

```python
def _assert_no_sensitive(payload: dict[str, Any]) -> None:
    from thermocline.sensitive import Sensitive
    for k, v in payload.items():
        if isinstance(v, Sensitive):
            raise AuditWriteError(
                f"Sensitive[T] value in audit payload field {k!r}; "
                f"audit log must not store privacy-sensitive content",
                code="AUDIT_SENSITIVE_LEAK",
            )
        if isinstance(v, dict):
            _assert_no_sensitive(v)
```

This is a runtime backstop on top of `Sensitive[T]` typing — defense in depth.

## `print(` AST Lint Scope (D-09 / CONF-06)

### Existing `print(` calls in library code paths

Verified scan (per `grep` results in research):

| Path | Use | Decision |
|------|-----|----------|
| `thermocline/thermocline/python/src/thermocline/scripts/check_no_json_dumps.py` lines 107-121 | Lint tool stderr output | **Allow** (mirrors `ALLOWLIST` of canonical-JSON lint — `scripts/` dir is dev tooling). |
| `seamount/pi-forge/server.py` lines 171-173 | Startup banner | **Allow** (server entry point, not library code). |
| `seamount/pi-forge/pi_forge/__main__.py` lines 52, 58, 62, 73 | `init` subcommand outputs + `PIFORGE_READY` marker | **Allow** (CLI entry point; the `PIFORGE_READY` print is contractual with subprocess_forge fixture in Phase 3). |
| `seamount/describe-forge/server.py` lines 134-136 | Startup banner | **Allow** (server entry point). |
| `seamount/describe-forge/describe_forge/__main__.py` lines 40, 46, 49, 60 | `init` subcommand outputs + `DESCRIBEFORGE_READY` marker | **Allow** (CLI entry point). |

**No other `print()` calls found in library code.** The lint will be green on first run if allow-list is configured correctly.

### `ast_lint_no_print.py` structure (mirror network-isolation lint)

```python
#!/usr/bin/env python3
"""AST lint forbidding `print(` in library code (CONF-06 / D-09).

Allows `print` only in:
  - CLI entry points (click subcommands use click.echo; forge init scripts use print)
  - Lint tools themselves (dev/CI tooling)
  - Test files (tests/)
  - Example files (examples/)
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

PROTECTED_FRAGMENTS: tuple[str, ...] = (
    "/src/thermocline/",
    "/src/photophore/",
)

ALLOWED_FRAGMENTS: tuple[str, ...] = (
    "/src/thermocline/scripts/",        # lint tools
    "/src/photophore/cli/",              # CLI uses click.echo elsewhere; allow defensive prints
    "/tests/",
    "/examples/",
)

# Forge-specific: pi-forge and describe-forge are flat-layout; allow their entry points.
ALLOWED_FORGE_FRAGMENTS: tuple[str, ...] = (
    "/pi-forge/server.py",
    "/pi-forge/pi_forge/__main__.py",
    "/describe-forge/server.py",
    "/describe-forge/describe_forge/__main__.py",
)

class _PrintVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.findings: list[int] = []
    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id == "print":
            self.findings.append(node.lineno)
        self.generic_visit(node)

# ... (mirror scan() + main() from ast_lint_network_isolation.py)
```

**Recommended location: three identical files** (`thermocline/tools/ast_lint_no_print.py`, `photophore/tools/ast_lint_no_print.py`, `seamount/tools/ast_lint_no_print.py`). Each CI workflow invokes its own. Less coupling than a shared file across repos.

## `SensitiveFilter` Logging Filter (D-09 / CONF-06)

### Current state
- **No `logging.py` module in photophore** (verified — no logging module found in photophore/python/src).
- **No existing `logger = logging.getLogger(__name__)` patterns** in photophore source (verified by grep).
- **Photophore is silent today** — output goes through `click.echo`. The filter must work for *future* logger consumers (downstream callers of photophore as a library).

### New module: `photophore/python/src/photophore/logging.py`

```python
"""Privacy-aware logging filter (CONF-06 / D-09).

Installs a logging.Filter that drops any record field whose value is a
Sensitive[T] instance OR whose key is in SENSITIVE_KEY_PATTERNS.

Photophore code that wants safe logging:
    from photophore.logging import configure_logging
    configure_logging()
    import logging
    logger = logging.getLogger(__name__)
    logger.info("dispatch", extra={"envelope_id": "abc", "content": sensitive_bytes})
    # The "content" field is dropped from the log record.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from thermocline.sensitive import Sensitive

_REDACTED = "<REDACTED>"

# Field names that always get redacted (defense in depth — typos like `Sensitive`-not-wrapping).
SENSITIVE_KEY_PATTERNS: tuple[str, ...] = ("content", "payload", "secret", "private_key", "seed", "bytes_hex")


class SensitiveFilter(logging.Filter):
    """Drops Sensitive[T] values from log records (CONF-06)."""

    def filter(self, record: logging.LogRecord) -> bool:
        # Walk record.__dict__ for any Sensitive instance.
        for k, v in list(record.__dict__.items()):
            if isinstance(v, Sensitive):
                setattr(record, k, _REDACTED)
            elif any(p in k.lower() for p in SENSITIVE_KEY_PATTERNS):
                if not isinstance(v, str) or len(v) > 8:
                    setattr(record, k, _REDACTED)
        # Walk record.args (positional format args).
        if isinstance(record.args, tuple):
            record.args = tuple(
                _REDACTED if isinstance(a, Sensitive) else a for a in record.args
            )
        elif isinstance(record.args, dict):
            record.args = {
                k: (_REDACTED if isinstance(v, Sensitive) else v)
                for k, v in record.args.items()
            }
        return True  # Always pass — we mutate, never drop.


def configure_logging(level: int = logging.INFO) -> None:
    """Install the default photophore logging config.

    Safe to call multiple times; idempotent.
    """
    root = logging.getLogger("photophore")
    if any(isinstance(f, SensitiveFilter) for f in root.filters):
        return
    root.setLevel(level)
    root.addFilter(SensitiveFilter())
```

### Test: `photophore/python/tests/test_logging_filter.py` (NEW)

Assert that `logger.info("dispatch", extra={"envelope": Sensitive(b"private")})` produces a log line with `<REDACTED>` and no `b"private"` substring. Use `caplog` fixture (built-in pytest).


## Release Script + CHANGELOGs (D-06 / CONF-08)

### `thermocline/scripts/tag-v0.1.0.sh`

**Directory does not exist yet** — Plan 04-02 creates `thermocline/scripts/`. (Verified: `ls /Users/dom/Projects/dom/thermocline/scripts/` returned "no such file".)

**Recommended script shape:**

```bash
#!/usr/bin/env bash
# tag-v0.1.0.sh — coordinate three v0.1.0 git tags across the Thermocline suite.
#
# Run from any directory. Reads THERMOCLINE_SUITE_ROOT (default: $HOME/Projects/dom).
# Asserts: clean working trees, branch=main, remote-up-to-date, pytest pass,
# CHANGELOG has `## [0.1.0] - <today>` heading. Then tags each repo on the same date.
#
# `--dry-run`: print what would happen; do NOT git tag.
# Operator MUST run `git push --tags` manually in each repo afterward.
set -euo pipefail

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=1
fi

SUITE_ROOT="${THERMOCLINE_SUITE_ROOT:-$HOME/Projects/dom}"
REPOS=(thermocline photophore seamount)
TODAY="$(date -u +%Y-%m-%d)"
TAG="v0.1.0"
TAG_MSG="${TAG} — coordinated with thermocline ${TAG} + photophore ${TAG} + seamount ${TAG}"

err() { echo "ERROR: $*" >&2; exit 1; }
note() { echo "  ✓ $*"; }
dry() { [[ "$DRY_RUN" == "1" ]] && echo "  [DRY] $*" && return 0; return 1; }

# Phase 1: precondition checks (read-only)
for repo in "${REPOS[@]}"; do
    REPO_PATH="$SUITE_ROOT/$repo"
    echo "Checking $repo at $REPO_PATH..."
    [[ -d "$REPO_PATH/.git" ]] || err "$repo: not a git repo"

    pushd "$REPO_PATH" >/dev/null

    # Clean working tree
    [[ -z "$(git status --porcelain)" ]] || err "$repo: working tree not clean"
    note "working tree clean"

    # Branch = main
    [[ "$(git rev-parse --abbrev-ref HEAD)" == "main" ]] || err "$repo: not on main"
    note "on main"

    # Remote up-to-date
    git fetch --quiet origin main
    LOCAL_SHA="$(git rev-parse HEAD)"
    REMOTE_SHA="$(git rev-parse origin/main)"
    [[ "$LOCAL_SHA" == "$REMOTE_SHA" ]] || err "$repo: not up-to-date with origin/main"
    note "remote up-to-date ($LOCAL_SHA)"

    # CHANGELOG entry exists for today
    CHANGELOG_PATH=""
    for cl in CHANGELOG.md thermocline/CHANGELOG.md; do
        [[ -f "$cl" ]] && CHANGELOG_PATH="$cl" && break
    done
    [[ -n "$CHANGELOG_PATH" ]] || err "$repo: no CHANGELOG.md found"
    grep -q "^## \[0.1.0\] - ${TODAY}$" "$CHANGELOG_PATH" || \
        err "$repo: CHANGELOG.md missing '## [0.1.0] - ${TODAY}' heading"
    note "CHANGELOG has 0.1.0 entry dated ${TODAY}"

    popd >/dev/null
done

# Phase 2: pre-tag lint sweep (per CONTEXT specifics)
for repo in "${REPOS[@]}"; do
    REPO_PATH="$SUITE_ROOT/$repo"
    pushd "$REPO_PATH" >/dev/null
    echo "Pre-tag lint sweep for $repo..."
    [[ -f tools/ast_lint_no_print.py ]] && python tools/ast_lint_no_print.py
    [[ -f tools/at_coverage.py ]] && python tools/at_coverage.py
    popd >/dev/null
done

# Phase 3: test suite
for repo in "${REPOS[@]}"; do
    REPO_PATH="$SUITE_ROOT/$repo"
    pushd "$REPO_PATH" >/dev/null
    echo "Running tests for $repo..."
    if [[ -d python ]]; then
        (cd python && pytest -q) || err "$repo: pytest failed"
    elif [[ -d thermocline/python ]]; then
        (cd thermocline/python && pytest -q) || err "$repo: pytest failed"
    fi
    # Forges have their own tests; loop through.
    for forge in pi-forge describe-forge conformance; do
        [[ -d "$forge" ]] && (cd "$forge" && pytest -q) || true
    done
    popd >/dev/null
done

# Phase 4: tag (with dry-run)
for repo in "${REPOS[@]}"; do
    REPO_PATH="$SUITE_ROOT/$repo"
    pushd "$REPO_PATH" >/dev/null
    echo "Tagging $repo with $TAG..."
    if dry "git tag -a $TAG -m \"$TAG_MSG\""; then
        :
    else
        git tag -a "$TAG" -m "$TAG_MSG"
        note "tagged $TAG"
    fi
    popd >/dev/null
done

echo ""
echo "All three repos tagged $TAG on $TODAY."
echo "Run 'git push --tags' in each repo to publish:"
for repo in "${REPOS[@]}"; do
    echo "    cd $SUITE_ROOT/$repo && git push --tags"
done
```

**macOS BSD vs GNU portability concerns:**
- `date -u +%Y-%m-%d` is portable.
- `grep -q "^## \[0.1.0\] - ..."` is portable (no `-P` PCRE flag).
- `git fetch --quiet`, `git rev-parse`, `git tag -a` are portable.
- No `sed -i` used (avoids the GNU/BSD `-i ''` divergence).
- `[[` is bash-specific but the shebang declares bash.

### CHANGELOG format (Keep-a-Changelog-lite per D-06)

**Template for each repo's CHANGELOG.md `## [0.1.0]` section:**

```markdown
## [0.1.0] - 2026-MM-DD

### Added
- (new functionality)

### Implemented
- THERMO-01 → spec patch cirdan→thermocline rename
- (one line per requirement ID this repo implements)

### Deferred to subsequent milestones
- Apple Silicon Secure Enclave hardware-anchored keystore entries (v0.2)
- Job envelopes + per-step shadow generation (Photophore spec v0.2)
- Ring 2 reconciliation protocol (v0.2)
- Trust score algorithm + model-based classifier (v0.3)
- Multi-hop channels + Ring 3 anchoring (v0.4)
- Per-content trust overrides (v0.5)
- Channel negotiation protocol (v1.0)
- Rust / TypeScript / Swift reference implementations (post-v0.1)

### Known limitations
- Default `python-keyring` macOS Keychain entries are software-backed
  (encrypted at rest, gated by user's login session). Hardware-anchored
  Secure Enclave entries require Apple Silicon + developer signing identity;
  deferred to v0.2. v0.1 threat model is satisfied without Secure Enclave.
- Linux + Windows ops paths documented best-effort; CI-tested matrix only
  covers ubuntu-latest (non-keystore) + macos-latest (keystore).
```

**Per-repo `Implemented` sections** (gathered from REQUIREMENTS.md traceability table):
- `thermocline`: THERMO-01..07, IDENT-01..05.
- `photophore`: CHAN-01..06, AUDIT-01..08, CLASS-01..06, SHADOW-01..06, POLICY-01..03, DISP-01..06, CLI-01..07.
- `seamount`: FORGE-01..05.
- Suite-wide (note in all three CHANGELOGs): CONF-01..08.

### thermocline `## [0.3.1]` CHANGELOG entry (NEW in Plan 04-02, for SP-3.3-01..03)

Append to existing `thermocline/thermocline/CHANGELOG.md` (the file exists; bumps from in-progress "v0.3.1" header to a dated entry).

```markdown
## [0.3.1] - 2026-MM-DD

### Spec amendments (SP-3.3-01..03 — Phase 3 surfaced; Phase 4 promotes to README)

- **SP-3.3-01 — Receipt-signature canonicalization invariant**: README §"Receipt Signatures" amended with normative paragraph requiring verifiers to canonicalize the envelope with `receipt_signature.sig = ""` (empty string), NOT removed. Cross-impl reproduction-by-reverse-engineering avoided.
- **SP-3.3-02 — Dispatch_signature pre-fill ordering**: README §"Dispatch Signatures" amended. All non-`sig` fields MUST be populated BEFORE canonicalization+signing.
- **SP-3.3-03 — Receipt field tolerance**: README §"Receipt Signatures" amended. Verifiers SHOULD accept `sig` OR `bytes_hex`; emitters MUST use `sig`.

`SUPPORTED_VERSIONS` in `thermocline-py` already includes `"0.3.1"` (Phase 1).

(Plus the existing "discovery phase" entries from before this amendment land.)
```


## Architecture Patterns

### Recommended Project Structure (post-Phase-4)

```
thermocline/                              # repo root (planning hub + spec + library)
├── .github/workflows/ci.yml             # NEW (Plan 04-01)
├── .planning/                           # planning hub (do not commit phase artifacts)
├── docs/                                # NEW (Plan 04-02)
│   ├── adr/                            # 5 ADRs
│   │   ├── ADR-0001-python-3-11-as-primary-language.md
│   │   ├── ADR-0002-pydantic-v2-lock-in.md
│   │   ├── ADR-0003-single-canonical-json-path.md
│   │   ├── ADR-0004-blake3-with-algo-version.md
│   │   ├── ADR-0005-no-in-process-key-material.md
│   │   └── index.md
│   ├── install.md
│   ├── ops.md                          # near-empty (library has no ops surface)
│   ├── quickstart.md                   # 30-min cross-repo walkthrough
│   └── index.md
├── scripts/                            # NEW (Plan 04-02)
│   └── tag-v0.1.0.sh
├── thermocline/                        # the actual library (existing nested path)
│   ├── README.md                       # AMEND (SP-3.3-01..03)
│   ├── CHANGELOG.md                    # EXTEND (## [0.1.0] + ## [0.3.1])
│   ├── conformance/
│   │   ├── invalid/                    # ADD AT-A3, AT-A6, AT-E1..E5 fixtures
│   │   ├── valid/
│   │   └── MANIFEST.yaml               # BACKFILL phase tags
│   ├── schema/
│   └── python/
│       ├── pyproject.toml
│       ├── src/thermocline/
│       └── tests/
│           ├── at_negative/            # NEW (Plan 04-01) — 6 AT-C* tests
│           └── ...
└── tools/                              # NEW (Plan 04-01)
    ├── ast_lint_no_print.py
    ├── ast_lint_network_isolation.py   # COPIED from photophore for self-contained CI
    ├── at_coverage.py                  # AT-C* (this repo)
    ├── at_coverage_total.py            # 17/17 roll-up (cross-repo)
    └── property_coverage.py            # 4/4 invariant check (cross-repo)

photophore/                              # repo root
├── .github/workflows/ci.yml             # EXTEND (new gates)
├── CHANGELOG.md                         # NEW (Plan 04-02)
├── README.md                            # ADD §"ADR" + §"Documentation"
├── docs/                                # NEW (Plan 04-02)
│   ├── adr/                            # 2 ADRs
│   │   ├── ADR-0001-trust-store-separation-from-audit-log.md
│   │   ├── ADR-0002-no-shadow-caching.md
│   │   └── index.md
│   ├── install.md
│   ├── ops.md
│   └── index.md
├── python/
│   ├── src/photophore/
│   │   ├── audit/                      # MOD: append_cli_invocation helper
│   │   ├── cli/__init__.py             # MOD: @audit_cli_invocation decorator
│   │   ├── cli/dispatch_cmds.py        # MOD: D-08 error message tweaks
│   │   ├── cli/classify_cmds.py        # MOD: D-08
│   │   ├── cli/policy_cmds.py          # MOD: D-08
│   │   ├── errors.py                   # MOD: BlockedBlock NamedTuple
│   │   └── logging.py                  # NEW: SensitiveFilter + configure_logging
│   └── tests/
│       ├── at_negative/                # NEW (Plan 04-01) — 6 AT-A* tests
│       ├── integration/test_property_dispatch_shadow_uniqueness.py  # NEW
│       ├── test_cli_invocation_audit.py                              # NEW
│       ├── test_cli_error_messages.py                                # NEW
│       ├── test_sensitive_redaction.py                               # NEW
│       └── test_logging_filter.py                                    # NEW
└── tools/
    ├── ast_lint_network_isolation.py   # EXISTING
    ├── ast_lint_no_print.py            # NEW
    └── at_coverage.py                  # NEW

seamount/                                # repo root
├── .github/workflows/ci.yml             # EXTEND (new gates)
├── CHANGELOG.md                         # NEW (Plan 04-02)
├── README.md                            # ADD §"ADR cross-refs" + §"Documentation"
├── pi-forge/
│   ├── docs/install.md                  # NEW
│   └── (existing)
├── describe-forge/
│   ├── docs/install.md                  # NEW
│   └── (existing)
├── conformance/
│   ├── docs/install.md                  # NEW
│   ├── at_negative/                     # NEW (Plan 04-01) — 5 AT-E* tests
│   ├── tests/                           # EXISTING (harness's own tests)
│   └── forge_conformance/               # EXISTING
└── tools/
    ├── ast_lint_no_print.py             # NEW
    └── at_coverage.py                   # NEW
```

### Pattern 1: AST lint mirror pattern
**What:** Phase 1's `check_no_json_dumps.py` + Phase 3's `ast_lint_network_isolation.py` set the template. Phase 4's new lints mirror it.
**When to use:** Any new structural rule that must run BEFORE pytest in CI.
**Example:**
```python
# Source: /Users/dom/Projects/dom/photophore/tools/ast_lint_network_isolation.py
PROTECTED_FRAGMENTS: tuple[str, ...] = (...,)
ALLOWED_FRAGMENTS: tuple[str, ...] = (...,)  # override

def check_file(path: Path) -> list[str]:
    if is_allowed(path): return []
    if not is_protected(path): return []
    tree = ast.parse(path.read_text())
    return [violation for node in ast.walk(tree) if ...]
```

### Pattern 2: Filename-based coverage gate
**What:** `at_coverage.py` greps `tests/at_negative/test_at_*.py` filenames, parses the AT-ID, asserts expected set.
**When to use:** When you want CI to fail with "missing AT-A4 coverage" not "test_foo failed".
**Example:**
```python
EXPECTED = {"AT-A1", "AT-A2", "AT-A3", "AT-A4", "AT-A5", "AT-A6"}
def main() -> int:
    pattern = re.compile(r"test_at_([acer])(\d+)_")
    found = set()
    for p in Path("tests/at_negative").glob("test_at_*.py"):
        m = pattern.match(p.name)
        if m: found.add(f"AT-{m.group(1).upper()}{m.group(2)}")
    missing = EXPECTED - found
    if missing:
        print(f"FAIL: missing coverage for {sorted(missing)}", file=sys.stderr)
        return 1
    return 0
```

### Pattern 3: Decorator-wrapped click subcommand
**What:** `@audit_cli_invocation("name")` wraps each leaf click command in try/finally that writes an audit entry.
**When to use:** CLI-06 retrofit — every subcommand emits an audit entry regardless of outcome.
**Example:** See `## cli_invocation Audit Retrofit (D-07)` section above.

### Anti-Patterns to Avoid

- **`print(envelope)` anywhere in library code:** triggers Pitfall 4 (private bytes leak). Use the new `print(` AST lint to prevent.
- **`json.dumps(envelope)` for signing input:** already enforced by existing `check_no_json_dumps.py`. Don't regress.
- **Reusing test envelope_ids across AT-* tests:** UUID collision would mask real dedupe bugs. Use `uuid.uuid4()` fresh per test.
- **`@settings(max_examples=200, deadline=10000)`:** Hypothesis `deadline` default is 200ms per example. Property tests with subprocess fixtures need `deadline=None`. Verify each property test.
- **Hardcoded SUITE_ROOT in tag-v0.1.0.sh:** the script reads `$THERMOCLINE_SUITE_ROOT` env var; tests of the script (if any) need a clean sandbox.
- **Hand-rolling MADR template:** use the existing thermocline ADR template if one exists; otherwise the one-page Context/Decision/Consequences/Status structure is reference-implementation-quality (no library needed).
- **Tagging without `git push --tags` reminder:** the script PRINTS the reminder but does NOT auto-push. Trust-is-never-automated principle.
- **Modifying existing fixtures in `invalid/`:** they are versioned wire-format references. Renames break cross-language ports. If a rename is needed, deprecate-then-add.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Property-based testing | Custom case generator | `hypothesis` (already in dev deps) | Existing tests show the pattern; new dispatch property reuses the strategy. |
| AST analysis | Regex over source code | `ast` stdlib module | False positives on regex (comments, identifiers). AST is precise. |
| BLAKE3 hashing | Hand-implement / subprocess to `b3sum` | `blake3` Python package (already in deps) | Used for audit chain + CLI arg sanitization. |
| Bash shell escaping in `tag-v0.1.0.sh` | Manual quoting | `set -u`; quote ALL variable expansions with `"$var"`; use `[[` not `[` | Subtle quoting bugs in release scripts are infamous. Keep it simple. |
| Date formatting | `date +%Y-%m-%d` per BSD format string differences | `date -u +%Y-%m-%d` (UTC; portable on macOS + Linux) | Avoids surprises. |
| CHANGELOG parsing | Markdown parser | Simple `grep -q "^## \[0.1.0\] - "` regex | Keep-a-Changelog format is grep-friendly by design. |
| Click decorator stacking | Custom inspection | Click's `@click.pass_context` plus `functools.wraps` | Documented click pattern. |
| Cross-process pubkey registration in tests | Re-implement | Phase 3 `_force_real_keyring_backend` autouse fixture | Already solved; reuse. |
| ADR template | Custom format | MADR-lite (Context/Decision/Consequences/Status) | Lightweight standard; one-page max per D-03. |
| Logging filter | Custom logger class | `logging.Filter` subclass | Stdlib pattern; `caplog` pytest fixture works with it. |

**Key insight:** Phase 4 is mostly assembly of existing patterns + a few new lints. Every "Don't Build" row is genuinely satisfied by an existing library or established pattern.


## Runtime State Inventory

Phase 4 is primarily additive (new files, new audit entry kind, new lints). No rename or refactor. The minimal state inventory:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | Audit log SQLite stores `cli.invoked` rows after Phase 4 lands. **No migration needed**: audit log is append-only and the new kind is added to `KNOWN_EVENT_TYPES` (slot already pre-shipped in `core.py` line 87). Existing chains continue to read; new entries chain onto the head. | none |
| Live service config | None — Phase 4 ships no service configuration. | none |
| OS-registered state | None — no new keystore entries beyond what Phase 1-3 created. Re-running the sample dispatch in `quickstart.md` may create a new sovereign-node entry (`thermocline.brine` service); this is documented as expected behavior. | none |
| Secrets / env vars | `$THERMOCLINE_SUITE_ROOT` is a new env var the release script reads. Default: `$HOME/Projects/dom`. Not a secret; no rotation. | none |
| Build artifacts / installed packages | After Plan 04-02 lands `## [0.1.0]` CHANGELOG entries, all four pyproject.toml files (`thermocline`, `photophore`, `pi-forge`, `describe-forge`, `forge_conformance`) keep their existing version strings unless someone wants v0.1.0 to map to a new package version. **Recommend: keep pyproject.toml versions at their current (e.g., 0.3.1) values** — the v0.1.0 git tag is the suite milestone, not the package version. Reasons: (a) `thermocline` package version tracks the spec version; (b) `photophore` package follows photophore spec; (c) the v0.1.0 tag is a suite coordination point. | Document in CHANGELOG: "git tag v0.1.0 = suite milestone; package versions per spec." |

**Nothing found in category "live service config" / "OS-registered state":** Verified — no Datadog tags, no Cloudflare tunnels, no Tailscale ACLs, no pm2 process names, no Task Scheduler entries reference Phase 4 outputs.

## Environment Availability

External dependencies the phase needs:

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All phases | ✓ (assumed) | 3.11+ | none — required |
| `git` | Release script + commits | ✓ (assumed) | 2.x | none |
| `bash` | Release script | ✓ | 3.2+ | macOS ships 3.2; script uses `set -euo pipefail` + `[[` which work in 3.2 |
| `hypothesis` | Property tests | ✓ | 6.0+ (verified in pyprojects) | none |
| `blake3` Python | Audit chain + CLI arg sanitization | ✓ | 1.0.8+ (verified in photophore deps) | could use `hashlib.sha256` if absent, but D-07 standardizes on BLAKE3 |
| `python-keyring` | Quickstart Keychain prompts | ✓ | 25+ (verified) | none |
| `click` | CLI decorator wiring | ✓ | 8.3+ (verified) | none |
| `pytest` | Test runs in release script | ✓ | 8.0+ | none |
| `mypy` (strict) on forges | CI gate (CONF-04 #2) | ✗ on seamount forges | — | **CONFLICT-04**: either add `[tool.mypy] strict = true` to forge pyprojects, OR document exemption. Decision deferred to planner. |
| GitHub Actions runner image with `macos-latest` (for keystore tests) + `ubuntu-latest` (for lint/non-keystore tests) | CI gates | ✓ (existing CI uses both) | — | none |

**Missing dependencies with no fallback:** none for runtime; **`mypy --strict` on seamount forges** is the only ambiguous slot (CONFLICT-04).

**Missing dependencies with fallback:** none.

## Common Pitfalls

### Pitfall 1: Property test `max_examples=200` saturates Hypothesis pair-strategy

**What goes wrong:** `test_audit_chain_property.py` uses `args=integers(2,15).flatmap(lambda n: integers(0, n-1).map(...))` — this generates 105 *unique* (n_entries, tamper_index) pairs. Bumping `max_examples` to 200 means Hypothesis must reuse pairs (deterministic stable shrinking still works, but you get duplicate examples).

**Why it happens:** Strategy space is bounded by parameter ranges; 200 > 105 forces saturation.

**How to avoid:** Either widen the parameter range (`integers(2,30)` gives 405 unique pairs) OR document that 105 unique cases × ~2 average reuse = 200 effective. Recommendation: widen the range so 200 = 200 distinct cases. Edit `test_audit_chain_property.py` `min_value=2, max_value=15` → `max_value=20` for ≥210 unique pairs.

**Warning signs:** Hypothesis prints `Falsifying example: ...` on every duplicate; CI takes longer than expected.

### Pitfall 2: macOS Keychain prompt on every CI test run

**What goes wrong:** `macos-latest` GH runner has no logged-in user; Keychain operations may prompt or fail silently.

**Why it happens:** `python-keyring` macOS backend defaults to the user's login keychain.

**How to avoid:** Phase 3 already solved this with the `_force_real_keyring_backend` autouse fixture in `photophore/python/tests/integration/conftest.py`. Phase 4's new keystore-touching tests (if any) reuse this fixture OR use an ephemeral namespace (`seamount.ci-test` per existing pattern).

**Warning signs:** CI hangs on macos-latest; tests pass locally but fail on CI.

### Pitfall 3: AT-* fixture filename ↔ surface ID mismatch

**What goes wrong:** Existing fixtures like `AT-A4-audit-log-tampering.json` actually describe AT-A6 (audit log tampering, not channel MITM). Plan 04-01's `at_coverage.py` filename scan trusts the filename.

**Why it happens:** Phase 1-2 fixture naming was preliminary; the spec text moved.

**How to avoid:** Audit each existing fixture's filename against its `_at_surface` JSON key BEFORE writing `at_coverage.py`. Rename if needed (single coordinated commit) and update MANIFEST. Alternative: `at_coverage.py` parses the JSON `_at_surface` key, not the filename — more robust, slightly more complex.

**Warning signs:** `at_coverage.py` reports "all 6 AT-A* present" but the AT-A4 test actually exercises AT-A6 behavior.

### Pitfall 4: `print(` lint false-positive on `print` as variable name

**What goes wrong:** AST visitor matches `print(x)` Call nodes. But `print = some_func; print(x)` is a different `print` — visitor flags it anyway.

**Why it happens:** Local rebinding of `print` is rare in real code but legal.

**How to avoid:** Document the lint's precision in its docstring; lint catches `print(` as a *call to the builtin* by default (don't try to track rebinding). If a library file deliberately rebinds `print` for tests, allow-list the file.

**Warning signs:** Unexpected lint failure on a file that obviously doesn't call the builtin `print`.

### Pitfall 5: BSD `grep -P` not available in `tag-v0.1.0.sh`

**What goes wrong:** GNU `grep` supports `-P` (Perl regex); BSD `grep` (default on macOS) does not. The CHANGELOG heading check uses `grep -q` (POSIX BRE), which is portable — but careless edits could introduce `-P`.

**Why it happens:** Developers test on Linux runners; first macOS run fails.

**How to avoid:** Stick to POSIX BRE in `tag-v0.1.0.sh`. CI for the release script (if any) should run on macos-latest.

**Warning signs:** Release rehearsal works in CI Linux but fails on the maintainer's macOS box.

### Pitfall 6: Click decorator order with `@audit_cli_invocation`

**What goes wrong:** Click decorators are order-sensitive. `@click.command()` must be outermost; `@click.pass_context` MUST be the innermost click decorator. Custom decorators like `@audit_cli_invocation` placed between `@click.command()` and `@click.option(...)` break click parameter detection.

**Why it happens:** click's decorator stack uses metadata stored on the wrapped function; custom decorators that wrap WITHOUT preserving `__wrapped__` lose the click metadata.

**How to avoid:** Decoration order: `@click.command(...)`, then `@click.option(...)` (any number), then `@audit_cli_invocation("name")`, then `@click.pass_context` (innermost), then the function body. Use `@functools.wraps(fn)` inside `audit_cli_invocation` to preserve click metadata.

**Warning signs:** click reports "no such option --channel" on a command that clearly declares `--channel`.

### Pitfall 7: `Sensitive[T]` Pydantic round-trip with non-bytes inner type

**What goes wrong:** `Sensitive.__get_pydantic_core_schema__` is specialized for `Sensitive[bytes]` (sensitive.py line 81). Wrapping `str` or `dict` works at runtime but Pydantic serialization defaults to `str(value)`, which may not round-trip.

**Why it happens:** Per the docstring, the wrapper is bytes-specialized.

**How to avoid:** Stick to `Sensitive[bytes]` for v0.1. If a different inner type is needed, extend `__get_pydantic_core_schema__`. Phase 4 sweep should NOT introduce `Sensitive[dict]` or `Sensitive[str]`.

**Warning signs:** Pydantic validation errors on a model that previously round-tripped.

### Pitfall 8: Tagging before CI is green

**What goes wrong:** Operator runs `tag-v0.1.0.sh` while CI is mid-run on a recent push. Tags land on the local commit, but the CI may later fail and require a new commit, leaving the tag at a no-longer-canonical SHA.

**Why it happens:** Operator pressure to ship.

**How to avoid:** Script's "remote up-to-date" check + manual pre-tag CI verification. Document in `tag-v0.1.0.sh` README: "Verify GitHub Actions are green on `origin/main` before running this script."

**Warning signs:** Post-tag, someone notices a failing CI run on the tagged SHA.


## Code Examples

### Example 1: AT-* negative test scaffold (mirror Phase 3 AT-A1 pattern)

```python
# Source: /Users/dom/Projects/dom/photophore/python/tests/integration/test_e2e_at_a1_replay.py (Phase 3 pattern)
# Path for Plan 04-01: photophore/python/tests/at_negative/test_at_a3_classifier_evasion.py

"""AT-A3: Classifier evasion — content crafted to bypass classifier MUST default to LOCAL.

Failure mode (from photophore/README.md §"Attack Surfaces and Mitigations"):
    Content is crafted to bypass the classifier — structured to avoid credential
    patterns, PII patterns, and sensitive file type detection, causing the
    classifier to assign `shared` or `public` to content that should be `local`.

Mitigation under test: v0.1 classifier defaults all unmatched content to LOCAL
(CLASS-04, CLASS-06). The classifier-evasion attack is NOT a code bug if the
classifier returns LOCAL — that IS the correct conservative default.
"""
from __future__ import annotations

import pytest

from photophore.classifier import classify
from photophore.core import Tier


@pytest.mark.at_surface("AT-A3")
def test_classifier_evasion_defaults_to_local() -> None:
    """Crafted-benign content with hidden credential-like substring → LOCAL."""
    # Content designed to evade pattern matchers: no obvious credential markers,
    # but contains a substring that could be a password if interpreted as such.
    crafted = b"normal looking text with hidden p4ssw0rd123 buried in prose"
    result = classify(crafted, path=None, rules=None)
    assert result.tier == Tier.LOCAL, (
        f"AT-A3: crafted content classified as {result.tier!r} "
        f"with reason {result.reason!r}; classifier MUST default to LOCAL "
        f"(CLASS-04 zero-trust default; AT-A3 mitigation)"
    )


@pytest.mark.at_surface("AT-A3")
def test_classifier_evasion_never_promotes_to_public() -> None:
    """Any classification result MUST NOT promote unmatched content to PUBLIC."""
    crafted = b"completely innocuous-looking text that an attacker could control"
    result = classify(crafted, path=None, rules=None)
    assert result.tier != Tier.PUBLIC, (
        f"AT-A3: classifier promoted content to PUBLIC; classifier MUST NEVER "
        f"infer-promote to PUBLIC (CLASS-04)"
    )
```

### Example 2: `at_coverage.py` per-repo

```python
#!/usr/bin/env python3
"""AT-* coverage gate for photophore (AT-A1..A6).

Globs photophore/python/tests/at_negative/test_at_*.py and asserts
all six AT-A surfaces have at least one test file.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

EXPECTED: frozenset[str] = frozenset({
    "AT-A1", "AT-A2", "AT-A3", "AT-A4", "AT-A5", "AT-A6",
})

PATTERN = re.compile(r"^test_at_a(\d+)_")


def main() -> int:
    here = Path(__file__).resolve().parent.parent / "python" / "tests" / "at_negative"
    if not here.is_dir():
        print(f"FAIL: {here} does not exist", file=sys.stderr)
        return 1
    found: set[str] = set()
    for p in sorted(here.glob("test_at_*.py")):
        m = PATTERN.match(p.name.lower())
        if m:
            found.add(f"AT-A{m.group(1)}")
    missing = EXPECTED - found
    if missing:
        print(f"FAIL: missing AT-A coverage: {sorted(missing)}", file=sys.stderr)
        print(f"Found: {sorted(found)}", file=sys.stderr)
        return 1
    print(f"ok: AT-A coverage complete ({len(found)}/6).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### Example 3: MADR-lite ADR template

```markdown
# ADR-0003: Single canonical JSON path

**Status:** Accepted · 2026-MM-DD

## Context

The Thermocline envelope is signed with ed25519 over its serialized bytes. If
the signer and verifier compute different bytes from the same logical envelope,
no signature ever verifies. RFC 8785 (JSON Canonicalization Scheme) defines a
deterministic serialization: keys sorted, whitespace normalized, ECMA-262
number formatting. Implementations that hand-roll JSON serialization (e.g.,
`json.dumps(envelope, sort_keys=True)`) produce subtly different bytes for
floats, Unicode, or zero-prefixed integers — a notorious cross-language drift
class.

## Decision

`thermocline-py` exposes exactly one canonicalization path:
`thermocline.canonical.canonicalize(payload: Mapping) -> bytes`, implemented
via the `rfc8785` library. All signing input across the suite (Photophore
dispatch coordinator, forge receipt signing, conformance harness verification)
goes through this single function. A CI lint
(`thermocline/python/src/thermocline/scripts/check_no_json_dumps.py`) forbids
`json.dumps`/`json.dump` calls in library code outside an explicit allow-list.

## Consequences

- ✓ Cross-impl signature verification works on first attempt (any v0.3.1
  conformant impl produces byte-identical canonical bytes).
- ✓ Adding a new envelope field is automatically signed correctly.
- ✗ Dev/CI tooling that emits human-readable JSON (build_schemas, debug
  printouts) must be explicitly allow-listed.
- ✗ Performance: `rfc8785` is slower than `json.dumps` for large envelopes;
  this is acceptable for envelope-sized payloads.

## References

- RFC 8785: https://www.rfc-editor.org/rfc/rfc8785
- Pitfall 11 in `.planning/research/PITFALLS.md`
- Lint: `thermocline/python/src/thermocline/scripts/check_no_json_dumps.py`
```

### Example 4: ADR cross-reference from photophore README

```markdown
## Architecture Decision Records

Forever-decisions that bind this implementation:

### Photophore-specific
- [ADR-0001: Trust-store separation from audit log](docs/adr/ADR-0001-trust-store-separation-from-audit-log.md)
- [ADR-0002: No shadow caching](docs/adr/ADR-0002-no-shadow-caching.md)

### Inherited from `thermocline-py`
- [ADR-0001: Python 3.11 as primary language](../thermocline/docs/adr/ADR-0001-python-3-11-as-primary-language.md)
- [ADR-0003: Single canonical JSON path](../thermocline/docs/adr/ADR-0003-single-canonical-json-path.md)
- [ADR-0004: BLAKE3 with `algo_version` chain](../thermocline/docs/adr/ADR-0004-blake3-with-algo-version.md)
- [ADR-0005: No in-process key material](../thermocline/docs/adr/ADR-0005-no-in-process-key-material.md)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `mypy --strict` skipped on forges (Phase 3) | Plan 04-01 either adds strict to forges OR documents exemption | Phase 4 | CONF-04 #2 — full type discipline on every package the suite ships. |
| AT-A1 only AT-* surface wired (Phase 3) | All 17 surfaces wired with at least one negative test (Plan 04-01) | Phase 4 | CONF-02 satisfied; CI counts coverage. |
| Property tests at `max_examples=100` | Bump to 200 (D-04); add dispatch-integrated property | Phase 4 | CONF-03 cadence; headroom on existing properties. |
| SP-3.3-01..03 documented inline in coordinator (Phase 3 SUMMARY) | Promoted to Thermocline README amendments (D-02) | Phase 4 | Cross-impl ports don't reverse-engineer Python coordinator. |
| `cli_invocation` enum slot present but unused (Phase 2) | Every CLI subcommand emits an entry (D-07) | Phase 4 | CLI-06 satisfied; audit log is complete proof. |
| No `print(` lint | AST lint enforced in CI (D-09) | Phase 4 | CONF-06 satisfied. |
| No `Sensitive[T]` runtime guard in audit payload | `AuditLog.append` rejects payload containing `Sensitive` (recommended) | Phase 4 | Defense in depth on top of static typing. |
| `python-keyring` macOS Keychain entries software-encrypted (Phase 1) | Same; Apple Silicon Secure Enclave entries deferred to v0.2 | v0.2 | D-11 — documented as known limitation. |

**Deprecated / outdated:**
- ROADMAP.md Phase 4 status column says "Phase 3: Not started" (line 147) — this is stale; Phase 3 is complete per STATE.md. Plan 04-02's documentation pass MAY refresh this if convenient, but it's a `gsd-transition` artifact and not required.
- The `_ResultPolicy` private alias in `thermocline/envelope.py` line 114 — Phase 2 LEARNINGS noted "Phase 4 may remove it once all callers have migrated." Plan 04-02 should grep for `_ResultPolicy` usage; if zero hits outside Phase 1 backward-compat tests, remove. If any production usage, keep through v0.1 and target v0.2 removal.


## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | `IdentityProvider` Protocol (delegated to platform keystore via PyNaCl + python-keyring). No password auth in v0.1 — node identity = ed25519 keypair. |
| V3 Session Management | partial | "Sessions" = channels. Trust ceiling lowered unilaterally; raised by deliberate human act + audit entry (CHAN-03). No HTTP-session-like state. |
| V4 Access Control | yes | Trust ceiling per channel (tier-0/1/2). `result_policy` issuer-authored, forge-immutable (POLICY-01). |
| V5 Input Validation | yes | Pydantic v2 strict mode (THERMO-03 `extra="forbid"`); RFC 8785 canonical JSON for signing input; AT-E1 negative test (Phase 4 new) for malformed payloads. |
| V6 Cryptography | yes | PyNaCl (libsodium) for ed25519; BLAKE3 for audit chain (`algo_version` versioned). No hand-rolled crypto. |
| V7 Error Handling and Logging | yes | `SensitiveFilter` logging filter (Phase 4 new); structured error codes per CLI subcommand; D-08 augments errors with `(tier, reason)`. |
| V9 Communications | partial | Transport-agnostic; envelope-level signatures provide integrity independent of transport. AT-A4 (MITM) covered by signature verification. |
| V10 Malicious Code | yes | `pip-audit` CI gate (CONF-04 #3); MIT-licensed deps; no `pickle` anywhere; AST lints enforce structural rules. |
| V11 Business Logic | yes | Audit log append-only by construction (SQLite trigger); shadow IDs unique per dispatch (no caching); classifier conservative default. |
| V14 Configuration | yes | `python-keyring` is the only key store; refuses to start without it (IDENT-05). Three-store separation enforced (D-04 Phase 2). |

### Known Threat Patterns for Python Privacy-Tiered Dispatch

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Envelope tampering in transit | Tampering | Dispatch signature over canonical JSON; verify-before-process (AT-C1 negative test). |
| Envelope replay | Tampering / Repudiation | UUID envelope_id; receiver replay cache (AT-C2 negative test). |
| Shadow inference | Information Disclosure | Per-dispatch shadow IDs; varied abstraction phrasing; irreversibility test (AT-A2 + AT-C3 property + negative tests). |
| Forged dispatch signature | Spoofing | Verify against registered public key; key_scheme dispatch (AT-C4 negative test). |
| Result policy escalation | Elevation of Privilege | result_policy in signed envelope; sovereign-node enforces on receipt (AT-C5 negative test). |
| Key compromise | Spoofing | Hardware-backed keystore where available; rotation API; revocation propagates (AT-C6 documents-only test). |
| Compromised sovereign node | Elevation of Privilege | Terminal threat; structural defenses: audit immutability, rotation, channel suspension (AT-A1 wired Phase 3). |
| Classifier evasion | Information Disclosure | Default LOCAL; explicit tag override (AT-A3 negative test — Phase 4 new). |
| Channel MITM | Tampering / Information Disclosure | Envelope signatures + TLS recommended (AT-A4 negative test). |
| Trust store tampering | Tampering | Platform keystore + audit log cross-check (AT-A5 negative test). |
| Audit log manipulation | Repudiation | Chained hashes; tamper invalidates all subsequent entries (AT-A6 negative test — Phase 4 new + property test). |
| Malicious envelope payload | DoS / Tampering | Pydantic strict + size limits (AT-E1 negative test — Phase 4 new). |
| Resource exhaustion | DoS | Per-task timeouts; forge-side limits (AT-E2 negative test — Phase 4 new). |
| Tool escape / shell breakout | Elevation of Privilege | v0.1 forges have no shell/plugin surface; AT-E3 documents-only. |
| Forge impersonation | Spoofing | Verify receipt sig against registered forge pubkey (AT-E4 negative test — reuse Phase 3 forged-receipt pattern). |
| Timing side channel | Information Disclosure | Coarse-grained logging; AT-E5 documents-only (out-of-band rig deferred). |
| Sensitive content leak via `repr`/log | Information Disclosure | `Sensitive[T]` wrapper + `SensitiveFilter` + `print(` lint (CONF-06; Phase 4 ships all three). |
| Trust-store ↔ audit-log co-location | Tampering | Three-store separation enforced (CHAN-04 + Phase 2 D-04; test exists). |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The 100-example bump to 200 for `test_shadow_uniqueness_property.py` (200 outer × 100 inner = 20,000 calls) completes in under 1 minute on CI runner | Property Test Inventory | CI time inflation. Mitigation: time the bump locally before commit; if >1 min, document and ship at 200 anyway (CONF-03 says ≥100). [ASSUMED] |
| A2 | The conflicting AT-A4 fixture naming (file says "audit-log-tampering" but spec says AT-A4 is MITM) is a Phase 1-2 naming error, not an intentional remapping | AT-* Surface Inventory | If intentional, our renaming break cross-language ports that read the existing filenames. Mitigation: verify with git history / Phase 1 LEARNINGS before renaming. [ASSUMED] |
| A3 | The existing `AT-C5-unsupported-version.json` fixture is misnamed (AT-C5 is result-policy escalation; unsupported version is THERMO-07) | AT-* Surface Inventory | Same as A2 — rename break. Mitigation: dual-fixture approach (keep old, add new with corrected name). [ASSUMED] |
| A4 | `photophore audit archive` command exists OR can be added in Plan 04-02 ops docs | Ops Docs Scope | If absent, ops.md describes nonexistent surface. Mitigation: VERIFY by reading `audit_cmds.py` before plan-phase. [ASSUMED] |
| A5 | The `BlockedBlock` NamedTuple proposal for D-08 is preferable to a free-form error message string | CLI-07 Error Message Retrofit | If planner picks string-based, less structured error inspection. Mitigation: string-based is acceptable; D-08 says "string-formatting tweaks." [ASSUMED — recommendation] |
| A6 | `mypy --strict` on seamount forges will pass with minor edits (the forges are small enough to type-clean quickly) | CI Gate Inventory | If extensive untyped code, exemption is the right call. Mitigation: run `mypy --strict` on forges as a probe during plan-phase. [ASSUMED] |
| A7 | Three identical `ast_lint_no_print.py` files is preferable to a shared one across repos | Print Lint Scope | More files to keep in sync. Mitigation: extract to a `thermocline.tools` shared module if drift emerges; not v0.1 critical. [ASSUMED — recommendation] |
| A8 | Click decorator stacking with `@audit_cli_invocation` between `@click.command` and `@click.pass_context` works correctly | cli_invocation Audit Retrofit | If broken, audit entries don't write. Mitigation: integration test verifies; `functools.wraps` + careful ordering is documented click pattern. [VERIFIED via click docs convention; UNTESTED in this codebase] |
| A9 | `Sensitive[T]` runtime guard in `AuditLog.append` is desirable (defense in depth on top of static typing) | Sensitive[T] Sweep | If overaggressive, legitimate payloads with `Sensitive` value get rejected. Mitigation: the guard's job is exactly to reject these; if a legitimate payload needs `Sensitive`, the design is wrong. [ASSUMED — recommendation] |
| A10 | The tag-v0.1.0.sh script's `find sibling repos via $THERMOCLINE_SUITE_ROOT` approach works for the eventual GitHub Actions release runner (if any) | Release Script | If CI tags, needs different layout. Mitigation: D-06 says manual invocation only; no CI tagging. [VERIFIED via D-06] |
| A11 | The "ChecklistItem(" grep gate from Phase 3 (returns 16, not 13) is a known artifact of `class ChecklistItem(NamedTuple):` syntax; Plan 04-01's `at_coverage.py` doesn't repeat this mistake | Code Examples | If Plan 04-01 introduces a similar grep gate, same false-positive. Mitigation: Phase 3 SUMMARY line 432-438 documents the fix (functional NamedTuple form). [VERIFIED] |
| A12 | "PIFORGE_READY port=..." print line is contract with `subprocess_forge` fixture | Print Lint Scope | If lint forbids, fixtures break. Mitigation: explicit allow-list entry. [VERIFIED] |

## Open Questions

1. **Fixture naming reconciliation (AT-A4, AT-A6, AT-C5).**
   - What we know: filenames don't match spec surfaces.
   - What's unclear: whether Phase 1-2 fixtures used different surface mappings than current spec.
   - Recommendation: Plan 04-01 first task is fixture audit. If misnamed, rename in a single commit with MANIFEST update; document in v0.3.1 CHANGELOG.

2. **`mypy --strict` on seamount forges (CONFLICT-04).**
   - What we know: forges have no `[tool.mypy]` section; `Verifier.verify` returns `None` in pi-forge envelope.py.
   - What's unclear: whether the forges will pass strict cleanly.
   - Recommendation: plan-phase task includes a probe — `cd seamount/pi-forge && mypy --strict server.py envelope.py pi_forge/`. If <10 errors, fix in Plan 04-01. If many, document exemption.

3. **`photophore audit archive` and `photophore audit verify` commands.**
   - What we know: ops.md plan references both.
   - What's unclear: whether they currently exist in `audit_cmds.py`.
   - Recommendation: verify before plan-phase. If absent, surface as Plan 04-02 implementation gap OR scope reduction in ops.md.

4. **`docs/adr/index.md` content beyond a bulleted list.**
   - What we know: D-03 says "one-line list of ADRs".
   - What's unclear: whether to include status (Accepted/Rejected) inline.
   - Recommendation: include `[ADR-XXXX](file) — Status, Date` per line. Status will be "Accepted" for all 7.

5. **CHANGELOG entry shape for thermocline (two entries: v0.3.1 + v0.1.0).**
   - What we know: thermocline already has `## v0.3.1 (in progress...)` heading; need to dateit. Plus add `## [0.1.0] - YYYY-MM-DD`.
   - What's unclear: ordering. Newest-on-top per Keep-a-Changelog → 0.3.1 (most recent spec) → 0.1.0 (suite milestone) → existing entries.
   - Recommendation: `## [0.3.1] - 2026-MM-DD` (spec patches), `## [0.1.0] - 2026-MM-DD` (suite milestone — same date is acceptable), then existing content.

6. **Should Plan 04-02 also bump pyproject.toml package versions?**
   - What we know: `thermocline` package is `0.3.1`, `photophore` is `0.3.1`, forges are `0.1.0`.
   - What's unclear: whether v0.1.0 git tag should align with `photophore` 0.3.1 → 0.1.0 (downgrade!) or stay decoupled.
   - Recommendation: KEEP package versions independent of suite milestone tag. The v0.1.0 git tag is a *coordination point*, not a package release. Document in each CHANGELOG.

7. **What does `dispatch_signature.policy_hash` carry in the audit payload?**
   - What we know: `_DispatchSignature.policy_hash: str | None = None` in `envelope.py` line 128.
   - What's unclear: whether Phase 3 dispatch coordinator populates it.
   - Recommendation: not Phase 4 scope; flag for v0.2 if AT-* tests can't assert hashing.


## Sources

### Primary (HIGH confidence)

- `/Users/dom/Projects/dom/thermocline/README.md` lines 495-555 — Thermocline §"Attack Surfaces and Mitigations" AT-C1..C6 normative text. [VERIFIED via Read]
- `/Users/dom/Projects/dom/photophore/README.md` lines 459-558 — Photophore AT-A1..A6 normative text. [VERIFIED via Read]
- `/Users/dom/Projects/dom/seamount/README.md` lines 302-330 — Seamount AT-E1..E5 normative text. [VERIFIED via Read]
- `/Users/dom/Projects/dom/thermocline/.planning/phases/03-photophore-dispatch-seamount-upgrade-the-integration-phase/03-03-SUMMARY.md` — SP-3.3-01..03 surfaced as coordinator changes; D-02 reclassifies as spec patches.
- `/Users/dom/Projects/dom/photophore/python/src/photophore/core.py` line 87 — `AuditEventType.CLI_INVOKED = "cli.invoked"` pre-shipped slot. [VERIFIED]
- `/Users/dom/Projects/dom/photophore/python/src/photophore/cli/__init__.py` — click group + sub-command structure. [VERIFIED]
- `/Users/dom/Projects/dom/photophore/python/src/photophore/cli/dispatch_cmds.py` lines 89-96 — current error message shape. [VERIFIED]
- `/Users/dom/Projects/dom/photophore/python/src/photophore/dispatch/_errors.py` — `DispatchSubcode` enum + retryable set. [VERIFIED]
- `/Users/dom/Projects/dom/thermocline/thermocline/python/src/thermocline/sensitive.py` — `Sensitive[T]` wrapper implementation. [VERIFIED]
- `/Users/dom/Projects/dom/thermocline/thermocline/python/src/thermocline/envelope.py` — content fields needing `Sensitive[T]` audit. [VERIFIED]
- `/Users/dom/Projects/dom/photophore/python/tests/test_audit_chain_property.py`, `test_classifier_default_property.py`, `test_shadow_uniqueness_property.py`, `/Users/dom/Projects/dom/thermocline/thermocline/python/tests/test_canonical_properties.py` — four existing CONF-03 property tests. [VERIFIED current `max_examples` values]
- `/Users/dom/Projects/dom/photophore/.github/workflows/ci.yml`, `/Users/dom/Projects/dom/seamount/.github/workflows/ci.yml` — existing CI shape; thermocline has none. [VERIFIED]
- `/Users/dom/Projects/dom/photophore/tools/ast_lint_network_isolation.py` — Phase 3 AST lint pattern, mirrored for `print(` lint. [VERIFIED]
- `/Users/dom/Projects/dom/thermocline/thermocline/python/src/thermocline/scripts/check_no_json_dumps.py` — Phase 1 AST lint pattern, mirrored. [VERIFIED]
- `/Users/dom/Projects/dom/thermocline/thermocline/conformance/MANIFEST.yaml` — fixture index; backfill needed. [VERIFIED]
- `/Users/dom/Projects/dom/thermocline/thermocline/conformance/invalid/` — fixture directory listing (AT-A1, A2, A4, A5; AT-C1..C6). [VERIFIED]
- `/Users/dom/Projects/dom/thermocline/.planning/research/PITFALLS.md` lines 197-213 — "Looks Done But Isn't" checklist. [VERIFIED]
- `/Users/dom/Projects/dom/photophore/python/pyproject.toml`, `/Users/dom/Projects/dom/thermocline/thermocline/python/pyproject.toml`, `/Users/dom/Projects/dom/seamount/pi-forge/pyproject.toml`, `/Users/dom/Projects/dom/seamount/describe-forge/pyproject.toml` — dependency manifests and mypy config status. [VERIFIED]
- `/Users/dom/Projects/dom/thermocline/thermocline/CHANGELOG.md` — existing v0.3.1 in-progress entry; extending in Plan 04-02. [VERIFIED]

### Secondary (MEDIUM confidence)

- Keep a Changelog v1.1.0 (https://keepachangelog.com/en/1.1.0/) — D-06 ships lite variant. [CITED: D-06]
- MADR (https://adr.github.io/madr/) — D-03 ships one-page variant. [CITED: D-03]
- RFC 8785 (https://www.rfc-editor.org/rfc/rfc8785) — canonical JSON; ADR-0003 source. [CITED]
- BLAKE3 spec (https://github.com/BLAKE3-team/BLAKE3) — chain hash + CLI arg sanitization choice. [CITED]
- click documentation — decorator stacking pattern for `@audit_cli_invocation`. [ASSUMED via convention]

### Tertiary (LOW confidence — none in this research)

No claims rely solely on unverified web search.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified in pyproject.toml files for all three repos.
- AT-* surface failure modes: HIGH — read directly from normative spec READMEs.
- File paths: HIGH — verified with `ls`/`find`/`Read` against actual filesystem.
- AT-A1 wire-in status: HIGH — Phase 3 SUMMARY documents `phase_wired: 3`.
- Property test current state: HIGH — `max_examples` values verified line-by-line.
- CI gate current state: HIGH — workflow YAML files read directly.
- Fixture naming mismatches: MEDIUM — observed, but exact resolution (rename vs add) needs Phase 1-2 LEARNINGS context.
- `cli_invocation` decorator pattern: MEDIUM — established click convention, but stacking with custom decorators in this codebase is untested.
- `mypy --strict` on forges: MEDIUM — assumption A6 is unverified; quick probe in plan-phase will resolve.
- Release script BSD/GNU portability: MEDIUM — design follows POSIX patterns but untested on macos-latest CI.
- ADR template (MADR-lite): HIGH — established documentation pattern.
- SP-3.3-01..03 wording: HIGH — paragraphs verbatim from D-02.
- 30-minute quickstart timing: MEDIUM — derived from spec installation + dispatch ops, untested in a clean clone.
- `Sensitive[T]` sweep recommendations: HIGH — each field audited against current code.
- `print(` lint scope: HIGH — full grep scan in research; allow-list explicit.

**Research date:** 2026-05-11
**Valid until:** 2026-06-10 (30 days; codebase is stable post-Phase-3; no major drift expected)

## RESEARCH COMPLETE

**Summary of findings:**
- **17 AT-* surfaces** mapped with failure modes, test paths, fixture status. **AT-A1 wired (Phase 3); 16 new tests in Phase 4.** Existing fixtures cover AT-A1, A2, A4, A5 + AT-C1..C6. New fixtures needed: AT-A3, AT-A6, AT-E1..E5.
- **Fixture naming conflicts** between filenames and spec surface IDs (AT-A4 file is misnamed; AT-C5 file is misnamed) — flagged for Plan 04-01 reconciliation; Open Question 1.
- **4 existing property tests** verified at `max_examples` levels: classifier=100, audit=100×2, canonical=200/100/100, shadow=100. Plan: bump to ≥200 each; widen audit chain strategy range to avoid pair saturation.
- **1 new dispatch-integrated property test** at `photophore/python/tests/integration/test_property_dispatch_shadow_uniqueness.py` — reuses Phase 3 `subprocess_forge` fixture.
- **`AuditEventType.CLI_INVOKED` enum slot already pre-shipped** in `core.py` line 87. Plan 04-01 wires `@audit_cli_invocation` decorator + `append_cli_invocation` helper.
- **CI gates: thermocline has NO workflow file** — Plan 04-01 creates one. photophore + seamount workflows extend with new gates (`at_coverage.py`, `property_coverage.py`, `ast_lint_no_print.py`).
- **`print(` lint scope verified** — 5 `print()` call-sites in non-test code; all in forge entry points or lint tools; all allow-listed. Lint is green on first run.
- **`Sensitive[T]` sweep**: `ContentBlock.content` already wrapped. Recommended NEW: runtime guard in `AuditLog.append` rejects `Sensitive` values in payload (defense in depth).
- **`SensitiveFilter` logging filter**: NEW module `photophore/python/src/photophore/logging.py`. Photophore currently has no logger — filter is forward-looking.
- **7 ADRs**: 5 in thermocline, 2 in photophore, 0 in seamount (cross-refs only). Source material verified for each.
- **30-minute quickstart**: command sequence drafted; macOS Keychain first-prompt gotchas documented.
- **Release script `tag-v0.1.0.sh`**: bash structure with `--dry-run`, BSD-portable, reads `$THERMOCLINE_SUITE_ROOT`.
- **CHANGELOGs**: thermocline already has `## v0.3.1 (in progress)`; extends with dated `## [0.1.0]`. photophore + seamount get new files.
- **Three CONTEXT.md conflicts flagged** (CONFLICT-01 path discrepancy, CONFLICT-02 spec-patch reclassification, CONFLICT-03 forge print scope) for planner to address.
- **12 assumptions logged** for downstream verification; **7 open questions** for plan-phase resolution.

**Files created:** `.planning/phases/04-hardening-conformance-and-v0-1-release/04-RESEARCH.md`

**Ready for planning:** Yes. Plan 04-01 has clear bounded scope (16 negative tests + 1 property + 5 tools + 3 CI workflow edits + CLI-06/07 retrofits + `Sensitive` sweep). Plan 04-02 has clear scope (7 ADRs + 7 docs files + SP-3.3-01..03 amendments + release script + 3 CHANGELOGs). Open Questions 1-3 (fixture renaming, mypy strict on forges, audit archive existence) need ~30 min of pre-plan verification; the rest is execution.

