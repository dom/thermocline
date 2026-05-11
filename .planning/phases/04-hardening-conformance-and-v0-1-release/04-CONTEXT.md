# Phase 4: Hardening, Conformance, and v0.1 Release - Context

**Gathered:** 2026-05-11
**Status:** Ready for planning
**Mode:** `--auto` (single-pass; recommended option auto-selected for each gray area; see DISCUSSION-LOG.md for trade-off tables)

<domain>
## Phase Boundary

This phase **freezes the v0.1 reference implementation** of the Thermocline suite and ships three coordinated v0.1 git tags. No new behavior lands — only verification, documentation, and release coordination. The output is a clone-to-first-dispatch-in-under-30-minutes experience for a new macOS user, with every forever-decision auditable via ADRs and every threat-model surface exercised by at least one negative test.

What lands:

- **Hypothesis property tests at ≥100 cases each** for the four critical invariants — classifier default fallthrough (`LOCAL`), audit chain integrity (any single-byte tamper invalidates), canonical-JSON round-trip stability, shadow-ID uniqueness across dispatches of identical content. (Three of four already exist from Phases 1-2; this phase consolidates them into a CONF-03 test-set with `max_examples=200` and adds the dispatch-time shadow uniqueness check.)
- **16 new AT-* negative tests** covering Thermocline AT-C1..C6, Photophore AT-A2..A6, Seamount AT-E1..E5 (AT-A1 already wired in Phase 3 — `phase:3` MANIFEST tag, `test_e2e_at_a1_replay.py`). Each test documents which surface it exercises and asserts the failure mode.
- **17/17 AT-* coverage CI gate** (1 inherited + 16 new) — a per-repo `at_coverage.py` script enumerates AT-tagged tests by filename convention and asserts the expected subset count; CI fails the build if any surface has zero coverage.
- **7 ADRs** distributed across the three repos in `docs/adr/`: Python as primary language + Pydantic v2 lock-in (thermocline), single canonical-JSON path + BLAKE3 algo_version (thermocline), trust-store separation + no in-process key material (photophore), no shadow caching (photophore). One ADR-XXXX per decision per repo; README cross-references with relative paths.
- **Three Phase-3 spec patches (SP-3.3-01..03)** authored as Thermocline README amendments: receipt-signature canonicalization invariant (strip `sig` before re-canonicalize for verify), `dispatch_signature` field pre-fill ordering, and `sig`/`bytes_hex` receipt field tolerance. These are wire-level concerns that any non-Python implementation will hit; the cross-impl-spec-patch pattern (THERMO-01 from Phase 1; reaffirmed in Phase 2 LEARNINGS) is the precedent.
- **`Sensitive[T]` audit retrofit** — sweep all content-bearing fields in `thermocline.envelope` and `photophore.audit` payloads to ensure they're wrapped in `Sensitive[T]` (CONF-06).
- **`print(` lint and privacy-aware logging filter** — custom AST lint forbidding `print(` in library code paths (`thermocline.*`, `photophore.*` excluding `cli/`); `logging` filter that drops any record field tagged `sensitive=True`.
- **Ops/install docs in each repo** — `docs/install.md` (keystore prereq + Python toolchain), `docs/ops.md` (chain archival, audit verify, channel ceiling rotation), and a cross-repo `thermocline/docs/quickstart.md` walking clone → first dispatch → audit query → audit export in under 30 minutes on macOS. README cross-references.
- **`scripts/tag-v0.1.0.sh` release helper** in `thermocline/scripts/` — verifies all three working trees clean, runs the full test suite in each, asserts CI green, then tags `v0.1.0` in each repo on the same date with a Keep-a-Changelog-lite CHANGELOG entry ("Added / Implemented / Deferred / Known limitations").
- **CI gates wired into thermocline's `.github/workflows/ci.yml`** (currently only photophore + seamount have CI). Final CONF-04 gate list: `ruff check`, `mypy --strict`, `pip-audit`, AST network-isolation lint, AST `print(` lint, `at_coverage.py`, `pytest`, `forge_conformance` (seamount only).
- **CLI-06 retrofit** — every `photophore` subcommand emits a `cli_invocation` kind audit entry with `(subcommand, args_sanitized, outcome, exit_code, ts)`; args containing file paths to envelopes/policies are hashed, not stored verbatim.
- **CLI-07 retrofit** — dispatch and classify error messages that block due to classification/policy include the relevant `(tier, reason)` so users can diagnose blocks (e.g., `error: dispatch blocked at step 2: block 'context[0]' classified (tier=LOCAL, reason=classifier:credential_pattern); ...`).

What does NOT land (deferred):

- **Apple Silicon Secure Enclave hardware-anchored keystore entries** — `python-keyring` macOS Keychain entries are software-backed/encrypted-at-rest by default, which satisfies the v0.1 threat model (key material never copied out of the keystore). Full Secure Enclave coverage requires Apple Silicon + a developer signing identity and is deferred to v0.2; documented as a known limitation in `thermocline/docs/install.md`.
- **Property tests for additional invariants beyond the four CONF-03 lists** — Phase 4 caps at the four required; further property tests are nice-to-have for v0.2.
- **Linux first-class / Windows first-class ops docs** — macOS is first-class per PROJECT.md constraints; Linux/Windows get a "may require additional setup" section in `docs/install.md` only.
- **Third-party forge conformance certification** — `forge_conformance` runs against `pi-forge` and `describe-forge` in CI; running against external impls is a post-v0.1 milestone.
- **Spec amendments beyond SP-3.3-01..03** — any new spec ambiguities surfaced during Phase 4 are captured and triaged but not auto-published; reflected in 04-LEARNINGS if found.

</domain>

<decisions>
## Implementation Decisions

### AT-* negative test placement and coverage enforcement (CONF-02)

