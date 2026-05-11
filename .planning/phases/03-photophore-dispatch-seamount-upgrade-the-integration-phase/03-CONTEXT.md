# Phase 3: Photophore Dispatch + Seamount Upgrade — Context

**Gathered:** 2026-05-11
**Status:** Ready for planning
**Mode:** `--auto` (single-pass; recommended option auto-selected for each gray area; see DISCUSSION-LOG.md for the trade-off table)

<domain>
## Phase Boundary

This phase delivers the **first real, working privacy-receipt round trip** for the Thermocline suite: Photophore's async dispatch coordinator runs the full 9-step flow end-to-end against two real Flask forges over real HTTP, both signing receipts with real ed25519 (brine) keys held in their own platform keystore entries.

What lands:

- `photophore.dispatch` — async coordinator implementing the 9-step flow (resolve channel → classify → shadow → policy → audit-pre → sign → send → verify-receipt → audit-post) with type-enforced receipt verification gate and POLICY-03 partial-closure check.
- `photophore dispatch` CLI subcommand wired to exit code 6 (Phase 2 D-14 reserved this code for dispatch errors).
- Custom AST lint enforcing the network-isolation contract (DISP-05) — HTTP imports forbidden outside `photophore.dispatch` and forge `server.py` files.
- `seamount/pi-forge/` upgraded from `key_scheme="none"` stubs to real brine via `thermocline-py` (retires `envelope.py:_verify_brine` and `envelope.py:_sign_receipt`); first forge keypair bootstrap UX.
- `seamount/describe-forge/` — the first reference forge that exercises tier-1 shadow handling end-to-end; templated description per FORGE-03.
- First Photophore → forge integration tests (happy + negative — forged receipt, missing-shadow, policy-violation).
- Cross-suite conformance harness (`seamount/conformance/` → `forge_conformance` package) mapped to the Seamount 12-item checklist, run in CI against both forges.
- AT-A1 behavioral wire-in (carried forward from Phase 2 — MANIFEST `phase:3` tag on the fixture).

What does NOT land in this phase (deferred):

- Per-step shadow generation for `job` envelopes (spec v0.2; out of scope).
- `result_policy` authoring inside `manifest` (spec v0.2; out of scope; `task`-envelope policy only — already covered by Phase 2).
- Ring 2 / Ring 3 anchoring, multi-hop channels (spec v0.2+).
- Property tests, the remaining 16 AT-* negative tests, ADRs, ops docs, v0.1 git tags — these are Phase 4 (CONF-01..08).
- LLM-backed forges; `pi-forge` accepting `job` envelopes (deferred forever / next milestone per PROJECT.md "Out of Scope").

</domain>

<decisions>
## Implementation Decisions

### Forge keypair bootstrap + sovereign pubkey acquisition (FORGE-01, FORGE-03, CONF-07)

- **D-01 (Forge bootstrap UX = `init` subcommand + `GET /pubkey` endpoint + TOFU register on the sovereign side):**

  Each forge (pi-forge, describe-forge) ships an `init` subcommand (e.g., `pi-forge init`, `describe-forge init`) that calls `thermocline.identity.BrineProvider.create()` against a forge-specific keystore service namespace — `seamount.piforge` and `seamount.describeforge` respectively — using the forge's stable identity string (`pi-forge`, `describe-forge`). Running `init` a second time is idempotent: if the keypair already exists in the keystore it's a no-op success; if a different identity is requested via `--identity <name>` and one exists at that service+username, the command exits non-zero and refuses to overwrite (operator must explicitly delete the old entry).

  Each forge HTTP surface exposes a new `GET /pubkey` endpoint returning `{"identity": "<name>", "key_scheme": "brine", "pubkey": "<hex>"}`. The endpoint is unauthenticated and read-only — public key by definition.

  On the sovereign-node side, `photophore channel new` gains a `--fetch-pubkey-from <url>` flag. When the flag is present, the CLI:
    1. GETs `<url>/pubkey` (httpx; this is the ONE allowed cross-boundary HTTP call outside `photophore.dispatch`, exempted in the AST lint by file path + endpoint).
    2. Calls `BrineProvider.register_public_key(channel.remote_node, pubkey_hex)` (Phase 1 BL-01 cross-role API).
    3. Persists the channel record per Phase 2 D-04..D-07 atomic three-step (keystore → audit → channels.db).

  Pubkey trust model = **TOFU (trust-on-first-use)**: the pubkey presented at `channel new` time is locked in the keystore from that moment forward. Subsequent dispatch-time verification mismatches are hard failures with `DispatchError.RECEIPT_INVALID` — no re-fetch, no rotation negotiation. Forge pubkey rotation requires a new channel (`channel new` against the rotated forge URL).

  Rationale: minimizes manual steps end-to-end (clone → `pi-forge init && pi-forge serve` → `photophore channel new --fetch-pubkey-from http://localhost:5000` → first dispatch); reuses Phase 1's `register_public_key` API; respects the "no remote sync of the trust store" mandate (pubkey is data, not state); makes CONF-07 30-minute walk feasible. TOFU keeps the security model honest — no surprise re-trust without a fresh deliberate human act.

