# Phase 2: Photophore Privacy Primitives + Foundations - Context

**Gathered:** 2026-05-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Build Photophore's privacy-critical components in `photophore/python/` (greenfield — sibling repo to `thermocline/`). Audit log (the chained, append-only foundation) and channel registry (trust store via platform keystore) land first because every other component writes through them. Classifier, shadow generator, and policy authoring follow as pure functions. The CLI ships its non-dispatch surface (`channel`, `audit`, `classify`, `policy preview`) so users can interact with the engine end-to-end before dispatch arrives in Phase 3.

This phase ships **no network code, no dispatch coordinator, and no forge-side logic**. Phase 3 wires those onto the foundations laid here.

Locked carry-forwards from Phase 1:
- Pydantic v2 envelope types from `thermocline-py`; canonical-JSON via `thermocline.canonicalize`
- `IdentityProvider` Protocol, `BrineProvider`, `Receipt` sentinel-only construction (Phase 1 D-01)
- Schema-generation pipeline with CI drift gate (Phase 1 D-02) — applies to any photophore-side schemas (e.g., audit JSON Lines export schema, rules-config schema)
- `Sensitive[T]` discipline (Phase 1 D-03) — applies to any photophore field holding content bytes
- Conformance manifest YAML schema (Phase 1 D-04) — Phase 2 ships AT-A1..A6 fixtures under the same scheme
- Tech stack: Python 3.11+, `python-keyring` 25.x, BLAKE3 0.4+ with `algo_version="blake3-v1"`, `click` 8.x, stdlib `sqlite3` 3.46+ (JSON1 assumed available), `pytest` 8.x + `hypothesis` 6.x, `mypy --strict`, `ruff`
- Trust store separate backing store from audit log (CHAN-04, AUDIT-01) — non-negotiable
- `isinstance` keystore probe (Phase 1 BL-03) — channel store reuses the same probe via `BrineProvider`/keystore-availability helper

</domain>

<decisions>
## Implementation Decisions

### Audit log SQLite schema (Plan 02-01)

- **D-01 (Table layout — denormalized):** Single `entries` table with indexed metadata columns (`id`, `algo_version`, `prev_hash`, `entry_hash`, `event_type`, `channel_id NULLABLE`, `envelope_id NULLABLE`, `timestamp`) plus a `payload TEXT` column holding canonical-JSON of the event-specific fields. Queries filter on indexed columns; payload parsed on read. AUDIT-05's spec-mandated filters (channel, node, tier, date range, shadow ID, envelope ID, receipt status) are satisfied by indexed columns + a small set of JSON1 expressions for shadow_id and tier-per-block lookups.

  **Rationale:** Single-table walk for AT-A6 chain integrity check is the simplest verifier loop; export to JSON Lines is a `SELECT * + payload concat` — almost free. SQLite triggers enforcing append-only (AUDIT-01) live on this one table. Schema migrations rare. Spec-aligned for cross-impl ports (any `thermocline-py`-aware verifier already canonicalizes).

  **Acceptance test:** `audit.append({event_type:"channel.created", ...})`; `audit.query()` returns the entry with `prev_hash == previous entry's entry_hash`; tampering with any byte of `payload` invalidates the chain on next read.

- **D-02 (Query API surface — typed wrapper over raw rows):** Internal `_query_rows() -> Iterator[dict[str, Any]]` returns the canonical JSON-Lines-shape dicts (single source of truth for export). Public `query() -> list[AuditEntry]` wraps that with typed dataclasses where `AuditEntry.event` is a `Union[ChannelEvent, DispatchEvent, ReceiptEvent, CliEvent]` typed by `event_type`. CLI `audit query --json` and `audit export` consume `_query_rows()` directly; Phase 3 dispatch coordinator consumes typed `query()` to enforce DISP-03 (verify-before-append).

  **Rationale:** Phase 3 needs typed entries to make DISP-03's verify-before-append type-safe; CLI/export need a fast streaming-friendly path; spec-aligned JSON Lines is the wire format. A property test asserts `from_dict(asdict(entry)) == entry` for every event type so the two paths cannot drift.

  **Acceptance test:** for each event type, generate a typed dataclass, serialize via `asdict`, parse back via `from_dict`, assert equality.

