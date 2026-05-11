# Phase 3: Photophore Dispatch + Seamount Upgrade — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in `03-CONTEXT.md` — this log preserves the alternatives considered.

**Date:** 2026-05-11
**Phase:** 03-photophore-dispatch-seamount-upgrade-the-integration-phase
**Mode:** `--auto` (all 5 gray areas auto-selected; recommended option auto-picked for each; single pass per `workflows/discuss-phase/modes/auto.md`)
**Areas discussed:** Forge keypair bootstrap UX; describe-forge behavior surface; Dispatch failure-mode surfacing; Integration test process model; Plan split (housekeeping)

`[--auto] Selected all gray areas: forge-bootstrap, describe-forge-behavior, dispatch-failure-surfacing, integration-test-process-model, plan-split.`

---

## Forge keypair bootstrap UX

| Option | Description | Selected |
|--------|-------------|----------|
| A | Auto-generate keypair on first server boot; print pubkey to stdout; operator manually registers on the sovereign side. | |
| B | Explicit `<forge> init` subcommand creates keypair; pubkey exposed at `GET /pubkey`; Photophore `channel new --fetch-pubkey-from <url>` pulls + registers via TOFU. | ✓ |
| C | Keypair auto-generated on first boot; `GET /pubkey` advertises it; sovereign `channel new --from-url` pulls automatically, no init step. | |

`[auto] forge-bootstrap — Q: "How does a fresh forge get a brine keypair, and how does the sovereign learn the pubkey?" → Selected: B (recommended default — explicit init + /pubkey + TOFU register)`

**Why B over A:** A requires manual stdout-copy steps, which makes CONF-07 ("first dispatch in 30 minutes") harder; B is one command per side. Reuses Phase 1 `register_public_key` (BL-01).
**Why B over C:** C couples key generation to server start, which makes ops/restart semantics murkier (does restart rotate?). B keeps generation explicit and idempotent. TOFU vs auto-trust on every fetch is a security-honest default — D-01 documents the rotation = new-channel rule.

---

## describe-forge behavior surface

| Option | Description | Selected |
|--------|-------------|----------|
| A | Accept ≥1 tier-1 shadow; describe ALL shadows in the result; refuse envelopes where tier-0 is present (defense-in-depth). | partial |
| B | Describe ONLY the first tier-1 shadow; ignore others; refuse envelopes with no tier-1 shadow. | |
| C | Describe ALL shadows; on mixed-tier (e.g., tier-2 inline alongside tier-1 shadows), describe shadows only + record `provenance.tiers_present` accurately; do NOT echo inline content. | ✓ |

`[auto] describe-forge-behavior — Q: "What's the input contract and the result shape for describe-forge?" → Selected: C (recommended default — multi-shadow describe + mixed-tier-by-ignoring-inline + explicit refuse on no-tier-1)`

**Why C over A:** A's "refuse if tier-0 present" is implementation-overreach — by the time a request reaches the forge, tier-0 has already been stripped by Photophore dispatch step 3 (shadow generation). The forge can't observe tier-0 because no tier-0 ever crosses the wire (PROJECT.md Core Value). Mixed-tier where tier-1 + tier-2 both exist is the realistic case; ignore-inline-content is the privacy-honest choice (no reflection-as-leak).
**Why C over B:** describing multiple shadows in a single dispatch is normal for any non-trivial envelope; B's "first only" is arbitrary and would surprise integrators. The spec example string is normative — replicated per shadow.

---

## Dispatch failure-mode surfacing

| Option | Description | Selected |
|--------|-------------|----------|
| A | Single exit code 6 with `DispatchError` subcode in output; NO auto-retry; transient failures surface plainly. | |
| B | Multiple exit codes (6 envelope, 7 transport, 8 receipt-verify); auto-retry on transient transport with exponential backoff. | |
| C | Single exit code 6 + 11 subcodes (one per 9-step stage + receipt-malformed + policy-violated); no auto-retry; `retryable: bool` advisory in JSON output; sovereign decides every retry. | ✓ |

`[auto] dispatch-failure-surfacing — Q: "How does a dispatch error surface in human and JSON modes? Auto-retry transient failures?" → Selected: C (recommended default — single exit 6 + 11 subcodes + no-auto-retry + retryable advisory)`

