# Phase 2: Photophore Privacy Primitives + Foundations - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-09
**Phase:** 02-photophore-privacy-primitives-foundations
**Areas discussed:** Audit log SQLite schema, Channel record persistence, Path-rules config, Sync vs async API surface, Photophore CLI conventions

---

## Audit log SQLite schema

### Q1.1 — Table layout

| Option | Description | Selected |
|--------|-------------|----------|
| A — Denormalized | Single `entries` table with indexed metadata columns + `payload TEXT` JSON column. AUDIT-05 filters via indexed columns + JSON1 expressions. | ✓ |
| B — Normalized | `entries` header + per-event-type detail tables (channel_events, dispatch_events, receipt_events) joined by entry_id. | |
| C — Hybrid | `entries` header + `entry_indexes` shadow table with (entry_id, key, value) triples for queryable extensibility. | |

**User's choice:** A
**Notes:** SQLite 3.46+ JSON1 assumed available. Recommended starting point for spec compliance — single-table walk for AT-A6 chain integrity is the simplest verifier loop; export to JSON Lines is almost free.

### Q1.2 — Query API return type

| Option | Description | Selected |
|--------|-------------|----------|
| A — Typed dataclasses only | `query()` returns `list[AuditEntry]`; CLI `--json` uses `dataclasses.asdict`. | |
| B — Raw dicts only | `query()` returns `Iterator[dict]` matching JSON Lines export shape. | |
| C — Both (typed wrapper over raw rows) | Internal `_query_rows()` returns dicts; public `query()` wraps with typed dataclasses. Property test asserts round-trip. | ✓ |

**User's choice:** C
**Notes:** Phase 3 dispatch needs typed entries to enforce DISP-03 (verify-before-append); CLI/export need a fast streaming-friendly path. Streaming question for large logs deferred — list return is fine for v0.1.

### Q1.3 — Chain hash domain

| Option | Description | Selected |
|--------|-------------|----------|
| A — Whole-entry canonical-JSON | input = `canonicalize({all fields except entry_hash})`; uses Phase 1's existing `canonicalize`. | ✓ |
| B — Header-only with payload digest | input = `canonicalize({header + payload_hash})`; enables future archival/redaction without breaking chain. | |
| C — Tuple-encoded | input = length-prefixed concat of fields; no JCS dependency for cross-language verifiers. | |

**User's choice:** A
**Notes:** `algo_version="blake3-v1"` encodes both hash + domain. Forward archival/redaction can be addressed via `blake3-v2` per AUDIT-02 dispatch from day 1 — do not speculatively build B.

---

## Channel record persistence

### Q2.1 — Where the channel record lives

| Option | Description | Selected |
|--------|-------------|----------|
| A — Pure keystore + index entry | All records in keyring; one `_index` keyring entry holds JSON array of channel_ids. List = O(N) keyring round-trips. | |
| B — Hybrid | Full record in keyring; parallel `channels` SQLite table mirrors queryable metadata. | |
| C — Three-store | Keyring (source of truth) + separate `channels.db` SQLite metadata index + `audit.db` (per AUDIT-01). Three discrete files, three responsibilities. | ✓ |

**User's choice:** C
**Notes:** Drift recovery = keystore-as-truth (rebuild `channels.db` from keystore on startup mismatch). Trust-store separation from audit log mandate (CHAN-04) honored to the letter.

### Q2.2 — Keystore namespace + atomic write ordering

| Option | Description | Selected |
|--------|-------------|----------|
| A — Audit-first | audit(pre) → keystore.set → channels.db.upsert → audit(post). Two audit entries per op. | |
| B — Audit-as-commit | keystore.set → channels.db.upsert → audit.append (single entry as commit point). | |
| C — Three-step with reconciliation | keystore.set → audit.append → channels.db.upsert. Halt-on-mismatch at startup; index rebuilt from keystore on drift. | ✓ |

**User's choice:** C
**Notes:** Single audit entry per channel op (cleaner audit log). Keystore-first ordering reflects "trust store is authoritative." Namespace `photophore.channel` service / `_index` sentinel locked. Mechanical sub-decisions folded without asking: channel_id = UUIDv4; state machine in `Channel.transition_to()` raising `ChannelStateError`; ceiling raise/lower = distinct audit event types per CHAN-03.

---

## Path-rules config

### Q3.1 — Format and location