- **D-03 (Chain hash domain — whole-entry canonical-JSON):** `entry_hash = blake3(canonicalize({all entry fields except entry_hash itself}))`. The `algo_version="blake3-v1"` field encodes both the hash function AND the domain rule. A future `algo_version="blake3-v2"` may change either or both; verifier dispatches on `algo_version` per AUDIT-02 from day 1.

  **Rationale:** Simplest possible reading; uses Phase 1's existing `canonicalize` (no new code path); cross-language ports already have JCS via the spec. Forward archival/redaction needs (the only motivation for header-only domain B) can be addressed in `blake3-v2` if v0.2+ requires; do not speculatively build.

  **Acceptance test:** Hypothesis property test: arbitrary entry → `entry_hash == blake3(canonicalize(entry_minus_hash))`; tampering any single byte invalidates.

### Channel record persistence (Plan 02-01)

- **D-04 (Three-store model):** Trust store source-of-truth = `python-keyring` (one entry per channel under service `photophore.channel`, username = channel_id, value = canonical-JSON of the full record). Channel metadata index = a separate SQLite file `channels.db` (NOT the audit DB) holding `(id, remote_node, ceiling, state, key_scheme, created_at, updated_at)` for `list`/`show` queries. Audit log = its own `audit.db` (per D-01..D-03). Three discrete stores, three files, three responsibilities.

  **Rationale:** CHAN-04 satisfied to the letter — trust-store backing and audit DB are different stores AND different files. `channels.db` is a derived projection of the keystore; the keystore is authoritative. AT-A1 (channel impersonation) framing is cleanest under this split: the audit log can never leak channel data via shared filesystem with the trust store.

- **D-05 (Drift recovery — keystore-as-truth):** On startup, `photophore.channels.bootstrap()` walks all keyring entries under service `photophore.channel`, compares against `channels.db`, and rebuilds the index from keystore if any drift detected. The keystore is always authoritative; an unaudited channel (record in keystore but no `channel.created` event in audit log) is a hard halt — node refuses to operate, surfaces the diagnostic, and waits for manual reconciliation.

  **Rationale:** Keystore is the trust store mandate; audit log is a witness, not a source. Halt-on-mismatch is conservative and surfaces tampering / partial-write damage explicitly.

- **D-06 (Keystore namespace):** Service = `photophore.channel`; usernames are channel_ids (UUIDv4); plus a sentinel `_index` username holding `[]` (empty JSON array) when no channels exist, or unused if the index is rebuilt from keystore-walk on startup. Decision deferred to planner: if the bootstrap walk is reliably fast (< 100ms for 1k channels), drop the `_index` sentinel; if slower or platform-dependent, keep it.

- **D-07 (Atomic write ordering for channel ops — three-step):** Per CHAN-05 ("audit entry produced before operation reported successful"), channel create/suspend/ceiling-change/close uses three steps in this exact order: (1) `keystore.set(channel_record)`, (2) `audit.append(channel_event)`, (3) `channels.db.upsert(index_row)`. CLI returns success after step 3. If step 2 fails after step 1, node halts at next op (unaudited channel detected at startup). If step 3 fails after step 2, startup detects index-vs-keystore drift and rebuilds the index per D-05.

  **Rationale:** Single audit entry per channel op (cleaner audit log; clearer reads). Keystore-first ordering reflects "trust store is authoritative." Index-as-derived means index rebuild is always safe. Halt-on-mismatch surfaces real damage instead of papering over it.

  **Mechanical sub-decisions (folded — not user-asked):**
  - channel_id = UUIDv4 (`uuid.uuid4()`) — matches shadow_id pattern, stdlib only
  - State machine validated in `Channel.transition_to(new_state)` raising `ChannelStateError` on invalid transition
  - Trust ceiling raise vs lower = distinct audit event types per CHAN-03 (`channel.ceiling_lowered`, `channel.ceiling_raised`)

### Path-rules config (Plan 02-02)

- **D-08 (Format = YAML; load-per-invocation; loader-time refusal):** Rules config is YAML (matches Phase 1 D-04 conformance manifest format — same parser, same idiom). Loaded fresh on every CLI invocation (no daemon). Catch-all enforcement: `RulesConfigError("missing mandatory '**' → 'local' catch-all")` raised at load time before any classify call returns; CLASS-03 is non-negotiable.