**Why C over A:** A doesn't formalize the subcode set; planners would invent them ad hoc. C nails the 11 (one per 9-step stage + receipt-malformed + receipt-invalid + policy-violated + audit-post) and maps each to a clear retryable advisory bit.
**Why C over B:** B's multiple exit codes conflict with Phase 2 D-14 ("6 reserved for dispatch" — single code). Auto-retry with backoff requires a retry policy + persistence + idempotence guarantees that aren't in v0.1 scope; sovereign-decides keeps the no-daemon mental model intact. POLICY_VIOLATED subcode discharges the Phase 2 POLICY-03 partial closure.

---

## Integration test process model

| Option | Description | Selected |
|--------|-------------|----------|
| A | Pure `subprocess.Popen` — every test spawns a real Flask forge process on an ephemeral port; tests POST real HTTP. | |
| B | Pure in-process Flask `app.test_client()` — embed forges directly; no networking; fast but doesn't exercise transport. | |
| C | Hybrid — happy-path E2E + receipt-verify tests use subprocess (real HTTP, real keystore); fast unit-level negative tests (malformed envelope, missing-tier-1, mixed-tier ignore-inline) use `app.test_client()`. | ✓ |

`[auto] integration-test-process-model — Q: "Subprocess Flask or in-process test_client for the E2E integration tests?" → Selected: C (recommended default — hybrid by test class)`

**Why C over A:** A is correct end-to-end but slow at the unit level; pure subprocess would make negative-path test loops painful and slow CI down.
**Why C over B:** B never exercises the real network boundary, which is exactly what DISP-05 + the AT-A1 wire-in need to prove behaviorally. C gets both — subprocess for "is the contract actually held under real HTTP" and test_client for "is the envelope-validation logic correct" — at the right speed for each.

---

## Plan split (housekeeping)

| Option | Description | Selected |
|--------|-------------|----------|
| A | Keep ROADMAP's 2 plans (03-01 = dispatch + lint; 03-02 = forge upgrades + harness + E2E). | |
| B | Split into 3 plans (03-01 = dispatch + CLI + lint; 03-02 = pi-forge upgrade + describe-forge; 03-03 = E2E + conformance harness). | ✓ |
| C | Re-balance into 3 differently (03-01 = dispatch coordinator + CLI; 03-02 = AST lint + AT-A1 wire; 03-03 = forges + E2E + harness). | |

`[auto] plan-split — Q: "Keep 2 plans per ROADMAP or split into 3 along repo/concern boundaries?" → Selected: B (recommended default — 3 plans, clean repo boundaries, clean dependencies)`

**Why B over A:** Phase 2 LEARNINGS noted 02-03 grew uncomfortably large; the 2-plan version of Phase 3 would repeat that with 03-02 doing pi-forge upgrade + describe-forge + harness + E2E (4 substantial concerns). 3 plans gives Photophore-only / Seamount-only / Cross-cutting partitioning that matches the actual review surfaces.
**Why B over C:** C splits the lint + AT-A1 wire-in into their own plan, but those are both tiny (lint is a single file; AT-A1 wire is two log lines in step 1 of dispatch). They naturally belong with the dispatch coordinator they enforce. C would over-shard.

**Note for plan-phase:** ROADMAP.md currently lists 2 plans for Phase 3. Plan-phase MUST update §"Phase 3" plan list to reflect the 3-plan split (D-05) as part of its commit. Plan IDs become 03-01, 03-02, 03-03.

---

## Claude's Discretion

The following sub-decisions are NOT in this discussion log — Claude (planner / executor) decides them:

- Exact subprocess-startup probe protocol (recommended: `PIFORGE_READY port=<n>` stdout line)
- AST-lint file location and CI-step wiring (recommended: `photophore/tools/ast_lint_network_isolation.py`)
- Conformance fixture corpus selection per forge
- `describe-forge` keystore identity string (recommended: `"describe-forge"`)
- CI matrix shape for the conformance harness (recommended: single matrix with `forge` axis)

## Deferred Ideas

Captured in `03-CONTEXT.md` `<deferred>` section. Summary:

- Forge pubkey rotation protocol (TOFU only in v0.1; rotation = new channel)
- Auto-retry with backoff for retryable subcodes
- Photophore daemon mode (no long-running process in v0.1)
- Conformance harness against external (non-reference) forges
- `pi-forge job` support (spec v0.2)
- Job-envelope dispatch path in Photophore (spec v0.2)

No reviewed-but-deferred todos — `gsd-sdk query todo.match-phase 3` returned zero matches.