- **D-01 (Per-repo split by AT-letter; filename-convention coverage counter):**

  The 17 AT-* surfaces split cleanly by which spec defines them: **Thermocline AT-C1..C6 → `thermocline/python/tests/at_negative/` (6 tests)**, **Photophore AT-A1..A6 → `photophore/python/tests/at_negative/` (6 tests; AT-A1 already exists as `photophore/python/tests/integration/test_e2e_at_a1_replay.py` — link/symlink or re-tag, do not duplicate)**, **Seamount AT-E1..E5 → `seamount/conformance/at_negative/` (5 tests)**.

  Filename convention: `test_at_<letter><number>_<one_word_failure>.py` (e.g., `test_at_c1_unknown_key_scheme.py`, `test_at_e3_receipt_signature_forged.py`). Each file's docstring opens with the AT-* surface ID and a one-line statement of the failure mode it asserts (`AT-C3: tier-0 content present in outgoing envelope → dispatch raises ContentTierEscape`).

  Coverage enforcement: each repo ships `tools/at_coverage.py` that globs `tests/at_negative/test_at_*.py`, extracts the AT-IDs from filenames, and asserts the expected set is present for that repo (`AT_C = {"AT-C1", ..., "AT-C6"}`). CI runs `python tools/at_coverage.py` BEFORE `pytest` so the failure surfaces as "missing AT-A4 coverage" not "test failed". A roll-up `at_coverage_total.py` in `thermocline/tools/` sums all three repo subsets and asserts `len(covered) == 17`.

  Rationale: each spec's negative tests live with the spec that defines them — readers of `photophore/README.md` find Photophore's AT-A* tests in `photophore/python/tests/at_negative/`, not buried in a sibling repo's harness. Filename convention is the simplest counter (no marker decorator, no manifest YAML), and it survives test refactors. The cross-repo roll-up exists so "17/17 covered" remains a single CI assertion at suite-level.

### Phase-3 cross-impl spec patches (SP-3.3-01, SP-3.3-02, SP-3.3-03)

- **D-02 (Ship all three as Thermocline README amendments, following THERMO-01 precedent):**

  All three concerns are wire-level: any non-Python implementation reading the Thermocline spec would arrive at a working impl only by reverse-engineering our coordinator. Amend the spec.

  - **SP-3.3-01 — Receipt-signature canonicalization invariant**: Thermocline README §"Receipt Signatures" gets a new normative paragraph: *"When verifying a `receipt_signature`, implementations MUST canonicalize the envelope with the `receipt_signature.sig` field set to the empty string `""`, NOT removed. The signer SHALL produce the signature over this same canonicalization shape. Removing the field would cause map-key set divergence between signer and verifier."* Plus a one-line example showing the before/after JSON.
  - **SP-3.3-02 — `dispatch_signature` field pre-fill ordering**: Thermocline README §"Dispatch Signatures" gets: *"Implementations MUST populate all non-`sig` fields of `dispatch_signature` (`signer`, `key_scheme`, `ts`, `algo`) BEFORE canonicalization and signing. The `sig` field SHALL be the empty string `""` during canonicalization. Failure to pre-fill any field will produce a signature that the verifier cannot reproduce."*
  - **SP-3.3-03 — Receipt field tolerance**: Thermocline README §"Receipt Signatures" gets: *"Verifiers SHOULD accept `receipt_signature.sig` as either a hex-encoded string (preferred) or a `bytes_hex` field carrying the same value. Implementations writing receipts MUST emit `sig`; reading them MUST accept both for backward compatibility with pre-0.3.1 drafts."* `thermocline-py` continues to emit `sig` per the preferred path.

  Implementation: a single commit in `thermocline/` titled `spec(0.3.1): clarify signature canonicalization invariants (SP-3.3-01..03)`; CHANGELOG entry under `## [0.3.1]`; `thermocline-py` bumps SUPPORTED_VERSIONS to include `"0.3.1"` (THERMO-07 already lists this). Plan 04-02 holds this commit since it lands alongside ADRs.

  Rationale: Phase 2 LEARNINGS noted THERMO-01 set the precedent — surface impl-driven spec drift as in-place patches at the draft version. These three are exactly that shape. Leaving them coordinator-internal would force every subsequent impl to discover them the hard way (the cross-impl drift the suite is supposed to prevent).

### ADR scope, location, and cross-linking (CONF-05)