- **D-09 (Location precedence — single global):** Default location is `~/.config/photophore/rules.yaml` (`XDG_CONFIG_HOME/photophore/rules.yaml` if `XDG_CONFIG_HOME` is set). CLI flag `--rules <path>` overrides for testing/preview. No CWD-walking, no per-project config in v0.1 — sovereign-node-per-user is the mental model. Operations that don't require classification (`channel`, `audit query/export/verify`) do not load the rules file. Operations that do (`classify`, `policy preview`, Phase 3 `dispatch`) hard-error if no rules file is present AND no `--rules` flag was passed.

- **D-10 (Rule schema):** Ordered list of `{pattern: glob, tier: local|shared|public, reason: str (freeform)}`; first-match-wins. The `reason` string surfaces in classifier output as `path_rule:<reason or pattern>` per CLASS-05. Mandatory final entry: `{pattern: "**", tier: local, reason: "default"}`.

  **Rationale:** YAML aligns with D-04. XDG-default location is the simplest single-source-of-truth and matches sovereign-node mental model. CLI flag covers test/preview without conflating machine config with project config. Loader-time hard refusal is the only acceptable enforcement for CLASS-03 since runtime fallthrough would silently classify unmatched content as something other than `local` — exactly the "false positive" mode the spec forbids.

### API surface async-ness (Plan 02-01..02-03)