### `describe-forge` behavior surface (FORGE-03)

- **D-02 (Multi-shadow describe; tier-1-required; mixed-tier handled by ignoring inline):**

  Accepted envelopes: `task` with at least one `context[]` block of `tier=1` whose `kind="shadow"`. The forge iterates `context[]` and for each tier-1 shadow appends an entry to `outputs.descriptions: list[{shadow_id: str, content_type: str, relevance: float, description: str}]`, where `description` is the templated string exactly per spec: `"This forge received a shadow of type '<content_type>' with relevance <relevance>."` (the spec example is normative; any deviation breaks FORGE-03 verification). Stateless; no caching; no learning.

  Rejection (HTTP 400, structured error envelope per existing pi-forge pattern):
    - Zero tier-1 shadows in `context[]` → `UNSUPPORTED_TASK_TYPE`, message `"describe-forge requires at least one tier-1 shadow in context[]"`.
    - Malformed shadow block (missing `shadow_id`, `content_type`, or `relevance`) → `MALFORMED_ENVELOPE`.

  Mixed-tier handling (tier-1 shadows AND tier-2 inline content in same `context[]`): describe shadows only; **do NOT echo, reflect, summarize, or otherwise pass through any inline content** — that prevents accidental reflection-as-leak (a tier-2 content block reflected verbatim in a result is the kind of subtle privacy regression the suite exists to prevent). The result's `provenance.tiers_present` records all tiers actually present in the envelope (e.g., `[1, 2]`); the result's `outputs.note` field carries the human-readable `"describe-forge operated on N shadows; M inline blocks ignored"` only when M > 0. `outputs.descriptions` always contains only shadow descriptions.

  Surface fields in the `task_result` envelope (mirroring pi-forge `envelope.build_task_result()` keys for consistency):
    - `outputs.descriptions: list[ShadowDescription]`
    - `outputs.note: str | None`
    - `provenance.shadows_received: list[shadow_id]` (same as pi-forge contract)
    - `provenance.tiers_present: list[int]` — actual tiers seen in the request envelope
    - `provenance.local_tiers_present: false` (always — tier-0 never crosses the wire by Photophore design)
    - `receipt_signature: ReceiptSignature` (real brine, per D-01)

### Dispatch failure-mode surfacing (DISP-01..06, POLICY-03, CLI-03)