- **D-03 (7 ADRs split across 3 repos in `docs/adr/`; README cross-refs; no symlinks):**

  CONF-05 lists seven forever-decisions. Each lands in the repo where the decision binds:

  - `thermocline/docs/adr/ADR-0001-python-3-11-as-primary-language.md`
  - `thermocline/docs/adr/ADR-0002-pydantic-v2-lock-in.md`
  - `thermocline/docs/adr/ADR-0003-single-canonical-json-path.md`
  - `thermocline/docs/adr/ADR-0004-blake3-with-algo-version.md`
  - `photophore/docs/adr/ADR-0001-trust-store-separation-from-audit-log.md`
  - `photophore/docs/adr/ADR-0002-no-shadow-caching.md`
  - `thermocline/docs/adr/ADR-0005-no-in-process-key-material.md` (lives with the IdentityProvider Protocol that defines it; photophore's README cross-references)

  Each ADR is **one page max** in MADR-lite format: Context (2-3 sentences) · Decision (1 sentence) · Consequences (2-3 bullets) · Status (Accepted, dated). README of each repo gets a new §"Architecture Decision Records" linking to its own `docs/adr/index.md` (a one-line list of ADRs). Cross-repo references use relative paths from the originating repo (e.g., from `photophore/README.md`: `[ADR-0005: No In-Process Key Material](../thermocline/docs/adr/ADR-0005-no-in-process-key-material.md)`). **No symlinks** (Windows users; git submodule complications); the relative path works because all three repos live as siblings under `~/Projects/dom/` for the dev environment, and on GitHub the relative repo paths resolve via the user's repo namespace.

  Rationale: each repo tells its own story for a reader landing on its README; ADRs aren't duplicated; relative paths give us cross-repo discoverability without symlink fragility.

### Property test cadence and scope (CONF-03)

- **D-04 (Reuse existing 4 property tests with `max_examples=200`; add 1 dispatch-time shadow-uniqueness property):**

  The four CONF-03 invariants and their current homes:

  1. **Classifier default fallthrough → `LOCAL`** — `photophore/python/tests/test_classifier_default_property.py` (Phase 2). Currently at `max_examples=100`; bump to 200.
  2. **Audit chain integrity (single-byte tamper invalidates)** — `photophore/python/tests/test_audit_chain_property.py` (Phase 2). Bump to 200.
  3. **Canonical-JSON round-trip stability** — `thermocline/thermocline/python/tests/test_canonical_properties.py` (Phase 1). Bump to 200.
  4. **Shadow ID uniqueness across dispatches of identical content** — `photophore/python/tests/test_shadow_uniqueness_property.py` (Phase 2; single-dispatch scope). Phase 4 adds a **dispatch-time** property to `photophore/python/tests/integration/test_property_dispatch_shadow_uniqueness.py`: same source `task` envelope, dispatched N times through `dispatch.dispatch_async()` against a mock forge, asserts all N shadow IDs distinct (`secrets.token_hex` collision probability is negligible but the assertion is the proof). At 200 cases this exercises the full coordinator path.

  All four property test files get a top-of-file comment: `# CONF-03 invariant: <name>` so the `at_coverage.py` analog `tools/property_coverage.py` can enumerate them and assert 4/4. CI fails if any of the four is missing or below `max_examples=200`.

  Rationale: CONF-03 says "≥100 cases each"; we choose 200 as the v0.1 cadence for headroom without making CI sluggish (Hypothesis at 200 cases on the existing four properties is well under one minute on the runner per Phase 2 LEARNINGS). Existing tests satisfy the requirement; only the dispatch-integrated shadow uniqueness property is new.

### Ops/install documentation surface (CONF-07)

- **D-05 (`docs/install.md` + `docs/ops.md` per repo + `thermocline/docs/quickstart.md` for cross-repo flow; macOS first-class):**

  Per-repo `docs/` directory created in each:

  - `thermocline/docs/install.md` — Python 3.11+, uv-managed venv, `pip install -e thermocline/python`, keystore prerequisites (macOS Keychain — works out of the box; Linux libsecret + D-Bus session; Windows Credential Manager). Documents Apple Silicon Secure Enclave as a v0.2 known limitation.
  - `thermocline/docs/ops.md` — Empty (no ops surface in the library).
  - `thermocline/docs/quickstart.md` — **The CONF-07 30-minute walkthrough** because it crosses all three repos. Sections: Clone all three repos (or use the submodule helper) → `pi-forge init` + `pi-forge serve` → `photophore channel new --fetch-pubkey-from http://localhost:5000` → `photophore dispatch --channel <id> --task examples/...` → `photophore audit query --channel <id>` → `photophore audit export > audit.jsonl`. Each step shows expected output. Timed: target 25 minutes on a clean macOS box with Python 3.11 already installed.
  - `photophore/docs/install.md` — depends on `thermocline-py`; `pip install -e ../thermocline/thermocline/python && pip install -e .`; keystore prerequisites.
  - `photophore/docs/ops.md` — chain archival (`photophore audit archive --reason "..."` — semantics: closes current chain, opens new chain with a chain-link record; **archive remains forever**), audit verify, channel ceiling rotation, channel close + close-reason recording.
  - `seamount/pi-forge/docs/install.md` and `seamount/describe-forge/docs/install.md` — per-forge keystore service namespace + `init` subcommand walkthroughs.
  - `seamount/conformance/docs/install.md` — running the conformance harness against an arbitrary forge URL.

  Each README gains a §"Documentation" section linking to its own `docs/` files. macOS is first-class throughout; Linux gets a "tested but not gated in CI" note (CI runs ubuntu-latest for non-keystore-dependent tests + macos-latest for keystore-dependent tests per the existing photophore CI workflow); Windows is documented best-effort.

  Rationale: README is for discovery; `docs/` is for depth. The 30-minute walkthrough is 1500+ words of step-by-step and doesn't belong in a top-level README. Per-repo `docs/install.md` keeps each repo's installation story self-contained for users who pip-install just one.

### Release coordination and CHANGELOG format (CONF-08)

- **D-06 (`scripts/tag-v0.1.0.sh` helper; same-day atomic tagging; Keep-a-Changelog-lite per repo):**

  A new `thermocline/scripts/tag-v0.1.0.sh` (the planning hub owns the helper) — bash script that:

  1. Reads sibling repo paths from `THERMOCLINE_SUITE_ROOT` env var (default: `$HOME/Projects/dom`).
  2. For each of `thermocline`, `photophore`, `seamount`: asserts `git status --porcelain` empty, asserts the current branch is `main`, asserts `git log -1` SHA matches the remote `origin/main`.
  3. For each: runs the repo's test suite (`pytest`); aborts on any failure.
  4. For each: opens that repo's `CHANGELOG.md` and asserts a `## [0.1.0] - YYYY-MM-DD` heading exists (date = today). The author writes these manually before invoking the script.
  5. For each: `git tag -a v0.1.0 -m "v0.1.0 — coordinated with thermocline v0.1.0 + photophore v0.1.0 + seamount v0.1.0"`.
  6. Prints a summary and reminds the operator to `git push --tags` in each repo (not automated — explicit human act per the trust-is-never-automated principle).

  CHANGELOG format per repo (Keep-a-Changelog-lite — no Unreleased section for v0.1):

  ```markdown
  # Changelog

  ## [0.1.0] - 2026-MM-DD

  ### Added
  - [Feature 1]
  - [Feature 2]

  ### Implemented
  - [Requirement ID → behavior]

  ### Deferred to subsequent milestones
  - [Feature, with milestone target — e.g., "job envelopes (v0.2)"]

  ### Known limitations
  - [Limitation, with workaround if any — e.g., "Apple Silicon Secure Enclave hardware-anchored entries are deferred to v0.2; default Keychain entries are software-backed but encrypted-at-rest"]
  ```

  Each repo's CHANGELOG is independent; the tag message records the coordination. `thermocline@5c0d87c` (cirdan→thermocline patch, pre-Phase-1) gets noted in the Thermocline CHANGELOG under §"Implemented".

  Rationale: explicit script makes the release procedure reproducible AND auditable (a privacy primitive suite that can't reproduce its own release would be embarrassing). Keep-a-Changelog-lite is the lightest format that still gives users what they need; "Deferred" + "Known limitations" sections honor the suite's "honest about what's not done" ethos and satisfy CONF-08's "implemented vs. what's deferred" wording.

### CLI-06 retrofit (every CLI subcommand emits an audit entry)

- **D-07 (Literal — every subcommand; new `cli_invocation` audit-entry kind; args sanitized):**

  Plan 04-01 adds a new audit-entry kind `cli_invocation` with payload `{subcommand: str, args: dict[str, str], outcome: "success" | "failure", exit_code: int, ts: ISO8601}`. The audit-entry kind extends the existing kinds (`channel_*`, `dispatch_pre`, `dispatch_post`, etc.) — additive, schema-extending change, no migration since the audit log is append-only and old kinds keep their meaning.

  Args sanitization:

  - File-path args (`--task path.json`, `--rules path.yaml`) → record `args["task"] = "sha256:<hex>"` of the file's contents at invocation time. The hash provides correlation across audit entries (same envelope → same dispatch chain) without retaining content.
  - Channel IDs, node IDs, envelope IDs → recorded verbatim (already non-secret identifiers).
  - `--json` / `--format` / `--ceiling` / boolean flags → recorded verbatim.
  - **Never recorded**: anything that could carry inline envelope content; `--key-material` (no such flag exists; this is a forward-looking guard).

  Every subcommand wraps in a try/finally:

  ```python
  ts_start = utcnow()
  outcome, exit_code = "success", 0
  try:
      result = subcommand_logic(...)
  except SystemExit as e:
      outcome, exit_code = "failure", e.code
      raise
  finally:
      audit.append_cli_invocation(
          subcommand=name,
          args=sanitize_args(click_ctx.params),
          outcome=outcome,
          exit_code=exit_code,
          ts=ts_start,
      )
  ```

  Implementation lives as a decorator (`@audit_cli_invocation`) on the `photophore.cli` group so all subcommands get wrapped uniformly. Read-only subcommands (`channel list`, `audit query`, `classify`, `policy preview`) also log — the audit entries are small (~200 bytes serialized) and the proof property of the audit log holds without exception: every CLI invocation is recorded.

  Rationale: spec text is literal. Inflation cost is bounded (a busy CI run has hundreds of CLI invocations, not millions). The audit log is the proof; selective recording would be exactly the kind of trust hole the suite exists to prevent. Args sanitization closes the obvious leak vector.

### CLI-07 retrofit (classification/policy error messages include `(tier, reason)`)

- **D-08 (Append `(tier=X, reason=Y)` to error messages from `dispatch`, `classify`, `policy preview`):**

  Three error paths get retrofitted:

  - `photophore dispatch` `DispatchError.POLICY_VIOLATED` → message becomes: `dispatch blocked at step 9: result violates authored policy. blocked block: context[0] (tier=LOCAL, reason=classifier:credential_pattern). retryable: false. audit entry: <hash>`.
  - `photophore classify <path>` already emits `(tier, reason)` per block (Phase 2 CLI-04) — Phase 4 ensures the error path (e.g., malformed rules config) also surfaces the failing rule's reason.
  - `photophore policy preview` errors when authoring would block dispatch → message includes the offending block's `(tier, reason)` so the user sees what to tag differently.

  Plan 04-01 adds these as string-formatting tweaks; no API change. Tested via `pytest` snapshot tests on the CLI error output.

  Rationale: small, mechanical retrofit; spec text is "every CLI error message that involves classification or policy" — three subcommands match that filter.

### `Sensitive[T]` audit retrofit + `print(` lint + privacy-aware logger (CONF-06)

- **D-09 (Sweep + lint + filter implementation):**

  1. **`Sensitive[T]` audit retrofit**: grep the codebase for envelope content fields (`content`, `text`, `bytes`, `payload`, `inline`, `abstraction`) in `thermocline.envelope`, `photophore.audit`, `photophore.shadow`. Each that carries user data wraps in `Sensitive[T]` (Phase 1 IDENT-04 / D-03 introduced `Sensitive`). Test: `__repr__` of a populated envelope must not include any content bytes — a CI test enumerates all `Sensitive`-tagged fields and asserts redacted-rendering.
  2. **`print(` lint**: new `thermocline/tools/ast_lint_no_print.py` (mirrors the network-isolation AST lint pattern from Phase 3). Rejects `print(` in all `*.py` files under `thermocline/python/src/`, `photophore/python/src/`, and `seamount/{pi-forge,describe-forge}/` excluding `cli/` (CLI subcommands use `click.echo` instead, which the lint also enforces). Test files (`tests/`) and example files (`examples/`) are exempt. Wired into each repo's CI before `pytest`.
  3. **Privacy-aware logging filter**: `photophore/python/src/photophore/logging.py` ships `SensitiveFilter` (a `logging.Filter` subclass) that walks `record.__dict__` and `record.args` and drops any field whose value is a `Sensitive[T]` instance. The default photophore logger configuration installs this filter. Tests assert that `logger.info("dispatch", extra={"envelope": envelope})` produces a log line with no envelope content bytes.

  Rationale: CONF-06 enumerates three items; we ship all three together since they reinforce each other (the filter catches what the lint misses; the wrapper makes both the lint and filter mechanically detectable).

### Plan structure (housekeeping)

- **D-10 (Keep ROADMAP's 2 plans; do NOT split):**

  ROADMAP defines two Phase 4 plans (04-01 tests + CI gates; 04-02 ADRs + docs + tags). The split is already clean — 04-01 is "machine-verifiable" (everything CI runs); 04-02 is "human-readable + release" (everything humans read or the release script touches). Phase 2 LEARNINGS noted 02-03 grew uncomfortably large; Phase 3 split into 3 to balance — Phase 4's two plans are roughly equal in scope and don't have the same growth pressure. Keep 2.

  Dependencies: 04-02 depends on 04-01 (CI must be green before tagging; ADRs reference test files that 04-01 produces). No parallelization opportunity since 04-02's release-coordination step needs 04-01's CI gates to exist.

  Rationale: don't split when the existing split is already balanced. Plan-phase MAY revisit if 04-01 scope grows beyond comfortable.

### Apple Silicon Secure Enclave (from STATE.md blocker)

- **D-11 (Document as v0.2 follow-up; not a v0.1 release blocker):**

  `python-keyring` against macOS Keychain stores entries that are software-encrypted by the OS at rest and gated by the user's login session. This satisfies the v0.1 threat model items: key material never leaves the keystore, never enters process memory beyond the brief RPC window, never falls back to file/env storage (IDENT-02, IDENT-05). Secure Enclave hardware-anchored entries are a *strengthening* of this, not a correctness fix.

  Phase 4 documents this in `thermocline/docs/install.md` and `photophore/docs/install.md` under §"Known limitations": *"Default `python-keyring` macOS Keychain entries are software-backed (encrypted at rest, gated by the user's login session). Hardware-anchored Secure Enclave entries require Apple Silicon and a developer signing identity, and are deferred to v0.2. The v0.1 threat model is satisfied without Secure Enclave: key material never leaves the keystore."*

  STATE.md blocker entry should be moved to PROJECT.md "Pending Validations" or to a `v0.2-backlog.md` (deferred). 04-LEARNINGS should reflect the resolution.

  Rationale: spec mandate is "delegate to platform keystore; never touch key material directly" — `python-keyring` macOS Keychain satisfies this. Secure Enclave is a hardware lift on top, valuable but not a v0.1 release gate.

### Claude's Discretion

The following are planner / executor discretion (not part of gray-area discussion):

- **Exact AT-* test bodies** — the failure mode each test asserts is fixed by the spec; the harness used is planner's call. Recommended: `pytest` parametrized fixtures + `pytest.mark.at_surface("AT-X<n>")` markers for cross-checking against `at_coverage.py`'s filename-scan.
- **ADR file format details** — MADR-lite is recommended (Context / Decision / Consequences / Status); exact heading levels are planner's call.
- **`tag-v0.1.0.sh` UX** — exact bash output formatting, color codes if any, dry-run mode (recommended: support `--dry-run` for testing).
- **Sanitization of CLI args** — exact hash function (recommended: BLAKE3 to match audit chain hash family, not SHA-256); exact dict-walking algorithm.
- **`docs/` index files** — recommended `docs/index.md` per repo cross-linking install/ops/quickstart; planner finalizes.
- **CI matrix for new ubuntu/macOS split** — already in place for photophore + seamount; thermocline's new CI mirrors photophore's split (ubuntu-latest for lint+pytest, macos-latest for keystore tests).
- **Whether `photophore/python/tests/at_negative/test_at_a1_unknown_key_scheme.py` re-imports the existing `test_e2e_at_a1_replay.py` fixture or duplicates the assertion** — recommended: thin re-export module that the `at_coverage.py` filename scan sees while the actual test logic stays in `integration/`.

### Folded Todos

None — `gsd-sdk query todo.match-phase 4` returned zero matches.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Specs (source of truth — SP-3.3-01..03 amendments land here in Plan 04-02)

- `/Users/dom/Projects/dom/thermocline/README.md` — Thermocline spec v0.3.0-draft. §"Dispatch Signatures", §"Receipt Signatures" (SP-3.3-01..03 amendments target these sections), §"Conformance" (CONF-04 lint enumeration), §"Attack Surfaces" AT-C1..C6.
- `/Users/dom/Projects/dom/photophore/README.md` — Photophore spec v0.3.0-draft. §"Attack Surfaces and Mitigations" AT-A1..A6 (Plan 04-01 implements negative tests; AT-A1 already wired via Phase 3).
- `/Users/dom/Projects/dom/seamount/README.md` — Seamount spec v0.3.0-draft. §"Forge Conformance Requirements" (12-item checklist already validated by Phase 3 harness), §"Attack Surfaces" AT-E1..E5.

### Planning hub (single source of truth)

- `.planning/PROJECT.md` — Suite definition, Key Decisions table (Phase 4 adds CONF-08 release coordination), Constraints. **Phase 4 evolution** updates this with the seven ADR landings + the SP-3.3-01..03 spec amendments.
- `.planning/REQUIREMENTS.md` — CLI-06, CLI-07 (§"Photophore CLI"); CONF-01..08 (§"Cross-Suite Hardening and Conformance"). Plan 04-01 MUST list these in frontmatter.
- `.planning/ROADMAP.md` §Phase 4 — Goal, SC1..SC5, plan list (2 plans — keep per D-10).
- `.planning/STATE.md` §"Blockers/Concerns" — Phase 4 inherits the Secure Enclave gap (D-11), conformance fixture freeze obligation, and SP-3.3-01..03 patch decision (D-02 resolves).

### Phase carry-forward (mandatory pre-reading — decisions locked)

- `.planning/phases/01-thermocline-py-foundations/01-CONTEXT.md` §Implementation Decisions — Phase 1 D-01..D-04 (Receipt private constructor, JSON Schema pipeline, **`Sensitive[T]` introduction — D-09 retrofits all envelope content fields**, conformance fixture YAML manifest).
- `.planning/phases/01-thermocline-py-foundations/01-LEARNINGS.md` — 12D / 10L / 11P / 8S. Critical: BL-01..BL-04 patterns that Phase 3 leaned on; canonical-JSON CI lint pattern (now extended to `print(` lint in D-09).
- `.planning/phases/02-photophore-privacy-primitives-foundations/02-CONTEXT.md` §Implementation Decisions — Phase 2 D-01..D-14. **D-12 / D-13 / D-14 (CLI conventions + exit codes 0–5 used, 6 reserved for dispatch)** directly shape Plan 04-01's CLI-06 retrofit (audit-entry kind, `cli_invocation`).
- `.planning/phases/02-photophore-privacy-primitives-foundations/02-LEARNINGS.md` — 46-item Phase 2 corpus. Critical: **THERMO-01 cross-impl-spec-patch pattern (D-02 applies this pattern again for SP-3.3-01..03)**; property-test-cases-per-property cadence (existing tests run at 100; D-04 bumps to 200).
- `.planning/phases/03-photophore-dispatch-seamount-upgrade-the-integration-phase/03-CONTEXT.md` §Implementation Decisions — Phase 3 D-01..D-05 (forge bootstrap, describe-forge behavior, dispatch error subcodes, integration test process model, plan split). All five carry forward.
- `.planning/phases/03-photophore-dispatch-seamount-upgrade-the-integration-phase/.continue-here.md` §Critical Anti-Patterns — Vercel skill-injection false-positive note (carried forward in this CONTEXT.md's session reminders).

### Phase 3 surfaced specs-patches (input to Plan 04-02 D-02)

- Phase 3 worktree commit history → search for `SP-3.3-01`, `SP-3.3-02`, `SP-3.3-03` to find the SUMMARY entries in `.planning/phases/03-photophore-dispatch-seamount-upgrade-the-integration-phase/03-03-SUMMARY.md` (referenced from STATE.md "Decisions" list; full text TBD on planner-side scout).

### External standards

- RFC 8785 — JSON Canonicalization Scheme. Continuing dependency; SP-3.3-01 clarifies our interpretation of "all map keys present at canonicalization time".
- BLAKE3 spec — chain-hash properties; D-07 also uses BLAKE3 for CLI arg-path hashing (matches audit-chain hash family).
- Keep a Changelog v1.1.0 (https://keepachangelog.com/en/1.1.0/) — CHANGELOG format reference for D-06 (we ship a lite variant).
- MADR (https://adr.github.io/madr/) — ADR template reference for D-03 (we ship a one-page variant).

### Existing reference code (in-tree — read for patterns)

- `/Users/dom/Projects/dom/photophore/tools/ast_lint_network_isolation.py` — Phase 3 AST lint pattern. Plan 04-01's `print(` lint mirrors structure (AST visitor + per-file-path allow-list).
- `/Users/dom/Projects/dom/photophore/python/tests/test_classifier_default_property.py` — CONF-03 property test #1 (bump to 200 in D-04).
- `/Users/dom/Projects/dom/photophore/python/tests/test_audit_chain_property.py` — CONF-03 property test #2 (bump to 200).
- `/Users/dom/Projects/dom/thermocline/thermocline/python/tests/test_canonical_properties.py` — CONF-03 property test #3 (bump to 200).
- `/Users/dom/Projects/dom/photophore/python/tests/test_shadow_uniqueness_property.py` — CONF-03 property test #4 (bump to 200; **new** dispatch-integrated companion lives at `photophore/python/tests/integration/test_property_dispatch_shadow_uniqueness.py` per D-04).
- `/Users/dom/Projects/dom/photophore/python/tests/integration/test_e2e_at_a1_replay.py` — AT-A1 already wired (Phase 3). D-01's `tests/at_negative/test_at_a1_*.py` is a thin re-export pointing here.
- `/Users/dom/Projects/dom/photophore/.github/workflows/ci.yml` — Existing CI shape (ubuntu + macos split; install matrix); thermocline's new CI mirrors this.
- `/Users/dom/Projects/dom/seamount/.github/workflows/ci.yml` — Existing seamount CI; Plan 04-01 extends with `at_negative/` test path inclusion.
- `/Users/dom/Projects/dom/seamount/conformance/forge_conformance/` — Phase 3 harness package; Plan 04-01 adds `at_negative/test_at_e*.py` alongside under `seamount/conformance/`.
- `/Users/dom/Projects/dom/photophore/python/src/photophore/errors.py` — `PhotophoreError` hierarchy + `DispatchError` (Phase 3). Plan 04-01 D-08 message-formatting tweaks land in this module's `__str__`.
- `/Users/dom/Projects/dom/photophore/python/src/photophore/audit/` — append/query/export/verify APIs. D-07 adds a new entry kind `cli_invocation` via the existing kinds-extending pattern.
- `/Users/dom/Projects/dom/photophore/python/src/photophore/cli/` — Click group + per-subcommand modules. D-07 wraps with `@audit_cli_invocation` decorator at the group level.
- `/Users/dom/Projects/dom/thermocline/thermocline/python/src/thermocline/sensitive.py` — `Sensitive[T]` wrapper from Phase 1 D-03 (Plan 04-01 D-09 retrofits content fields to use this).

### Conformance fixtures (input to property-test cadence; conformance fixture freeze obligation per STATE.md)

- `/Users/dom/Projects/dom/thermocline/thermocline/conformance/valid/` — valid fixtures.
- `/Users/dom/Projects/dom/thermocline/thermocline/conformance/invalid/` — invalid fixtures; **Phase 4 freezes the set + annotates each invalid fixture with the AT-* surface it exercises** (THERMO-06 spec text).
- `/Users/dom/Projects/dom/thermocline/thermocline/conformance/MANIFEST.yaml` — phase-tagged fixtures (AT-A1 carries `phase:3`; AT-A2..A6, AT-C1..C6, AT-E1..E5 fixtures land in this phase with `phase:4` tags).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **Phase 3 AST lint pattern** (`photophore/tools/ast_lint_network_isolation.py`) — Plan 04-01's `print(` lint mirrors this: AST `ast.parse` + visitor over `ast.Call` nodes, per-file-path allow-list.
- **Phase 2 property test infrastructure** — Hypothesis `@given` decorators, `@settings(max_examples=N, deadline=None)` patterns; just bump `max_examples` from 100 to 200.
- **Phase 3 `subprocess_forge` fixture** (`photophore/python/tests/integration/conftest.py`) — Phase 4's new dispatch-integrated shadow uniqueness property test reuses this; spawn pi-forge once, dispatch N times, collect shadow IDs, assert distinct.
- **Phase 2 audit kinds-extending pattern** — `photophore.audit.append(kind="dispatch_pre", payload={...})`; new `kind="cli_invocation"` is a 5-line addition to the kinds enum + serialization.
- **Phase 1 `Sensitive[T]` wrapper** (`thermocline/python/src/thermocline/sensitive.py`) — already wraps tier-0 content; D-09 audits remaining content fields and wraps them.
- **Existing CHANGELOG** (`thermocline/CHANGELOG.md`) — already has v0.3.0-draft entry (`thermocline@5c0d87c` cirdan→thermocline patch); Plan 04-02 adds `## [0.1.0] - 2026-MM-DD` section. Photophore and Seamount get new CHANGELOG.md files from scratch.
- **Phase 3 forge_conformance package** — runnable Python package pattern; Plan 04-01's `at_negative/` may grow into a sibling package if AT-E* tests need an entry point.
- **pytest infrastructure across all three repos** — conftest.py + fixture libraries; Plan 04-01 extends with `at_negative/` test directories per D-01.
- **Phase 3 CI workflow shape** (photophore + seamount) — thermocline's new CI mirrors this; lint + non-integration tests on ubuntu, keystore-dependent tests on macos.

### Established Patterns

- **Three-store separation** (Phase 2 D-04) — Plan 04-01 must not introduce any new mixing. The `cli_invocation` audit entries write to the audit DB only.
- **Sync core + async shim** (Phase 2 D-11) — Plan 04-01's dispatch-integrated property test runs sync from pytest via `asyncio.run()` (Phase 3 pattern).
- **Atomic three-step for channel ops** (Phase 2 D-07) — no new use in this phase; just preserved.
- **Exit code per error class** (Phase 2 D-14) — 0–5 used; 6 dispatch (Phase 3); D-07 CLI-06 retrofit does NOT introduce new exit codes (audit-entry write is best-effort wrapped in the finally; failure to write is logged but doesn't change the subcommand's exit code — the user's command outcome is what they see).
- **Privacy-aware logger** (Phase 2; Phase 1 `Sensitive[T]`) — Plan 04-01 D-09 finishes the wiring across all three packages.
- **CLI conventions** (Phase 2 D-12, D-13) — Click group decorator pattern; D-07 wraps the group with `@audit_cli_invocation`.
- **Forge structure** (pi-forge / describe-forge) — Plan 04-01 extends each with `at_negative/` tests under their respective `tests/` dirs (or `seamount/conformance/at_negative/` for cross-forge AT-E tests).
- **Cross-impl spec-patch pattern** (Phase 2 LEARNINGS THERMO-01; **applied again in D-02 for SP-3.3-01..03**) — surface impl-driven spec drift as in-place patches at the draft version.

### Integration Points

- **CI → AST lint → pytest**: each repo's CI runs AST lints (network-isolation, `print(`, canonical-JSON-no-`json.dumps`) BEFORE pytest so structural violations surface clean.
- **CI → at_coverage.py → pytest**: each repo's CI runs `tools/at_coverage.py` BEFORE pytest so missing AT-* coverage surfaces as a clear "missing AT-X coverage" failure rather than a pytest error.
- **CI → forge_conformance → matrix forge**: existing Phase 3 wiring; no change.
- **Release script → repo working trees**: `scripts/tag-v0.1.0.sh` reads `$THERMOCLINE_SUITE_ROOT` (default `~/Projects/dom`) and operates on three sibling repos.
- **ADR cross-refs → relative repo paths**: `photophore/README.md` linking to `thermocline/docs/adr/ADR-0005-no-in-process-key-material.md` uses `../thermocline/docs/adr/...` (works for the sibling-clone dev env and GitHub when both repos are in the same org/user namespace).
- **CHANGELOG → tag annotation**: `tag-v0.1.0.sh` validates the CHANGELOG has the expected `## [0.1.0]` heading before tagging; the tag's annotation message records the cross-repo coordination but does NOT embed the changelog text.
- **`Sensitive[T]` retrofit → `__repr__` test**: a new test in each repo (`thermocline/python/tests/test_sensitive_redaction.py`, `photophore/python/tests/test_sensitive_redaction.py`) enumerates all `Sensitive`-typed fields via Pydantic model introspection and asserts none appear in `repr(model)`.

### Phase 4 work-distribution sketch (planner refines)

- **Plan 04-01** (machine-verifiable; CI gates + property tests + AT-* negatives + CLI-06/07 retrofits + lints):
  - `thermocline/python/tests/at_negative/test_at_c{1..6}_*.py` — 6 new test files (AT-C* surfaces).
  - `thermocline/tools/at_coverage.py` + `thermocline/tools/ast_lint_no_print.py`.
  - `thermocline/.github/workflows/ci.yml` — NEW file; mirrors photophore CI shape.
  - `thermocline/thermocline/python/tests/test_sensitive_redaction.py` — `Sensitive[T]` retrofit assertion.
  - `photophore/python/tests/at_negative/test_at_a{1..6}_*.py` — 6 test files (AT-A1 is a re-export of the Phase 3 integration test per D-01 Claude's-Discretion).
  - `photophore/python/tests/integration/test_property_dispatch_shadow_uniqueness.py` — NEW dispatch-integrated property test.
  - `photophore/tools/at_coverage.py` + `photophore/tools/ast_lint_no_print.py`.
  - `photophore/python/src/photophore/audit/` — new kind `cli_invocation`; `append_cli_invocation()` helper.
  - `photophore/python/src/photophore/cli/__init__.py` — `@audit_cli_invocation` decorator on the click group.
  - `photophore/python/src/photophore/logging.py` — NEW file; `SensitiveFilter` + default logger config.
  - `photophore/python/src/photophore/errors.py` — D-08 message-formatting tweaks.
  - `photophore/.github/workflows/ci.yml` — extend with at_coverage + print-lint steps.
  - `seamount/conformance/at_negative/test_at_e{1..5}_*.py` — 5 test files (AT-E* surfaces).
  - `seamount/conformance/tools/at_coverage.py` (subset for AT-E*).
  - `seamount/.github/workflows/ci.yml` — extend with at_coverage step.
  - All three repos: `pyproject.toml` adds Hypothesis to dev deps (already present in photophore + thermocline).
  - Bump existing 4 property tests to `@settings(max_examples=200)`.
- **Plan 04-02** (human-readable + release):
  - 7 ADRs (paths under §"ADR scope" above).
  - SP-3.3-01..03 spec amendments to `thermocline/README.md`; `thermocline/CHANGELOG.md` `## [0.3.1]` entry.
  - `thermocline/docs/{install.md,ops.md,quickstart.md}`.
  - `photophore/docs/{install.md,ops.md}` + photophore README §"Documentation" section.
  - `seamount/{pi-forge,describe-forge,conformance}/docs/install.md`.
  - `thermocline/scripts/tag-v0.1.0.sh`.
  - Each repo gets a fresh `CHANGELOG.md` (or extension): `## [0.1.0] - 2026-MM-DD` section per the D-06 format.
  - Three coordinated v0.1 git tags (manual invocation of `tag-v0.1.0.sh`).
  - STATE.md + PROJECT.md evolution (post-tag commits).

</code_context>

<specifics>
## Specific Ideas

- **Phase 3 LEARNINGS not yet extracted** — `find .planning -name "03-LEARNINGS.md"` returns empty. Typical pre-discuss step `/gsd-extract-learnings 3` did not run before this discussion. Not a blocker for Phase 4 plan-phase (the relevant decisions are captured in 03-CONTEXT.md and STATE.md), but recommended before plan-phase to surface any Phase-3 patterns that should shape Phase 4 testing. **Action for planner**: run `/gsd-extract-learnings 3` before plan-phase if the user wants the Phase 3 retrospective to inform Phase 4 plans.
- **`test_e2e_at_a1_replay.py` → re-export pattern** — Phase 3 already wrote the AT-A1 integration test. Plan 04-01's `tests/at_negative/test_at_a1_unknown_key_scheme.py` is a thin re-export (1-2 lines: `from ..integration.test_e2e_at_a1_replay import *`) so the `at_coverage.py` filename-scan sees AT-A1 covered without duplicating the assertion. The integration test stays the source of truth.
- **MANIFEST `phase:4` tags** — every new conformance fixture (16 AT-* negatives) gets `phase: 4` in `thermocline/conformance/MANIFEST.yaml`. Mirrors the Phase 3 AT-A1 `phase: 3` tag pattern.
- **`cli_invocation` audit kind schema** — new kind in `photophore.audit.kinds` enum; CHANGELOG.md notes it under "Added" so users running `audit query` against an upgraded chain see the new kind. The Phase 2 D-02 algo_version field ensures forward compatibility — `blake3-v1` chain reads new kinds, no migration needed.
- **CONF-04 final gate list** — verified against Phase 3 wiring:
  1. `ruff check` (all three repos)
  2. `mypy --strict` (thermocline + photophore; seamount forges = source-level only, no strict mypy yet — Plan 04-01 either adds strict to forges or documents the exemption with rationale)
  3. `pip-audit` (all three repos)
  4. Network-isolation AST lint (photophore — exists; thermocline new in 04-01)
  5. `print(` AST lint (NEW — all three repos)
  6. canonical-JSON-no-`json.dumps` lint (thermocline — exists from Phase 1; verify still passing)
  7. `at_coverage.py` (NEW — all three repos; roll-up in thermocline)
  8. `property_coverage.py` (NEW — checks 4 properties exist with `max_examples >= 200`)
  9. `pytest` (all three repos)
  10. `forge_conformance` (seamount only; against both forges per Phase 3 matrix)
- **`tag-v0.1.0.sh` dry-run mode** — `--dry-run` flag prints what would happen without executing `git tag`; useful for testing in the worktree-isolated executor environment without polluting the real repos with test tags.
- **Pre-tag final lint sweep** — `tag-v0.1.0.sh` step (3) runs `python tools/ast_lint_no_print.py` + `python tools/at_coverage.py` in each repo before running pytest, so the script's failure modes match CI's order (structural violations surface before test failures).
- **Worktree-isolated executor note (carried forward)** — Phase 1 + Phase 2 + Phase 3 LEARNINGS all flagged "worktree-isolated executor commits directly on main." If Phase 4 exhibits the same pattern, log + proceed; escalate as harness bug if it recurs a fourth time. Plan-phase reviews this in pre-execution critique.
- **Stale `.pth` files** (Phase 2 LEARNINGS surprise #10) — verify on Plan 04-01 start that `_editable_impl_thermocline.pth` in `photophore/python/.venv` + each forge's `.venv` still points to the canonical `thermocline/python/` source; re-`pip install -e` if drifted.
- **Spurious Vercel skill injection** (Phase 3 .continue-here.md anti-pattern, severity: advisory) — Phase 4 work touches `.github/workflows/*.yml`, which triggers a `deployments-cicd` Vercel skill suggestion. The repo does NOT use Vercel; the injection is a false-positive suffix match. Ignore per CLAUDE.md guidance ("Use Vercel guidance only when the current repo, prompt, or tool call makes it relevant"). This advisory carry-forward is logged here for the planner.
- **Tag message format** — `git tag -a v0.1.0 -m "v0.1.0 — coordinated with thermocline v0.1.0 + photophore v0.1.0 + seamount v0.1.0"` for all three repos (same message); the cross-repo coordination is visible in `git tag -v v0.1.0` output.

</specifics>

<deferred>
## Deferred Ideas

- **Hardware-anchored Secure Enclave coverage** — D-11; documented as v0.2 follow-up. Requires Apple Silicon + developer signing identity; satisfies a strengthening, not a correctness fix.
- **Property tests beyond the four CONF-03 invariants** — additional Hypothesis properties (e.g., audit-export round-trip, channel state-machine determinism) are nice-to-have but not v0.1 gated.
- **Conformance harness against third-party (non-reference) forges** — Phase 3 deferred this; reaffirmed in Phase 4. Post-v0.1 milestone concern (public certification badge).
- **Linux / Windows first-class ops docs** — Phase 4 ships best-effort docs; first-class platform coverage (CI matrix + tested install paths) is v0.2.
- **`mypy --strict` on seamount forges** — Plan 04-01 either extends strict typing to forges or documents the exemption. If exempted, capture as deferred for v0.2.
- **MADR-full ADRs vs MADR-lite** — we chose one-page MADR-lite. A future "ADR audit" pass could expand to the full MADR template (problem / drivers / options / pros-cons) for the seven decisions; not v0.1.
- **CHANGELOG migration to keep-a-changelog full** — we ship Keep-a-Changelog-lite (Added / Implemented / Deferred / Known limitations). Future minor versions may add `Changed` / `Fixed` / `Security` per the full spec.
- **Daemon mode for Photophore** (Phase 3 deferred; reaffirmed Phase 4) — per-CLI-invocation overhead acceptable for v0.1; daemon = v0.2+.
- **Automated release via CI tagging on push to a release branch** — Phase 4 ships a local script invocation. CI-triggered releases are post-v0.1.

### Reviewed Todos (not folded)

None — no todos matched the phase per `gsd-sdk query todo.match-phase 4`.

</deferred>

---

*Phase: 04-hardening-conformance-and-v0-1-release*
*Context gathered: 2026-05-11*
*Auto-mode pass cap: this file is the single pass; no re-passes per `workflows/discuss-phase/modes/auto.md`.*