- **D-11 (Sync Phase 2 + thin async shim in Phase 3):** All Phase 2 public APIs are sync `def`: `audit.append/query/export/verify`, `channels.create/list/show/transition/set_ceiling`, `classify(content)`, `shadow.generate(content, content_type)`, `policy.author(channel, envelope_draft)`. SQLite via stdlib `sqlite3` (no `aiosqlite`). CLI is sync-native. Phase 3 ships a small `photophore.dispatch.aio` shim (~20 LOC, in dispatch's module) that exposes async wrappers for the few Phase 2 functions dispatch awaits (`audit_append_async`, etc.) using `asyncio.to_thread`. The shim is Phase 3 scope — Phase 2 does not pre-build it.

  **Rationale:** Sync core keeps domain logic readable, testable, dependency-light. Pure-CPU functions (classifier, shadow) shouldn't be `async def`. Phase 3 dispatch is the only async surface and owns its own boundary code.

  **Acceptance test:** Phase 2 has zero `async def` and zero `aiosqlite` import; full Phase 2 test suite runs without `pytest-asyncio`.

### CLI conventions (Plan 02-01..02-03)

- **D-12 (`--json` flag with audit-jsonl twist):** CLI default = human-readable; `--json` flag flips to machine-parseable. `audit query` and `audit export` emit JSON Lines under `--json` (one entry per line, streaming-friendly); all other subcommands emit a single JSON document. CLI-06's audit-trail schema records `output_mode: "human"|"json"`. No `--format=` enum; per-subcommand JSON-vs-JSONL distinction is by nature.

- **D-13 (Single `photophore` entry point with click groups):** Per CLAUDE.md tech stack and Phase 1 idioms, single binary `photophore` exposed via `pyproject.toml` `[project.scripts]`, with `click.Group` per area: `photophore channel|audit|classify|policy <subcmd>`. Each group has its own subcommands (e.g., `photophore channel new|list|show|suspend|close|set-ceiling`). `--help` everywhere; non-zero exit on any error.

- **D-14 (Structured exit codes per error class):**
  - `0` = success
  - `1` = generic error (last-resort)
  - `2` = config error (rules file missing/malformed; channel record corrupt)
  - `3` = audit chain integrity failure (chain broken, prev_hash mismatch)
  - `4` = classifier error (content unreadable, encoding failure)
  - `5` = keystore error (keystore unavailable, channel record not found in keystore)
  - Phase 3 reserves `6` for dispatch errors (RECEIPT_INVALID, AUDIT_FAILED, etc.).

  **Rationale:** Predictable exit codes make CI integration trivial; CONF-07 ops docs reference these directly. Audit-chain failure (3) is distinct from generic error (1) because it signals a privacy-critical incident requiring forensic followup.

### Claude's Discretion

The following are not user-locked — planner/executor has flexibility within the constraints above:

- Exact module layout under `photophore/python/src/photophore/` — recommended: `core/` (envelope re-exports + shared types), `audit/` (schema, append, query, export, verify, anchor), `channels/` (record types, lifecycle, bootstrap), `classifier/` (rules loader, classifier engine, default fn), `shadow/` (per-content-type strategies + irreversibility test), `policy/` (result_policy authoring), `cli/` (click groups). Sub-module shapes within each are planner discretion.
- Shadow content-type strategy: closed enum + match statement vs registry pattern. v0.1 ships the spec-mandated 6 (`document`, `conversation`, `credential`, `file`, `identity`, `code`); planner may choose either internal shape so long as adding a 7th type in v0.2 is a localized change.
- `AnchorTarget` Protocol surface (AUDIT-07): planner picks the method shape (suggestion: `def anchor(self, entry: AuditEntry) -> AnchorReceipt | None` with no-op default returning `None`); v0.1 ships only the Protocol + no-op default + a smoke test.
- Policy preview output detail level (`photophore policy preview`): minimum is the `result_policy` JSON; planner may add a synthetic envelope view showing tier-0 stripped, tier-1 → shadow placeholder, tier-2 visible if it improves the dev loop.
- SQLite trigger shape for AUDIT-01 append-only enforcement: planner picks (a `BEFORE DELETE` raising `RAISE(ABORT, ...)` plus a `BEFORE UPDATE` raising the same, both on `entries`).
- Photophore-side conformance fixtures (AT-A1..A6) — fixture authorship effort is Phase 2 scope; behavioral wiring of A1..A6 happens here OR is phase-tagged forward to Phase 3 per Phase 1 D-04 manifest convention.
- `pyproject.toml` exact metadata, dependency pin format, `[project.optional-dependencies] dev` set — planner picks; matches `thermocline/python/pyproject.toml` style.

### Folded Todos

None — `gsd-sdk query todo.match-phase 2` returned 0 matches.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Specs (source of truth)
- `photophore/README.md` — Photophore spec v0.3.0-draft (channels §"Channels", §"Channel Lifecycle"; classifier §"Classifier Specification"; shadows §"Shadows" + §"Shadow Generation Quality"; result policy §"Result Policy Authorship"; audit log §"The Audit Log" + §"Properties" + §"What Each Entry Records" + §"The Three-Ring Storage Model" + §"The Privacy Receipt"; threat model §"Attack Surfaces and Mitigations" — AT-A1..A6; trust store / audit storage §"The Trust Store and Audit Storage"; design constraints §"Design Constraints").
- `thermocline/README.md` — Thermocline spec v0.3.0-draft (envelope contract; AT-C1..C6; the 5-role architecture).
- `seamount/README.md` — Seamount spec v0.3.0-draft (forge role context for AT-A6 / receipt verification semantics; describe-forge / pi-forge integration is Phase 3 scope).

### Planning hub
- `thermocline/.planning/PROJECT.md` — Suite-wide project definition, key decisions table, constraints
- `thermocline/.planning/REQUIREMENTS.md` §"Photophore Channels" + §"Photophore Classification" + §"Photophore Shadow Generation" + §"Photophore Result Policy Authoring" + §"Photophore Audit Log" + §"Photophore CLI" — CHAN-01..06 + CLASS-01..06 + SHADOW-01..06 + POLICY-01..03 + AUDIT-01..08 + CLI-01,02,04,05 (Phase 2 scope; CLI-03/06/07 are Phase 3/4)
- `thermocline/.planning/ROADMAP.md` §"Phase 2" — phase goal, success criteria SC1..SC5, plan list (02-01, 02-02, 02-03)
- `thermocline/.planning/STATE.md` — current position, accumulated decisions

### Phase 1 carry-forward (mandatory pre-reading — these decisions still apply)
- `thermocline/.planning/phases/01-thermocline-py-foundations/01-CONTEXT.md` §"Implementation Decisions" — D-01 Receipt sentinel, D-02 schema-generation pipeline, D-03 `Sensitive[T]` discipline, D-04 conformance manifest schema. All four carry forward unchanged.
- `thermocline/.planning/phases/01-thermocline-py-foundations/01-LEARNINGS.md` — full Phase 1 learning corpus (12 decisions, 10 lessons, 11 patterns, 8 surprises). Especially: lookup-order invariant + `_PUBKEY_PREFIX` pattern (BL-01), `isinstance` keystore probe over substring (BL-03), real-fixture-from-disk regression discipline.
- `thermocline/CHANGELOG.md` v0.3.1 section — cross-implementation contract record for any photophore-side spec patches discovered during Phase 2.

### Research bundle
- `thermocline/.planning/research/STACK.md` — locked stack (Python 3.11+, Pydantic 2.7+, PyNaCl 1.5+, `rfc8785`, `python-keyring` 25, BLAKE3 0.4+, `mypy --strict`, `ruff`)
- `thermocline/.planning/research/ARCHITECTURE.md` — repo layout, module boundaries, suite-wide diagram (network-isolation contract for `photophore.{classifier,shadow,policy,audit,channels,core}`)
- `thermocline/.planning/research/PITFALLS.md` Pitfall 1 (audit chain integrity), Pitfall 2 (classifier default), Pitfall 3 (shadow caching), Pitfall 4 (`Sensitive` discipline — Phase 1 already shipped, applies here), Pitfall 6 (trust store co-location), Pitfall 9 (no in-process keys), Pitfall 11 (json.dumps), Pitfall 12 (Pydantic v1 patterns)
- `thermocline/.planning/research/FEATURES.md` — feature scope per repo
- `thermocline/.planning/research/SUMMARY.md` — executive summary of all research

### External standards
- **RFC 8785 (JCS)** — JSON Canonicalization Scheme, the only canonical-JSON path. Used for audit chain hash domain (D-03). Implemented via `thermocline.canonicalize`.
- **BLAKE3** (https://github.com/BLAKE3-team/BLAKE3) — chain hash properties; we use the `blake3` Python binding tagged via `algo_version="blake3-v1"` for migration safety.
- **Pydantic v2 documentation** — `model_dump(mode='json')`, custom serializers, `ConfigDict(extra="forbid", frozen=True)`. v2 patterns only; `.dict()` / `.json()` are forbidden by Pitfall 12.
- **`python-keyring` 25.x** — backend selection, `keyring.backends.fail.Keyring` / `null.Keyring` `isinstance` probe (Phase 1 BL-03), service/username conventions.
- **`click` 8.x** — command groups, parameter types, JSON output handling.
- **SQLite 3.46+ JSON1 extension** — for derived JSON-payload lookups (e.g., shadow_id, tier-per-block) per D-01.

### Phase 1 reference impl (in-tree — read for patterns)
- `thermocline/python/src/thermocline/identity.py` — `BrineProvider` pattern (keystore namespace, `isinstance` probe, `register_public_key` cross-role API, `generate`/`rotate` clobber-safe pattern). Channel keystore code reuses these idioms.
- `thermocline/python/src/thermocline/canonical.py` — `canonicalize()` for audit chain hash domain.
- `thermocline/python/src/thermocline/envelope.py` — Pydantic v2 envelope types Phase 2 imports.
- `thermocline/python/src/thermocline/sensitive.py` — `Sensitive[T]` wrapper Phase 2 applies to any photophore field carrying content bytes.
- `thermocline/python/scripts/build_schemas.py` — schema generation pattern; Phase 2 may add audit JSON Lines schema, rules-config schema using the same idiom.
- `thermocline/python/tests/conftest.py` — `brine_in_memory_keyring` fixture pattern; Phase 2 reuses for channel-store tests.

### Reference implementation to learn from
- `seamount/pi-forge/server.py` — Flask handler shape, request/response flow, structured error envelope construction. Informs but does not constrain Phase 2.
- `seamount/pi-forge/envelope.py` — existing validation idioms (will be replaced by `thermocline-py` in Phase 3); useful for understanding the wire shape Phase 2 receives.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `thermocline/python/src/thermocline/identity.py::_PUBKEY_PREFIX` namespace pattern — Phase 2 channel-store uses `photophore.channel` service + per-channel-id usernames; same `keyring.set_password`/`get_password` ergonomics; same `isinstance(backend, (fail.Keyring, null.Keyring))` startup probe.
- `thermocline/python/src/thermocline/canonical.py::canonicalize()` — used directly for audit chain hash domain (D-03) and any photophore-side signing input.
- `thermocline/python/src/thermocline/sensitive.py::Sensitive` — applied to any photophore field holding content bytes (`ContentBlock.content` already typed; `Shadow.abstraction` may need it depending on planner choice).
- `thermocline/python/tests/conftest.py::brine_in_memory_keyring` — fixture pattern for channel-store tests (real `KeyringBackend` subclass, deliberately not named `Keyring`).
- `thermocline/python/scripts/build_schemas.py` — schema generation pipeline; Phase 2 extends with photophore-specific schemas (audit JSON Lines export schema, rules-config JSON schema for editor tooling).
- `thermocline/python/scripts/check_no_json_dumps.py` — AST-based lint for canonical-JSON discipline; Phase 2 inherits this rule (any photophore code that signs/hashes uses `canonicalize`, never `json.dumps`).

### Established Patterns
- **Spec-mandated module separation** (per `research/ARCHITECTURE.md`): `photophore.{audit, channels, classifier, shadow, policy, cli, core}`. **No HTTP imports** anywhere in `photophore.{classifier, shadow, policy, audit, channels, core}` — enforced by Phase 3 AST lint (DISP-05), but Phase 2 must respect it from the first commit.
- **Pydantic v2 only**: `pydantic>=2.7,<3.0` pinned in `photophore/python/pyproject.toml`; CI lint flags `.dict(` and `.json()` v1 patterns (Pitfall 12).
- **`mypy --strict` + `ruff` + `pip-audit`** in CI from day 1, matching `thermocline/python/pyproject.toml` config.
- **Real-fixture-from-disk regression discipline** (Phase 1 BL-04 lesson): tests load conformance fixtures via `Path(__file__).resolve().parents[N]` — synthetic in-test envelopes are an anti-pattern.
- **Versioned hash dispatch**: `algo_version="blake3-v1"` field + verifier dispatch per AUDIT-02 from day 1, even though only one version exists in v0.1 (mirrors Phase 1's `KeyScheme` enum + verifier dispatch in `thermocline.identity`).

### Integration Points
- **Phase 3 dispatch (`photophore.dispatch`)** imports `from photophore import (audit, channels, classifier, shadow, policy)` and orchestrates the 9-step flow. Phase 2 API stability matters — breaking changes after Phase 2 cascade across Phase 3 (dispatch) AND Phase 4 (hardening tests).
- **Phase 3 forge upgrade (`seamount/pi-forge`)** — `pi-forge` continues to use `thermocline-py` (Phase 1) for envelope handling; it does NOT import from `photophore` (forges are receivers, not policy engines).
- **`photophore.dispatch.aio` (Phase 3, ~20 LOC)** — async shim wrapping `audit.append/query/verify` and `channels.transition_to` calls with `asyncio.to_thread`. Phase 2 does NOT pre-build this; Phase 3 owns it.

### Network-isolation contract (DISP-05, enforced via AST lint in Phase 3)
- `photophore.{audit, channels, classifier, shadow, policy, core, cli}` — MUST NOT import `httpx`, `requests`, `aiohttp`, `urllib.request`, or any HTTP client. Phase 2 must respect this from the first commit; Phase 3 lands the AST lint as a CI gate, but the rule is in effect from now.

</code_context>

<specifics>
## Specific Ideas

- **Audit entries table example schema** (illustrative only — planner finalizes):
  ```sql
  CREATE TABLE entries (
      id TEXT PRIMARY KEY,                    -- UUIDv4 entry id
      algo_version TEXT NOT NULL,             -- "blake3-v1"
      prev_hash TEXT NOT NULL,                -- BLAKE3 hex of previous entry's entry_hash; "" for chain head
      entry_hash TEXT NOT NULL,               -- BLAKE3 hex of canonicalize(entry minus this column)
      event_type TEXT NOT NULL,               -- "channel.created", "channel.suspended", "dispatch.pre", "dispatch.receipt", ...
      channel_id TEXT,                        -- NULLABLE — non-channel events may not carry one
      envelope_id TEXT,                       -- NULLABLE — non-dispatch events may not carry one
      timestamp TEXT NOT NULL,                -- ISO 8601 UTC (Z suffix)
      payload TEXT NOT NULL                   -- canonical-JSON of event-specific fields
  );
  CREATE INDEX idx_entries_channel ON entries(channel_id);
  CREATE INDEX idx_entries_envelope ON entries(envelope_id);
  CREATE INDEX idx_entries_timestamp ON entries(timestamp);
  CREATE INDEX idx_entries_event_type ON entries(event_type);
  -- BEFORE DELETE / BEFORE UPDATE triggers RAISE(ABORT, ...) per AUDIT-01
  ```

- **Channel keystore record example shape** (illustrative — JSON value stored under `photophore.channel:<channel_id>`):
  ```json
  {
    "id": "...",
    "local_node": "alice",
    "remote_node": "bob",
    "ceiling": "tier-1",
    "key_scheme": "brine",
    "state": "OPEN",
    "remote_pubkey_hex": "...",
    "created_at": "2026-05-09T12:00:00Z",
    "creator_identity": "alice",
    "description": "..."
  }
  ```

- **Rules-config example shape:**
  ```yaml
  version: 0.1
  rules:
    - pattern: "**/.env*"
      tier: local
      reason: env-credentials
    - pattern: "**/*.pem"
      tier: local
      reason: keys
    - pattern: "docs/**/*.md"
      tier: shared
      reason: shared-docs
    - pattern: "**"
      tier: local
      reason: default
  ```

- **CLI usage examples** (illustrative — planner finalizes):
  - `photophore channel new --remote-node bob --ceiling tier-1 --key-scheme brine`
  - `photophore channel list --json` (single JSON array document)
  - `photophore audit query --channel <id> --json` (JSON Lines, one entry per line)
  - `photophore audit export --since 2026-05-01 --json > export.jsonl`
  - `photophore classify ./docs/ --json`
  - `photophore policy preview --channel <id> --task ./draft.json`

</specifics>

<deferred>
## Deferred Ideas

- **Shadow strategy registry pattern** — explicit "open vs closed" choice deferred to planner (Claude's discretion). v0.1 ships the spec-mandated 6 content types; whether internally a closed enum + match or a registry is shape-only.
- **Daemon-mode rules-config hot-reload** — Phase 2 ships load-per-invocation only. A persistent `photophored` daemon with hot-reload is a future-milestone consideration, not v0.1.
- **CWD-walking rules discovery (`.photophore/rules.yaml`)** — out of scope for v0.1; sovereign-node-per-user model is the v0.1 mental model. Per-project rules can be revisited if v0.2+ adds the use case.
- **`photophore policy preview` synthetic-envelope view** — minimum is `result_policy` JSON only. The fuller "what the wire would look like" view is planner discretion / nice-to-have.
- **SQL `audit query` streaming** — v0.1 returns lists; if early-deployment audit logs grow large enough that materialization is a problem, refactor to iterators. Spec-mandated filters keep result sets small in v0.1.
- **Phase 4 CLI-06 audit-of-CLI-invocations schema** — Phase 2 scope is the CLI surface; Phase 4 wires every CLI subcommand to emit an audit entry recording the operation invoked. The schema for that lives next to D-01 audit table; the wiring is Phase 4.
- **Phase 4 CONF-06 `print(` lint + logging redacting filter** — Phase 2 must respect `Sensitive[T]` `__repr__` discipline from day 1, but the suite-wide CI lint forbidding `print(` and the privacy-aware logging filter both belong in Phase 4.
- **Apple Silicon Secure Enclave coverage** — STATE.md flags this as a blocker requiring physical hardware + signing identity. Phase 2 targets standard Keychain via `python-keyring`; Secure Enclave specifics deferred to Phase 4 testing.
- **Photophore spec patches discovered during Phase 2** — like Phase 1's THERMO-01 evolution, Phase 2 may uncover photophore spec ambiguities. Each lands as a separate commit on `photophore/README.md` (and `photophore/CHANGELOG.md`) in this phase, not deferred.

### Reviewed Todos (not folded)
None — no matching pending todos.

</deferred>

---

*Phase: 02-photophore-privacy-primitives-foundations*
*Context gathered: 2026-05-09*