- **D-03 (Single exit code 6 + 11 `DispatchError` subcodes; no auto-retry; `retryable: bool` advisory):**

  Exit code 6 is reserved for ALL dispatch errors (Phase 2 D-14 carry-forward). The `DispatchError` class is the single error class raised by `photophore.dispatch.dispatch()`; the subcode is a `StrEnum` member surfaced in CLI output, in the structured error returned from the async API, and in the audit log payload of the pre-dispatch audit entry when the failure happens AFTER audit-pre but BEFORE audit-post.

  The 11 subcodes (each maps to a specific stage of the 9-step flow):

  | Stage | Subcode | Retryable | Notes |
  |-------|---------|-----------|-------|
  | 1 | `CHANNEL_RESOLVE_FAILED` | false | Channel unknown / SUSPENDED / CLOSED |
  | 2 | `CLASSIFICATION_FAILED` | false | Rules-config error or classifier exception |
  | 3 | `SHADOW_GENERATION_FAILED` | false | Irreversibility hard fail or generator error |
  | 4 | `POLICY_AUTHORING_FAILED` | false | Policy authoring exception |
  | 5 | `AUDIT_FAILED_PRE` | true | Pre-dispatch audit write failed (DISP-02 — no signing happens) |
  | 6 | `SIGNING_FAILED` | true | Identity provider error / keystore unreachable / locked |
  | 7 | `TRANSPORT_TIMEOUT` / `TRANSPORT_REFUSED` | true | Forge unreachable / handshake failed |
  | 8a | `RECEIPT_MALFORMED` | false | Receipt block missing required fields |
  | 8b | `RECEIPT_INVALID` | false | DISP-03 — receipt signature failed brine verify |
  | 8c | `POLICY_VIOLATED` | false | POLICY-03 partial closure — `compare_result_against_policy(received, authored_policy)` returned violation |
  | 9 | `AUDIT_FAILED_POST` | true | Receipt was verified; post-receipt audit write failed; replay-safe |

  **No automatic retries.** The sovereign decides every retry. The CLI prints `retryable: <bool>` for human use; the structured JSON includes the same field. Replay strategy for `AUDIT_FAILED_PRE` and `AUDIT_FAILED_POST` is documented as a manual operator step (re-run the same dispatch command) — Phase 4 docs cover this.

  CLI exit codes 0–5 remain as Phase 2 assigned them; exit 6 is the dispatch family; exit 7+ are reserved for future use (not assigned in this phase). All non-retryable subcodes that are security-relevant (`RECEIPT_INVALID`, `POLICY_VIOLATED`) are logged at WARNING level via the privacy-aware logger (no envelope bytes; subcode, channel_id, envelope_id, audit_entry_hash only).

  Human-mode CLI error format (single line, structured):

  ```
  error: dispatch failed (RECEIPT_INVALID) at step 8: signature verification failed for envelope <id> via channel <id>. retryable: false. audit entry: <hash>.
  ```

  JSON-mode CLI error envelope (per Phase 2 D-12):

  ```json
  {
    "error": "DispatchError",
    "subcode": "RECEIPT_INVALID",
    "stage": 8,
    "message": "signature verification failed",
    "retryable": false,
    "envelope_id": "...",
    "channel_id": "...",
    "audit_entry_hash": "..." 
  }
  ```

  `audit_entry_hash` is present when the failure happened after the pre-dispatch audit write succeeded; absent otherwise.

### Integration test process model (DISP-05 boundary verification, FORGE-04..05 conformance)

- **D-04 (Hybrid: subprocess for happy-path + receipt-verify; `app.test_client()` for fast unit-level negative paths):**

  E2E tests that exercise the full network-crossing path (Photophore → forge over real HTTP, real ed25519 sign/verify, real keystore reads) run the forge as a real Flask process via `subprocess.Popen`. A pytest fixture `subprocess_forge(role: Literal["pi-forge", "describe-forge"])` handles:
    1. Spawn `<role>` on an ephemeral port (port 0; read assigned port from the process via a short stderr/stdout probe protocol).
    2. Run `<role> init` first in a temporary keystore namespace (`seamount.<role>.test-<uuid>`) so tests do not collide with the dev keystore.
    3. Wait until `GET /pubkey` returns 200 (readiness probe with timeout).
    4. Yield `(url, pubkey, role)` to the test.
    5. Teardown: SIGTERM the process; delete the test keystore namespace entries.

  Negative-path tests that don't actually need transport — malformed envelope rejection, missing-tier-1 rejection on describe-forge, mixed-tier ignore-inline assertion — use Flask's `app.test_client()` directly against the forge module, no subprocess, no keystore. These are fast (~ms vs ~100ms+ for subprocess fixtures).

  The hybrid model satisfies DISP-05 (the AST lint guarantees the contract at code level; the subprocess fixtures prove the contract behaviorally at runtime against real HTTP), and gives the AT-A1 wire-in (Phase 2 carry-forward, MANIFEST `phase:3` tag) a place to live: an integration test that replays the AT-A1 fixture through Photophore → pi-forge over real HTTP and asserts on the audit-log content.

  Test keystore hygiene: every `subprocess_forge` fixture finalizer deletes its `seamount.<role>.test-<uuid>` namespace; a session-scoped autouse fixture in `conftest.py` does a final sweep of any orphaned `*.test-*` entries (handles SIGKILL recovery from interrupted runs).

  Receipt-forgery test: a separate fixture `forged_receipt_forge` is a tiny in-process Flask app served via subprocess that always returns a receipt with `sig` set to a known-invalid string; the dispatch is expected to return `DispatchError.RECEIPT_INVALID` and the audit log must contain zero entries referencing the forged receipt (DISP-03 conformance).

### Plan split (housekeeping; was 2 plans in ROADMAP) — 3 plans