| Dimension | Options | Selected |
|-----------|---------|----------|
| Format | YAML / TOML | YAML (✓) |
| Location | A — Single global (`~/.config/photophore/rules.yaml` + `--rules` override) / B — CWD-walking with global fallback / C — Single global with hard error if missing | A (✓) |
| Reload | Load-per-invocation / Hot-reload daemon | Load-per-invocation (✓) |
| Catch-all enforcement | Loader-time hard refusal / Validator pass | Loader-time refusal (✓) |

**User's choice:** A (with lean defaults: YAML, load-per-invocation, loader-time refusal)
**Notes:** YAML aligns with Phase 1 D-04 (conformance manifest format — same parser). XDG-default location matches sovereign-node mental model. CLI `--rules` covers test/preview without conflating machine config with project config. CWD-walking deferred. Mechanical: rule schema = `{pattern, tier, reason}`, ordered list, first-match-wins; `reason` is freeform string surfacing in classifier output.

---

## Sync vs async API surface

### Q4.1 — How async appears in Phase 2 vs Phase 3

| Option | Description | Selected |
|--------|-------------|----------|
| A — Sync everywhere; Phase 3 wraps | All Phase 2 APIs sync; Phase 3 dispatch wraps blocking calls with `asyncio.to_thread` everywhere it touches Phase 2. | |
| B — Async everywhere from day one | All Phase 2 APIs `async def`; `aiosqlite`; `pytest-asyncio` everywhere. | |
| C — Sync core + thin async shim in Phase 3 | Phase 2 sync; Phase 3 ships `photophore.dispatch.aio` shim (~20 LOC) wrapping the few Phase 2 calls dispatch awaits. | ✓ |

**User's choice:** C
**Notes:** Stdlib `sqlite3` only; no `aiosqlite`. Phase 2 has zero `async def` and runs without `pytest-asyncio`. Phase 3 owns the boundary code in its own `dispatch.aio` module.

---

## Photophore CLI conventions

### Q5.1 — Output mode default and flag

| Option | Description | Selected |
|--------|-------------|----------|
| A — `--json` boolean flag, human default | Matches `gh`, `pip`, `vercel`. Per-subcommand JSON-vs-JSONL distinction by nature. | |
| A with twist — `--json` + audit-jsonl | Same as A but `audit query`/`audit export` emit JSON Lines under `--json`; other subcommands emit single JSON document. | ✓ |
| B — `--format=human|json|jsonl` | Explicit three-way enum. | |
| C — Two binaries / env var | `photophore.json` separate binary or `PHOTOPHORE_JSON=1` env var. | |

**User's choice:** A with audit-jsonl twist
**Notes:** No `--format=` enum needed. Mechanical CLI defaults folded without asking: single `photophore` entry point with `click` command groups; `--help` everywhere; structured exit codes per error class (1=generic, 2=config, 3=audit-chain, 4=classifier, 5=keystore; Phase 3 reserves 6=dispatch).

---

## Claude's Discretion

User did not push back on any of the following — planner has flexibility:

- Exact module layout under `photophore/python/src/photophore/` (recommendation in CONTEXT.md `<decisions>`).
- Shadow content-type strategy: closed enum + match vs registry pattern (v0.1 ships the same 6 either way).
- `AnchorTarget` Protocol method shape (suggestion: `def anchor(entry) -> AnchorReceipt | None` with no-op default).
- `photophore policy preview` output detail level (minimum = `result_policy` JSON; richer view is planner discretion).
- SQLite trigger shape for AUDIT-01 append-only enforcement.
- Photophore-side conformance fixtures AT-A1..A6 — fixture authorship Phase 2; behavioral wiring may phase-tag forward to Phase 3 per Phase 1 D-04 manifest convention.
- `pyproject.toml` exact metadata, dependency pin format, dev extras set.

## Deferred Ideas

- Daemon-mode rules-config hot-reload (future milestone)
- CWD-walking rules discovery `.photophore/rules.yaml` (future milestone)
- Streaming `audit query` for large logs (refactor when materialization becomes a problem)
- Phase 4 CLI-06 audit-of-CLI-invocations schema (Phase 4 scope)
- Phase 4 CONF-06 `print(` lint + logging redacting filter (Phase 4 scope)
- Apple Silicon Secure Enclave coverage (Phase 4 testing)
- Photophore spec patches discovered during Phase 2 — land in-phase as Phase 1 did (THERMO-01 pattern)
