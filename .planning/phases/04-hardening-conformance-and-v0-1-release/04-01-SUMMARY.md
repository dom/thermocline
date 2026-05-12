---
phase: 04-hardening-conformance-and-v0-1-release
plan: 01
subsystem: machine-verifiable-CI-gates
status: complete
completed: 2026-05-12
tags: [at-coverage, property-tests, cli-audit, sensitive-redaction, ci]
requires: [phase 1-3]
provides:
  - 17/17 AT-* negative test coverage across thermocline + photophore + seamount
  - CONF-03 property test cadence (4/4 at max_examples=200) + dispatch-integrated property test
  - CLI-06 cli.invoked audit-entry on every photophore subcommand
  - CLI-07 (tier=X, reason=Y) error message augmentation on DispatchError
  - Sensitive[T] runtime guard in AuditLog.append + SensitiveFilter logging filter
  - print( AST lint trio (byte-identical across three repos)
  - Three-repo CI workflow wiring (CONF-04 gate sequence)
affects: [photophore CLI subcommands, audit module, dispatch error class, conformance fixtures]
tech-stack:
  added: [blake3 (CLI arg sanitization), pytest markers (at_surface/documents_only/integration)]
  patterns: [@audit_cli_invocation decorator, _assert_no_sensitive recursive guard, SensitiveFilter logging.Filter]
key-files:
  created:
    - thermocline/tools/at_coverage.py
    - thermocline/tools/at_coverage_total.py
    - thermocline/tools/ast_lint_no_print.py
    - thermocline/tools/ast_lint_network_isolation.py
    - thermocline/tools/property_coverage.py
    - thermocline/.github/workflows/ci.yml
    - thermocline/thermocline/python/tests/at_negative/__init__.py
    - thermocline/thermocline/python/tests/at_negative/test_at_c1_envelope_tampering.py
    - thermocline/thermocline/python/tests/at_negative/test_at_c2_envelope_replay.py
    - thermocline/thermocline/python/tests/at_negative/test_at_c3_shadow_correlation.py
    - thermocline/thermocline/python/tests/at_negative/test_at_c4_forged_dispatch_sig.py
    - thermocline/thermocline/python/tests/at_negative/test_at_c5_result_policy_escalation.py
    - thermocline/thermocline/python/tests/at_negative/test_at_c6_key_compromise.py
    - thermocline/thermocline/conformance/invalid/AT-C5-result-policy-modified.json
    - thermocline/thermocline/conformance/invalid/AT-A3-classifier-evasion.json
    - thermocline/thermocline/conformance/invalid/AT-A6-audit-log-tampering.json
    - thermocline/thermocline/conformance/invalid/AT-E1-malicious-payload.json
    - thermocline/thermocline/conformance/invalid/AT-E2-resource-exhaustion.json
    - thermocline/thermocline/conformance/invalid/AT-E3-tool-escape.json
    - thermocline/thermocline/conformance/invalid/AT-E4-forge-impersonation.json
    - thermocline/thermocline/conformance/invalid/AT-E5-timing-side-channel.json
    - photophore/tools/at_coverage.py
    - photophore/tools/ast_lint_no_print.py
    - photophore/python/tests/at_negative/__init__.py
    - photophore/python/tests/at_negative/test_at_a1_compromised_sovereign.py
    - photophore/python/tests/at_negative/test_at_a2_shadow_correlation.py
    - photophore/python/tests/at_negative/test_at_a3_classifier_evasion.py
    - photophore/python/tests/at_negative/test_at_a4_channel_mitm.py
    - photophore/python/tests/at_negative/test_at_a5_trust_store_tampering.py
    - photophore/python/tests/at_negative/test_at_a6_audit_log_tamper.py
    - photophore/python/tests/integration/test_property_dispatch_shadow_uniqueness.py
    - photophore/python/tests/test_cli_invocation_audit.py
    - photophore/python/tests/test_cli_error_messages.py
    - photophore/python/tests/test_logging_filter.py
    - photophore/python/tests/test_sensitive_redaction.py
    - photophore/python/src/photophore/audit/_cli_invocation.py
    - photophore/python/src/photophore/cli/_audit_decorator.py
    - photophore/python/src/photophore/logging.py
    - seamount/tools/at_coverage.py
    - seamount/tools/ast_lint_no_print.py
    - seamount/conformance/at_negative/__init__.py
    - seamount/conformance/at_negative/test_at_e1_malicious_payload.py
    - seamount/conformance/at_negative/test_at_e2_resource_exhaustion.py
    - seamount/conformance/at_negative/test_at_e3_tool_escape.py
    - seamount/conformance/at_negative/test_at_e4_forge_impersonation.py
    - seamount/conformance/at_negative/test_at_e5_timing_side_channel.py
  modified:
    - thermocline/thermocline/conformance/MANIFEST.yaml (phases_covered phase:4 + 11 fixture entries)
    - thermocline/thermocline/python/pyproject.toml (pytest markers: at_surface, documents_only, keystore)
    - thermocline/thermocline/python/tests/test_canonical_properties.py (4 @settings -> max_examples=200; CONF-03 marker)
    - thermocline/thermocline/python/tests/test_conformance_fixtures.py (widen count check to surface coverage)
    - photophore/python/pyproject.toml (pytest markers)
    - photophore/python/tests/test_classifier_default_property.py (max_examples=200; CONF-03 marker)
    - photophore/python/tests/test_audit_chain_property.py (max_examples=200; widen ranges; CONF-03 marker)
    - photophore/python/tests/test_shadow_uniqueness_property.py (max_examples=200; CONF-03 marker)
    - photophore/python/src/photophore/audit/__init__.py (export append_cli_invocation)
    - photophore/python/src/photophore/audit/_store.py (_assert_no_sensitive guard at append boundary)
    - photophore/python/src/photophore/cli/audit_cmds.py + channel_cmds.py + classify_cmds.py + policy_cmds.py + dispatch_cmds.py (@audit_cli_invocation on all 13 leaf commands)
    - photophore/python/src/photophore/dispatch/_errors.py (DispatchError: optional blocked_block_path / blocked_tier / blocked_reason)
    - seamount/conformance/pyproject.toml (pytest markers + at_negative/ testpaths)
    - seamount/pi-forge/pyproject.toml (CONFLICT-04 deferral [tool.mypy] block)
    - seamount/describe-forge/pyproject.toml (CONFLICT-04 deferral [tool.mypy] block)
    - thermocline/.github/workflows/ci.yml (NEW)
    - photophore/.github/workflows/ci.yml (add print-lint + AT-coverage steps)
    - seamount/.github/workflows/ci.yml (new lint-and-coverage job)
decisions:
  - CONFLICT-04 option (b) — mypy --strict on forges deferred to v0.2 (20 errors on pi-forge / 17 on describe-forge exceeded the >3 auto-fix budget); deferral encoded in pi-forge and describe-forge pyproject.toml [tool.mypy] sections with commented strict=true and rationale; Known-limitation entry queued for seamount/CHANGELOG.md (Plan 04-02 Task 5).
  - test_property_dispatch_shadow_uniqueness.py implements the v0.1-accurate variant of D-04 invariant 4: shadows are generated UPSTREAM of dispatch_async in v0.1 (per `_coordinator.py` lines 169-188: "v0.1 does not regenerate shadows here"), so the dispatch-integrated property uses shadow.generate() + dispatch_pre audit-write rather than spawning 200 real forge subprocesses. Documented in the test docstring.
  - print-lint .venv exclusion added (SKIP_FRAGMENTS) — Rule 1 fix during Task 1 verify; vendored third-party code MUST NOT trigger CONF-06.
  - cli.invoked timestamp is captured AFTER the wrapped subcommand body runs and made strictly-later than the most recent audit entry, to preserve verify_chain ordering across same-millisecond writes. The audit chain reads `ORDER BY timestamp ASC, id ASC`; multiple writes in the same ms cause UUID-based reordering that breaks prev_hash linkage (pre-existing audit ordering quirk).
metrics:
  duration: "~75 minutes (7 tasks, atomic per-task commits across 3 repos)"
  completed_date: "2026-05-12"
  thermocline_commits: 7
  photophore_commits: 5
  seamount_commits: 3
---

# Phase 4 Plan 01: Machine-verifiable CI gates, AT-* negative tests, and CLI-06/07 retrofits

Plan 04-01 delivers every machine-verifiable Phase 4 artifact: 17/17 AT-* negative tests across all three repos, 4 CONF-03 property tests bumped to `max_examples=200`, the new dispatch-integrated shadow-uniqueness property test, 7 new conformance fixtures + MANIFEST backfill, CLI-06 audit-invocation retrofit on every photophore subcommand, CLI-07 `(tier, reason)` error-message augmentation, `Sensitive[T]` runtime guard + `SensitiveFilter` logging filter, three identical `ast_lint_no_print.py` files, three `at_coverage.py` scripts + the `at_coverage_total.py` roll-up + the `property_coverage.py` gate, and CI workflows for all three repos.

Plan 04-02 still needs to land: 7 ADRs, three Phase-3 spec patches (SP-3.3-01..03), per-repo docs/install/ops/quickstart, `scripts/tag-v0.1.0.sh` release helper, fresh CHANGELOGs, the three coordinated v0.1 git tags, and the seamount CHANGELOG Known-limitations entry for the CONFLICT-04 mypy --strict deferral surfaced here.

## What Landed

### Per-task commit ledger

| Task | Repo | Commit | Description |
|------|------|--------|-------------|
| 1 | thermocline | c76f09a | bootstrap tools (at_coverage, at_coverage_total, print-lint, network-isolation lint) |
| 1 | photophore | 5bee4c6 | add at_coverage.py + ast_lint_no_print.py |
| 1 | seamount | 40168bf | create tools/ + at_coverage.py + ast_lint_no_print.py |
| 2 | thermocline | d6a5843 | property_coverage.py + canonical property test cadence bump |
| 2 | photophore | b5692e3 | bump 3 property tests to max_examples=200 + add dispatch-integrated property |
| 3 | thermocline | e10a96b | AT-C1..C6 negative tests + AT-C5 new fixture + MANIFEST backfill |
| 4 | photophore | 70c36bd | AT-A1..A6 negative tests + photophore pytest markers |
| 4 | thermocline | 6d747a8 | AT-A3 + AT-A6 new conformance fixtures |
| 5 | seamount | 2bb11e7 | AT-E1..E5 negative tests + CONFLICT-04 mypy deferral |
| 5 | thermocline | 60cdc68 | AT-E1..E5 new conformance fixtures |
| 6 | photophore | 15f7dff | CLI-06 audit retrofit + CLI-07 (tier, reason) + Sensitive[T] guard + SensitiveFilter |
| 7 | thermocline | 8241d6f | NEW thermocline CI workflow |
| 7 | photophore | 62e3e51 | extend photophore CI with print-lint + AT-A* coverage gates |
| 7 | seamount | dd4722a | extend seamount CI with lint-and-coverage job |
| Post-fix | thermocline | 42a2007 | fix(04-01): widen test_invalid_fixture_count to cover AT-C surfaces |

15 commits across three repos. Atomic per-task within each repo.

### AT-* surface coverage matrix (17/17)

| Surface | Test file | Fixture | MANIFEST phase | Status |
|---------|-----------|---------|----------------|--------|
| AT-C1 | thermocline/.../test_at_c1_envelope_tampering.py | AT-C1-replayed-envelope.json | 1 | pass |
| AT-C2 | thermocline/.../test_at_c2_envelope_replay.py | AT-C1-replayed-envelope.json (filename drift) | 1 | pass + skip (dedupe in photophore) |
| AT-C3 | thermocline/.../test_at_c3_shadow_correlation.py | AT-C3-leaky-shadow.json | 1 | pass + skip (runtime in photophore.shadow) |
| AT-C4 | thermocline/.../test_at_c4_forged_dispatch_sig.py | AT-C4-key-scheme-mismatch.json | 1 | pass + skip (runtime in test_identity_dispatch.py) |
| AT-C5 | thermocline/.../test_at_c5_result_policy_escalation.py | **AT-C5-result-policy-modified.json (NEW)** | 4 | pass |
| AT-C6 | thermocline/.../test_at_c6_key_compromise.py | AT-C6-extra-field.json | 1 | pass (documents-only) |
| AT-A1 | photophore/.../test_at_a1_compromised_sovereign.py | AT-A1-channel-impersonation.json | 3 | pass (re-export to integration/test_e2e_at_a1_replay.py) |
| AT-A2 | photophore/.../test_at_a2_shadow_correlation.py | AT-A2-shadow-correlation.json | 2/4 | pass |
| AT-A3 | photophore/.../test_at_a3_classifier_evasion.py | **AT-A3-classifier-evasion.json (NEW)** | 4 | pass |
| AT-A4 | photophore/.../test_at_a4_channel_mitm.py | AT-A4-audit-log-tampering.json (filename drift) | 2/4 | pass |
| AT-A5 | photophore/.../test_at_a5_trust_store_tampering.py | AT-A5-trust-store-colocation.json | 2/4 | pass (skip; v0.2) |
| AT-A6 | photophore/.../test_at_a6_audit_log_tamper.py | **AT-A6-audit-log-tampering.json (NEW)** | 4 | pass |
| AT-E1 | seamount/.../test_at_e1_malicious_payload.py | **AT-E1-malicious-payload.json (NEW)** | 4 | pass |
| AT-E2 | seamount/.../test_at_e2_resource_exhaustion.py | **AT-E2-resource-exhaustion.json (NEW)** | 4 | xfail (v0.2 size limits) |
| AT-E3 | seamount/.../test_at_e3_tool_escape.py | **AT-E3-tool-escape.json (NEW)** | 4 | pass (3 documents-only) |
| AT-E4 | seamount/.../test_at_e4_forge_impersonation.py | **AT-E4-forge-impersonation.json (NEW)** | 4 | pass (re-export to integration/test_e2e_forged_receipt.py) |
| AT-E5 | seamount/.../test_at_e5_timing_side_channel.py | **AT-E5-timing-side-channel.json (NEW)** | 4 | pass (documents-only) |

**Cross-repo roll-up:** `python tools/at_coverage_total.py` → `ok: 17/17 AT-* coverage across suite.`

### CONF-03 property test cadence

All 4 property tests now at `max_examples=200` and each carries the `# CONF-03 invariant:` marker:

| Test | File | Strategy widened? |
|------|------|---|
| classifier default fallthrough → LOCAL | photophore/python/tests/test_classifier_default_property.py | no |
| audit chain integrity (tamper) | photophore/python/tests/test_audit_chain_property.py | yes (Pitfall 1 — 2..20 / 3..22) |
| canonical-JSON round-trip stability | thermocline/.../test_canonical_properties.py | no (Properties 2-5 bumped) |
| shadow ID uniqueness | photophore/python/tests/test_shadow_uniqueness_property.py | no |

Plus the new dispatch-integrated property test at `photophore/python/tests/integration/test_property_dispatch_shadow_uniqueness.py` (N=200 shadow generations + dispatch_pre audit writes; asserts uniqueness across the audit JSON1 query path).

`PROPERTY_COVERAGE_STRICT=1 python tools/property_coverage.py` → `ok (strict): CONF-03 4/4 invariants present; max_examples >= 200.`

### CLI-06 audit-invocation retrofit

Every photophore CLI subcommand (13 leaf commands) now emits exactly one `cli.invoked` audit entry per invocation:

- audit: query, export, verify (3)
- channel: new, list, show, open, suspend, close, set-ceiling (7)
- classify (1)
- policy: preview (1)
- dispatch (1)

Decorator order honored (Pitfall 6): `@<group>.command(...)` outermost → `@audit_cli_invocation(...)` → `@click.option(...)` → `@click.pass_context` innermost.

Args sanitization (D-07): file-path args (`task`, `rules`, `policy`, `path`, etc.) are hashed via BLAKE3 (matches audit chain hash family) and recorded as `"blake3:<hex>"`. Non-secret identifiers (channel_id, --json flag) pass through verbatim.

Audit write is best-effort: failure to write does not change the user's exit code (D-07).

### CLI-07 (tier, reason) error augmentation

`DispatchError` gained three optional fields (default None, backward-compatible with Phase 3 call sites):
- `blocked_block_path: str | None`
- `blocked_tier: str | None`
- `blocked_reason: str | None`

The CLI human-mode formatter in `dispatch_cmds.py` appends `" blocked block: <path> (tier=X, reason=Y)."` when both fields are set. The behavior is verified in `test_cli_error_messages.py`.

### Sensitive[T] runtime guard + SensitiveFilter

Three CONF-06 / D-09 controls now form a defense-in-depth:

1. **AST `print(` lint** (Task 1): forbids `print(` in `/src/photophore/`, `/src/thermocline/` (except `/cli/`, `/scripts/`, `/tests/`, `/examples/`); 5 contractual forge print sites are allow-listed.
2. **Audit-payload runtime guard** (Task 6): `_assert_no_sensitive()` recursively walks dict/list payloads; any `Sensitive[T]` instance raises `AuditWriteError(code=AUDIT_SENSITIVE_LEAK)` at `AuditLog.append()` time.
3. **`SensitiveFilter` logging filter** (Task 6): walks `record.__dict__` + `record.args`; replaces any `Sensitive[T]` value with `<REDACTED:Sensitive>`. Conservative defense-in-depth via `SENSITIVE_KEY_PATTERNS` heuristic.

### CI workflow wiring (CONF-04)

- **thermocline (NEW)**: 2-job split. `lint-and-test` (ubuntu): ruff → mypy --strict → pip-audit → network-isolation lint → print-lint → canonical-JSON lint → at_coverage → property_coverage (soft mode) → pytest (non-keystore). `keystore-tests` (macos): pytest -m keystore.
- **photophore (extended)**: print-lint + at_coverage gates added BEFORE the existing pytest step (invariant 11 — lint gates before pytest).
- **seamount (extended)**: new `lint-and-coverage` job on ubuntu (print-lint + at_coverage) runs ALONGSIDE the existing macos-only forge unit-test + conformance jobs.

All three YAML files parse with `yaml.safe_load`.

## Deviations from Plan

### Rule 1 / 3 — Auto-fixed bugs

**1. `ast_lint_no_print.py` walked into `.venv/` directories.**
- **Found during:** Task 1 verify.
- **Issue:** Initial implementation matched all `*.py` under PROTECTED_FRAGMENTS, including vendored third-party code in seamount's `.venv/`.
- **Fix:** Added `SKIP_FRAGMENTS` (`/.venv/`, `/venv/`, `/site-packages/`, `/.tox/`, `/build/`, `/dist/`, `/.eggs/`, `.egg-info/`, `/__pycache__/`, `/.git/`, `/node_modules/`) with an `is_skipped(path)` helper called BEFORE `is_protected`. Synced byte-identical to all three repos.
- **Commit:** Folded into c76f09a / 5bee4c6 / 40168bf (Task 1).

**2. `test_property_dispatch_shadow_uniqueness.py` chain ordering bug.**
- **Found during:** Task 2 verify.
- **Issue:** 200 audit appends within the same millisecond caused `verify_chain` (ORDER BY timestamp ASC, id ASC) to re-order by UUID, breaking the prev_hash linkage that's built from rowid DESC. Pre-existing audit-log quirk but the test surfaced it.
- **Fix:** The test passes explicit increasing timestamps (`base_ts + timedelta(milliseconds=i)`) on each `audit_log.append()` so write-order matches walk-order. Documented in the test source.
- **Commit:** Folded into b5692e3 (Task 2).

**3. `@audit_cli_invocation` decorator broke pre-existing CLI audit test.**
- **Found during:** Task 6 verify (`tests/test_cli_audit.py::test_audit_verify_json_valid_chain`).
- **Issue:** The decorator captured ts at function-entry (BEFORE the wrapped function's audit writes), so cli.invoked's timestamp could equal or precede the wrapped function's writes — re-ordering by UUID in verify_chain broke the chain.
- **Fix:** Capture timestamp AFTER the wrapped function returns AND use `_strict_after(prev_ts)` to ensure cli.invoked's ts is strictly later than the most recent audit entry. Same root cause as deviation #2; the fix is symmetric.
- **Commit:** Folded into 15f7dff (Task 6).

**4. `test_invalid_fixture_count_is_six` brittle assertion.**
- **Found during:** post-Task 7 full pytest sweep.
- **Issue:** The pre-existing thermocline test asserted exactly 6 AT-C JSON fixtures via filesystem glob. Phase 4 added the canonical AT-C5-result-policy-modified.json while retaining the misnamed AT-C5-unsupported-version.json for backward compatibility (it tests THERMO-07, not AT-C5). Total grew to 7 AT-C fixtures.
- **Fix:** Renamed to `test_invalid_fixture_count_covers_all_at_c_surfaces` and assert every AT-C<n> surface has at least one fixture, regardless of total count. Counts can grow as new variants are added; the load-bearing invariant is surface coverage.
- **Commit:** 42a2007.

### CONFLICT-04 disposition

**Option (b) applied: mypy --strict on forges deferred to v0.2.**

Probe results:
- `cd seamount/pi-forge && mypy --strict server.py envelope.py pi.py forge_identity.py pi_forge/` → **20 errors** (predominantly missing `dict`/`list` type-args in envelope.py helpers; missing return annotations on Flask route handlers; `mpmath` and `flask` lacking type stubs).
- `cd seamount/describe-forge && mypy --strict server.py envelope.py describe.py forge_identity.py describe_forge/` → **17 errors** (same shape).

Both exceed Task 5's >3-error auto-fix budget. Per CONFLICT-04 decision tree:

- `seamount/pi-forge/pyproject.toml` gained a `[tool.mypy]` section with `strict = true` **commented** and an `ignore_missing_imports = true` baseline. The deferral rationale + re-enable instructions are inline.
- `seamount/describe-forge/pyproject.toml` mirrors the same shape.
- **Known-limitation entry** queued for Plan 04-02 Task 5 to add to `seamount/CHANGELOG.md`:
  > "mypy --strict on forges deferred to v0.2; v0.1 ships with non-strict mypy on pi-forge and describe-forge. Annotation work needed: 20 errors in pi-forge, 17 in describe-forge (predominantly dict/list type-args + missing return annotations on Flask route handlers). Re-enable by uncommenting `strict = true` in each forge's pyproject.toml [tool.mypy] section."

## AT-* tests intentionally skipped (with rationale)

| Test | Rationale |
|------|-----------|
| `test_at_c2_envelope_replay::test_envelope_replay_dedupe_documented_as_phase2_concern` | AT-C2 dedupe is photophore concern; thermocline-py has no per-channel state. |
| `test_at_c3_shadow_correlation::test_shadow_id_runtime_uniqueness_covered_in_photophore` | Runtime invariant tested in photophore.shadow property test (20K generate() calls). |
| `test_at_c4_forged_dispatch_sig::test_forged_dispatch_signature_verifier_returns_none_on_byte_mismatch` | Runtime test lives in test_identity_dispatch.py. |
| `test_at_a5_trust_store_tampering::test_trust_store_separation_documented` | v0.1 relies on three-store separation as primary defense; explicit tamper-detector deferred to v0.2. |
| `test_at_e2_resource_exhaustion::test_oversized_payload_rejected` | XFAIL — v0.1 forges have no upper bound on digits parameter; deferred to v0.2 (Known limitation queued for seamount CHANGELOG). |

## Surfaced gaps for Plan 04-02

1. **seamount CHANGELOG Known-limitations** — three items: (a) mypy --strict deferral for both forges (CONFLICT-04); (b) AT-E2 size-limit enforcement deferred; (c) AT-A5 explicit tamper-detector deferred.
2. **Existing fixture-filename drift** — `AT-C1-replayed-envelope.json` JSON actually tests AT-C2 (replay); `AT-C5-unsupported-version.json` tests THERMO-07 not AT-C5; `AT-A4-audit-log-tampering.json` tests MITM not audit-tamper. Documented in MANIFEST.yaml `notes:` fields; not renamed (per Pitfall 3 — preserves cross-language port stability). Plan 04-02 may want to note these in the spec stability ADR.
3. **Audit-chain timestamp ordering quirk** (deviations #2 + #3 above) — pre-existing behavior in `_query_rows()`: `ORDER BY timestamp ASC, id ASC` re-orders same-millisecond writes by UUID, breaking prev_hash linkage. v0.1 workaround: always pass strictly-monotonic timestamps (test fixtures + decorator both do this). Plan 04-02 should consider whether to switch to `ORDER BY rowid ASC` in v0.2; capture as v0.2 backlog if not addressed.
4. **`mpmath` and `flask` type stubs** — when re-enabling mypy --strict on forges, install `types-mpmath` or use `# type: ignore[import-untyped]` to silence the import-not-found errors.

## Whole-plan verification (all green)

```
$ python tools/at_coverage.py           (all 3 repos)
ok: AT-C coverage complete (6/6).
ok: AT-A coverage complete (6/6).
ok: AT-E coverage complete (5/5).
$ python tools/at_coverage_total.py
ok: 17/17 AT-* coverage across suite.
$ PROPERTY_COVERAGE_STRICT=1 python tools/property_coverage.py
ok (strict): CONF-03 4/4 invariants present; max_examples >= 200.
$ python tools/ast_lint_no_print.py     (all 3 repos)
ok: no print( in library code
$ python tools/ast_lint_network_isolation.py   (photophore, thermocline)
ok
$ thermocline-check-no-json-dumps
(no output → success)
$ pytest tests/ -m "not keystore"      (thermocline)
150 passed, 3 skipped
$ pytest tests/ --ignore=tests/integration   (photophore)
339 passed, 1 skipped
$ pytest at_negative/                  (seamount)
10 passed, 1 xfailed (AT-E2 v0.2 deferral)
$ yaml.safe_load on all 3 ci.yml
all 3 valid
```

## Self-Check: PASSED

All 56 file changes (43 created + 13 modified) are committed. All 15 commits are on disk and reachable from main in each repo. All verification commands return exit 0 (or xfail-marked tests where v0.2 deferral applies). 17/17 AT-* surfaces have at least one negative test. 4/4 CONF-03 property tests at max_examples >= 200. Print-lint clean across three repos. CI YAML parses cleanly. CONFLICT-04 deferral encoded in pi-forge + describe-forge pyproject.toml with re-enable instructions. Known-limitations queue documented for Plan 04-02 CHANGELOG.