- **D-05 (Split ROADMAP's 2 plans into 3 for balance and clean dependencies):**

  ROADMAP.md currently lists 2 plans for Phase 3. We split into 3 to keep each plan close in size to Phase 2's 02-01..02-03 (Phase 2 LEARNINGS noted 02-03 grew uncomfortably large; do not repeat that pattern when we can split cleanly along repo and concern boundaries). Plan-phase MUST update ROADMAP.md to reflect the new plan count (3) and re-numbered plan IDs as part of its phase commit. The 3 plans:

  - **Plan 03-01 — `photophore.dispatch` (Photophore-only):**
    - Async dispatch coordinator implementing the 9-step flow with `httpx.AsyncClient`.
    - `dispatch.aio` shim (~20 LOC per Phase 2 D-11) wrapping Phase 2's sync APIs (`audit.append`, `channels.show`, `classify`, `shadow.generate`, `policy.author`) via `asyncio.to_thread`.
    - Canonical-JSON signing input via `thermocline.canonical.canonicalize` (DISP-04); property test for round-trip stability deferred to Phase 4 (CONF-03) but smoke-tested here.
    - Audit-pre / audit-post with hard-fail semantics (DISP-02, DISP-03).
    - POLICY-03 partial-closure call: `compare_result_against_policy(received_result, authored_policy)` at step 9 BEFORE audit-post (Phase 2 carry-forward, frontmatter MUST cite POLICY-03).
    - `photophore dispatch` CLI subcommand (CLI-03) with `--channel <id>`, `--task <draft.json>`, `--json` (Phase 2 D-12), exit 6 family per D-03 above.
    - Custom AST lint at `tools/ast_lint_network_isolation.py` enforcing DISP-05: rejects `import httpx | requests | aiohttp` in `photophore.{classifier,shadow,policy,audit,channels,core}` and `thermocline.{envelope,canonical,identity,schemes}`; allow-listed in `photophore.dispatch` and `photophore.cli.dispatch_command`.
    - AT-A1 behavioral wire-in: the dispatch coordinator's classifier-result step records the `path_rule:<reason>` provenance in the pre-dispatch audit payload exactly as the MANIFEST `phase:3` AT-A1 fixture expects.

  - **Plan 03-02 — Forge upgrades (Seamount-only, both forges):**
    - Upgrade `seamount/pi-forge/`:
      - Replace `pi-forge/envelope.py` with calls into `thermocline.envelope` + `thermocline.identity` (retires the `envelope.py:_verify_brine` stub at lines 87–99 and `envelope.py:_sign_receipt` stub at lines 139–165).
      - Wire `BrineProvider` initialized against `seamount.piforge` keystore service.
      - Keep `key_scheme="none"` as a configurable dev-mode option (`FORGE_KEY_SCHEME=none` env var) for local development without keystore — but the default is `brine`.
      - `pi-forge init` subcommand + `GET /pubkey` endpoint per D-01.
      - Regression: replay `pi-forge/examples/task-100-digits.json` through the new envelope handling, assert outputs equivalent modulo IDs/timestamps (FORGE-02).
    - Add `seamount/describe-forge/`:
      - Flask app skeleton mirroring pi-forge's `server.py` structure.
      - Templated description per D-02; tier-1 required; mixed-tier ignore-inline.
      - `describe-forge init` subcommand + `GET /pubkey` endpoint per D-01.
      - Own `pyproject.toml`, own `.venv` (per `.continue-here.md` Infrastructure State).

  - **Plan 03-03 — E2E integration tests + cross-suite conformance harness (cross-cutting):**
    - Photophore → pi-forge happy-path E2E test (subprocess fixture, real brine, examples/task-100-digits replay).
    - Photophore → describe-forge happy-path E2E test (subprocess fixture, tier-1 shadow in context[], templated description in result).
    - Forged-receipt negative test (DISP-03 conformance) — see D-04.
    - Policy-violated negative test (POLICY-03) — describe-forge variant that returns a result violating an authored `result_policy`, dispatch must fail with `DispatchError.POLICY_VIOLATED`.
    - Cross-suite conformance harness package `seamount/conformance/forge_conformance/` (FORGE-04) — runnable Python package that POSTs envelopes from `thermocline/conformance/` fixtures and validates against `thermocline/schema/` JSON Schemas + verifies receipt signatures; structured pass/fail report mapped to the Seamount 12-item conformance checklist (FORGE-05).
    - CI hook: `forge_conformance` invoked against both forges on every PR — wire into both `photophore/` and `seamount/` CI workflows.

  Dependencies: 03-02 depends on 03-01 (forges need real `thermocline.identity.BrineProvider` API stable — but that already shipped in Phase 1, so this is really 03-02 depending on Phase 1's locked surface, not on 03-01). 03-03 depends on both 03-01 and 03-02. Plans 03-01 and 03-02 are parallelizable (different repos, no shared file edits).

### Claude's Discretion

The following implementation details are within Claude's discretion (planner / executor) and were not part of the gray-area discussion:

- **Process-startup protocol for the `subprocess_forge` fixture** — exact stdout/stderr parsing format to read the bound ephemeral port. Recommended: forge prints `PIFORGE_READY port=<n>` once Flask is listening; fixture polls until line appears or timeout (e.g., 5s).
- **AST-lint file location and registration** — likely `photophore/tools/ast_lint_network_isolation.py` invoked from `photophore/python/Makefile` and from the `photophore/.github/workflows/ci.yml` job; planner finalizes paths.
- **Conformance fixture corpus** — exact list of envelopes the harness exercises against each forge. Minimum: every fixture in `thermocline/conformance/` that pi-forge / describe-forge declare compatible with. Phase 3 might also derive a few new fixtures from real dispatches and freeze them; the cross-impl-spec-patch pattern (Phase 2 LEARNINGS THERMO-01) applies if a fixture surfaces a spec ambiguity.
- **`describe-forge` keystore identity string** — recommended `"describe-forge"` (matches the binary name); planner finalizes.
- **CI matrix** — whether to run the conformance harness against both forges in a single matrix step or two separate jobs. Recommended: single matrix step with `forge` axis = `[pi-forge, describe-forge]`; cheaper failure isolation.

### Folded Todos

None — `gsd-sdk query todo.match-phase 3` returned zero matches.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Specs (source of truth)

- `/Users/dom/Projects/dom/thermocline/README.md` — Thermocline spec v0.3.0-draft. Envelope shapes (`task`, `task_result`, `task_error`), `dispatch_signature` / `receipt_signature` block schemas, `key_scheme` values, role definitions.
- `/Users/dom/Projects/dom/photophore/README.md` — Photophore spec v0.3.0-draft. §"Dispatch (9-step flow)", §"The Privacy Receipt", §"Attack Surfaces and Mitigations" AT-A1..A6 (AT-A1 wired in this phase).
- `/Users/dom/Projects/dom/seamount/README.md` — Seamount spec v0.3.0-draft. §"Forge Conformance Requirements" (12-item checklist for FORGE-05 mapping), §"Receipt Signature" block shape, AT-E1..E5 surfaces.

### Planning hub (single source of truth for cross-repo planning)

- `.planning/PROJECT.md` — Suite definition, Key Decisions table, Constraints (especially "no cloud inference for classification" and the 3-store mandate).
- `.planning/REQUIREMENTS.md` — DISP-01..06 (§"Photophore Dispatch and Privacy Receipts"); CLI-03 (§"Photophore CLI"); FORGE-01..05 (§"Seamount Forge Upgrades"); CONF-07 (cross-suite, mentioned but its full satisfaction lives in Phase 4).
- `.planning/ROADMAP.md` §Phase 3 — Goal, Success Criteria SC1..SC5, plan list (PLAN-PHASE MUST UPDATE this section to reflect the 3-plan split per D-05).

### Phase carry-forward (mandatory pre-reading — decisions locked)

- `.planning/phases/01-thermocline-py-foundations/01-CONTEXT.md` §Implementation Decisions — Phase 1 D-01..D-04 (Receipt private constructor, JSON Schema pipeline, `Sensitive[T]`, conformance fixture YAML manifest).
- `.planning/phases/01-thermocline-py-foundations/01-LEARNINGS.md` — Phase 1 corpus (12D / 10L / 11P / 8S). Critical: BL-01 `_PUBKEY_PREFIX` + `register_public_key` cross-role API (used by D-01 above); `isinstance` keystore probe.
- `.planning/phases/02-photophore-privacy-primitives-foundations/02-CONTEXT.md` §Implementation Decisions — Phase 2 D-01..D-14 (audit + channels + classifier rules + sync API surface + CLI conventions). D-11 (sync core + ~20 LOC `dispatch.aio` shim) and D-14 (exit code 6 reserved for dispatch) shape this phase.
- `.planning/phases/02-photophore-privacy-primitives-foundations/02-LEARNINGS.md` — Phase 2 46-item corpus. Critical: THERMO-01 cross-impl-spec-patch pattern (expect another in Phase 3); shadow soft-fail-warnings discipline; POLICY-03 partial-closure obligation (drives Plan 03-01 frontmatter requirement); worktree-isolated executor commits directly on main.

### External standards

- RFC 8785 — JSON Canonicalization Scheme. Already a Phase 1 dependency (`rfc8785` package); Plan 03-01's `canonicalize()` call is on this spec.
- BLAKE3 spec — chain-hash properties already used by audit log; no new use in this phase (no new audit shapes added).

### Reference implementation to learn from (in-tree — read for patterns)

- `/Users/dom/Projects/dom/thermocline/thermocline/python/src/thermocline/identity.py` — `BrineProvider`, `_PUBKEY_PREFIX`, `register_public_key`, `Verifier`, `IdentityProvider` Protocol. The whole identity surface used by Phase 3.
- `/Users/dom/Projects/dom/thermocline/thermocline/python/src/thermocline/canonical.py` — `canonicalize()` for signing input (DISP-04).
- `/Users/dom/Projects/dom/thermocline/thermocline/python/src/thermocline/schemes.py` — `KeyScheme` enum, `Signature` block.
- `/Users/dom/Projects/dom/photophore/python/src/photophore/audit/` — append/query/export/verify APIs; `_query_rows()` typed wrapper; Phase 2 D-01..D-03 shapes.
- `/Users/dom/Projects/dom/photophore/python/src/photophore/channels/` — channel lifecycle, bootstrap, three-store atomic ordering (Phase 2 D-04..D-07).
- `/Users/dom/Projects/dom/photophore/python/src/photophore/classifier/` — `classify(content)` sync API (Phase 2 D-08..D-10).
- `/Users/dom/Projects/dom/photophore/python/src/photophore/shadow/` — `shadow.generate(content, content_type)`; `ShadowResult.warnings` discipline.
- `/Users/dom/Projects/dom/photophore/python/src/photophore/policy/` — `policy.author(channel, envelope_draft)`; `compare_result_against_policy()` for POLICY-03 (Phase 2 carry-forward).
- `/Users/dom/Projects/dom/photophore/python/src/photophore/errors.py` — Existing `PhotophoreError` hierarchy. Plan 03-01 adds `DispatchError` here with the 11-subcode `StrEnum`.
- `/Users/dom/Projects/dom/seamount/pi-forge/server.py` — Existing Flask app, `handle_task()` at line 30, `health()` at line 99. The shape Plan 03-02 evolves.
- `/Users/dom/Projects/dom/seamount/pi-forge/envelope.py` — Lines 87–99 (`_verify_brine` stub) and 139–165 (`_sign_receipt` stub) — the exact code FORGE-01 retires.
- `/Users/dom/Projects/dom/seamount/pi-forge/examples/task-100-digits.json` — Regression fixture for FORGE-02.

### Conformance fixtures (in-tree)

- `/Users/dom/Projects/dom/thermocline/conformance/` — JSON envelopes + YAML MANIFEST per Phase 1 D-04. The `forge_conformance` harness (Plan 03-03) consumes fixtures from here.
- `/Users/dom/Projects/dom/thermocline/conformance/MANIFEST.yaml` — phase-tagged fixtures; the AT-A1 fixture carries `phase:3` and is consumed by Plan 03-03 integration tests.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `thermocline.identity.BrineProvider` (Phase 1) — full ed25519 sign/verify lifecycle via `python-keyring`. `create()`, `register_public_key()`, `sign()`, `verify()`. Each forge instantiates its own under a forge-specific service namespace (D-01); Photophore instantiates one in dispatch for signing outgoing envelopes + verifying receipts.
- `thermocline.identity.Verifier` (Phase 1) — receipt verification entry point. Plan 03-01's step 8 calls `Verifier.verify()`; failure raises an exception that maps to `DispatchError.RECEIPT_INVALID`.
- `thermocline.canonical.canonicalize` (Phase 1) — RFC 8785 JCS for signing input. Both dispatch (envelope sign) and forge (receipt sign + verify) use this.
- `thermocline.sensitive.Sensitive[T]` (Phase 1) — wraps tier-0 content. Dispatch's classify step inspects but never reveals; shadow generator (Phase 2) extracts non-reversible features; nothing tier-0 makes it past step 3.
- `photophore.audit.append / query / verify` (Phase 2 D-01..D-03) — sync APIs; dispatch awaits them via `asyncio.to_thread` in the `dispatch.aio` shim (Phase 2 D-11).
- `photophore.channels.show` (Phase 2 D-04..D-07) — channel record lookup; dispatch step 1 uses this.
- `photophore.classifier.classify` + `photophore.shadow.generate` + `photophore.policy.author` — sync APIs from Phase 2, all consumed via the same `asyncio.to_thread` shim.
- `photophore.errors.PhotophoreError` hierarchy — `DispatchError(PhotophoreError)` extends it; subcode `StrEnum` is a class attr.
- `seamount/pi-forge/server.py` `handle_task()` (line 30) — existing 12-step request handler; FORGE-01 replaces envelope validation block with `thermocline.envelope` calls and receipt-building block with `thermocline.identity.BrineProvider.sign()` over `thermocline.canonical.canonicalize` output.
- `pi-forge/examples/task-100-digits.json` — Regression fixture for FORGE-02; Plan 03-02 replays it with the new envelope handling and asserts equivalence.
- pytest fixture vocabulary from Phase 2 — `tmp_path`, `freezer`, sync-keystore fixtures via `python-keyring` `set_keyring()`; extended in Plan 03-03 with the `subprocess_forge(role)` fixture.

### Established Patterns

- **Sync core + async shim** (Phase 2 D-11) — Phase 3 dispatch is async; uses ~20 LOC of `asyncio.to_thread` wrappers; no `aiosqlite`.
- **Three-store separation** (Phase 2 D-04) — audit DB, channels DB, keystore are three discrete files/stores. Plan 03-01 must not introduce any new mixing — dispatch reads from all three but writes only to audit DB.
- **Atomic three-step for channel ops** (Phase 2 D-07) — `keystore.set → audit.append → channels.db.upsert`. New: same idempotent pattern when registering a fetched forge pubkey under `channel new --fetch-pubkey-from`.
- **Exit code per error class** (Phase 2 D-14) — 0–5 used; 6 reserved for dispatch (now claimed; subcoded per D-03).
- **Privacy-aware logger** (Phase 2; Phase 1 `Sensitive[T]`) — Plan 03-01's log statements use logger filter that drops `sensitive=True` fields; no envelope bytes ever in log output.
- **CLI conventions** (Phase 2 D-12, D-13) — `--json` flag (per-subcommand JSON vs JSONL by nature); `photophore dispatch` is a single subcommand under the shared `click.Group`.
- **Forge structure** (pi-forge) — `server.py` (Flask) + `envelope.py` (validation/build) + `pi.py` (task-specific compute). Plan 03-02 mirrors this in `describe-forge/`: `server.py` + `envelope.py` + `describe.py` (templated description).
- **Cross-impl spec-patch pattern** (Phase 2 LEARNINGS THERMO-01) — if Plan 03-02 or 03-03 surfaces a spec ambiguity (e.g., describe-forge result envelope shape underdefined), patch the spec in-place and cite the patch from the plan's PR.

### Integration Points

- **Photophore dispatch → forge HTTP boundary** — the only place inside Photophore that imports `httpx`. AST-lint enforced (DISP-05).
- **Photophore dispatch → audit log** — two writes per dispatch (pre-dispatch event + receipt event); both via `audit.append`. Replay safety: pre-dispatch entry contains envelope_id + classifier output + policy hash; receipt entry contains envelope_id + receipt sig + verification result.
- **Photophore dispatch → identity provider** — `BrineProvider.sign()` for outgoing envelope dispatch_signature; `Verifier.verify()` for incoming receipt_signature.
- **Photophore CLI → photophore.dispatch.dispatch_async** — CLI invokes via `asyncio.run()`; CLI is the only sync entry point for the async coordinator in this phase.
- **Forge → thermocline-py** — both forges depend on `thermocline-py` (already published in Phase 1 as editable install in `seamount/pi-forge/.venv` per the bootstrap UX). The dependency replaces the in-tree `pi-forge/envelope.py`.
- **AST lint → photophore CI** — new tool in `photophore/tools/`; invoked from `Makefile lint` target and from CI workflow; fails build on contract violation.

### Network-isolation contract (DISP-05, enforced via AST lint in Plan 03-01)

Forbidden imports `(httpx | requests | aiohttp)` in:
- `photophore.{classifier,shadow,policy,audit,channels,core}`
- `thermocline.{envelope,canonical,identity,schemes,sensitive}`

Allowed imports (`httpx`) in:
- `photophore.dispatch.*`
- `photophore.cli.dispatch_command` (single carve-out for the `--fetch-pubkey-from` flag in `channel new`; lint allow-list by exact file path).

Allowed imports (`flask`) in:
- `seamount/pi-forge/server.py`
- `seamount/describe-forge/server.py`

</code_context>

<specifics>
## Specific Ideas

- **POLICY-03 partial closure obligation** — Plan 03-01's PLAN.md frontmatter MUST list POLICY-03 in `requirements:` (Phase 2 LEARNINGS surfaced this; the dispatch coordinator's step 9 calls `compare_result_against_policy()` before audit-post, closing the spec gap that Phase 2 partially opened).
- **AT-A1 behavioral wire-in** — the dispatch coordinator records classifier provenance (`path_rule:<reason>` strings per Phase 2 D-10) in the pre-dispatch audit event payload. The Phase 2 MANIFEST `phase:3` AT-A1 fixture asserts on this payload exactly. Plan 03-01's tests replay the fixture and assert byte-for-byte equivalence after timestamps are normalized.
- **`forge_conformance` package naming** — the package is `forge_conformance` (snake_case for Python imports); the directory is `seamount/conformance/`. CI invokes `python -m forge_conformance --target http://localhost:5000 --role pi-forge` etc.
- **`describe-forge` exit codes** — same conventions as pi-forge (existing Flask app patterns); HTTP-status mapping for `MALFORMED_ENVELOPE` (400), `UNSUPPORTED_TASK_TYPE` (400), `SIGNATURE_INVALID` (401), unexpected errors (500).
- **Templated description as normative string** — D-02's exact `"This forge received a shadow of type '<content_type>' with relevance <relevance>."` template is the spec example; treat it as normative. Any executor temptation to "make it more descriptive" is rejected — that's the LLM-backed-forge concern from the deferred Out-of-Scope list.
- **Worktree-isolated executor note** — Phase 1 + Phase 2 LEARNINGS both flagged "executor commits directly on main" — if Phase 3 shows the same, log + proceed; escalate as harness bug if it recurs a third time. Plan-phase reviews this in pre-execution critique.
- **Stale `.pth` files** — Phase 2 LEARNINGS surprise #10 — verify on Plan 03-02 start that `_editable_impl_thermocline.pth` in `seamount/pi-forge/.venv` still points to the canonical `thermocline/python/` source; re-`pip install -e` if it drifted. Same once `seamount/describe-forge/.venv` is created.

</specifics>

<deferred>
## Deferred Ideas

- **Forge pubkey rotation protocol** — D-01 chose TOFU; rotation = new channel. A "trust rotation" workflow (re-fetch + audit-recorded re-trust event) is a future capability — fits the Photophore spec v0.2 "channel re-key" line of work; capture for next milestone, not this one.
- **Auto-retry policy with backoff for retryable subcodes** — D-03 chose no auto-retry; advisory `retryable: bool` only. A future "policy-engine-as-supervisor" workflow could retry transparently for `AUDIT_FAILED_PRE` / `TRANSPORT_TIMEOUT`. Out of v0.1 scope; sovereign always decides for now.
- **Daemon mode for Photophore** — currently every CLI invocation reloads keystore + classifier rules. A long-running daemon would reduce per-dispatch latency. Out of v0.1 (sovereign-node-per-user CLI mental model; Phase 2 D-09 stated this explicitly).
- **Conformance harness against third-party (non-reference) forges** — Plan 03-03 only runs the harness against pi-forge and describe-forge. Running it against external implementations as part of CI / a public certification badge is a Phase 4 + post-v0.1 milestone concern.
- **`pi-forge job` support** — explicit Out of Scope per PROJECT.md (deferred to spec v0.2 / next milestone).
- **Job-envelope dispatch path in Photophore** — same — task only in v0.1.

### Reviewed Todos (not folded)

None — no todos matched the phase per `gsd-sdk query todo.match-phase 3`.

</deferred>

---

*Phase: 03-photophore-dispatch-seamount-upgrade-the-integration-phase*
*Context gathered: 2026-05-11*
*Auto-mode pass cap: this file is the single pass; no re-passes per `workflows/discuss-phase/modes/auto.md`.*
