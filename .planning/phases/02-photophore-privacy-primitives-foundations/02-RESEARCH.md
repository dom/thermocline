---
phase: "02"
phase_name: "photophore-privacy-primitives-foundations"
generated: "2026-05-09"
sources_consulted:
  - "photophore/README.md (v0.3.0-draft — normative)"
  - "thermocline/.planning/phases/02-photophore-privacy-primitives-foundations/02-CONTEXT.md"
  - "thermocline/.planning/REQUIREMENTS.md"
  - "thermocline/.planning/research/PITFALLS.md"
  - "thermocline/.planning/research/ARCHITECTURE.md"
  - "thermocline/.planning/phases/01-thermocline-py-foundations/01-LEARNINGS.md"
  - "thermocline/thermocline/python/src/thermocline/identity.py (live code)"
  - "thermocline/thermocline/python/src/thermocline/canonical.py (live code)"
  - "thermocline/thermocline/python/src/thermocline/sensitive.py (live code)"
  - "thermocline/thermocline/python/tests/conftest.py (live code)"
  - "thermocline/thermocline/python/src/thermocline/scripts/build_schemas.py (live code)"
  - "thermocline/thermocline/conformance/invalid/MANIFEST.yaml (live)"
  - "SQLite 3.53.0 (verified in venv)"
  - "blake3 1.0.8 (verified via pip index)"
  - "keyring 25.7.0 (verified in venv)"
  - "pydantic 2.13.4 (verified in venv)"
  - "hypothesis 6.152.4 (verified in venv)"
  - "pathspec 1.1.1 (verified via pip index)"
  - "click 8.3.3 (verified via pip index)"
deps_added:
  - "blake3>=1.0.8"
  - "click>=8.3"
  - "pyyaml>=6.0"
  - "pathspec>=1.1.1"
---

# Phase 2: Photophore Privacy Primitives + Foundations — Research

**Researched:** 2026-05-09
**Domain:** Photophore privacy primitives — audit log, channels, classifier, shadow, policy, CLI
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions (D-01 through D-14)
- D-01: Single `entries` table, denormalized, JSON `payload` column, indexed metadata. SQLite triggers enforce append-only.
- D-02: `query() -> list[AuditEntry]` wraps `_query_rows() -> Iterator[dict]`. Property test: `from_dict(asdict(entry)) == entry`.
- D-03: `entry_hash = blake3(canonicalize(entry_minus_entry_hash))`. `algo_version="blake3-v1"` from day 1.
- D-04: Three discrete stores: keystore (trust store), `channels.db` (index), `audit.db` (audit log). Never co-located.
- D-05: Drift recovery = keystore-as-truth. Unaudited channel = halt-on-startup.
- D-06: Keystore namespace `photophore.channel` service + channel_id usernames. `_index` sentinel deferred to planner.
- D-07: Three-step write ordering: keystore.set → audit.append → channels.db.upsert. channel_id = UUIDv4. State machine in `Channel.transition_to()`.
- D-08: Path-rules = YAML, load-per-invocation, loader-time refusal of missing `**` catch-all.
- D-09: Default `~/.config/photophore/rules.yaml` (XDG override), `--rules` CLI flag. No CWD-walking.
- D-10: Ordered rule list `{pattern, tier, reason}`, first-match-wins, mandatory `**` → `local` final entry.
- D-11: All Phase 2 APIs are sync `def`. Zero `async def`, zero `aiosqlite`. Full suite runs without `pytest-asyncio`.
- D-12: `--json` flag. `audit query`/`audit export` emit JSON Lines; other subcommands emit single JSON document.
- D-13: Single `photophore` binary. `click.Group` per area: `channel|audit|classify|policy`.
- D-14: Exit codes: 0=success, 1=generic, 2=config, 3=audit-chain-integrity, 4=classifier, 5=keystore.

### Claude's Discretion
- Exact module layout under `photophore/python/src/photophore/` (recommended: `core/`, `audit/`, `channels/`, `classifier/`, `shadow/`, `policy/`, `cli/`)
- Shadow content-type strategy: closed enum + match OR registry pattern
- `AnchorTarget` Protocol surface shape
- `policy preview` output detail level
- SQLite trigger shape (BEFORE DELETE + BEFORE UPDATE)
- AT-A1..A6 fixture authorship timing (Phase 2 or phase-tagged to Phase 3)
- `pyproject.toml` exact metadata, pin format, dev optional-dependencies

### Deferred Ideas (OUT OF SCOPE)
- Shadow strategy registry open/closed choice (shape only — planner decides)
- Daemon-mode hot-reload rules config
- CWD-walking rules discovery
- `policy preview` synthetic-envelope view
- SQL audit query streaming
- Phase 4 CLI-06 audit-of-CLI-invocations
- Phase 4 CONF-06 print lint + logging redacting filter
- Apple Silicon Secure Enclave coverage
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CHAN-01 | Channel creation with UUID, identity, ceiling, key_scheme, timestamp, description | D-07 write ordering; keystore namespace pattern |
| CHAN-02 | PROPOSED→OPEN→SUSPENDED→CLOSED state machine; CLOSED terminal; IDs never reused | `Channel.transition_to()` raising `ChannelStateError` |
| CHAN-03 | Trust ceiling monotonically decreasing on suspicion; raise = distinct audit event | Distinct `channel.ceiling_raised`/`channel.ceiling_lowered` event types |
| CHAN-04 | Channel registry backed by `python-keyring`; never co-located with audit DB | D-04 three-store model verified |
| CHAN-05 | Every channel op produces audit entry BEFORE reported successful | D-07 write ordering locks this in |
| CHAN-06 | `photophore channel list`/`show` with JSON + human output | D-12 `--json` flag pattern |
| CLASS-01 | Explicit Tag > Path Rule > Classifier strict priority | Single `classify()` with explicit branch order |
| CLASS-02 | Explicit tags `@photophore:local/shared/public` parsed from content | Regex parser on content text |
| CLASS-03 | Path rules must end with `**` → `local`; refuse to load without it | Loader-time `RulesConfigError` |
| CLASS-04 | Rule-based classifier defaults to `local`; detects credentials/PII/sensitive files | `default_tier()` named function |
| CLASS-05 | Every classification produces `(tier, reason)` | Reason string format: `explicit_tag`, `path_rule:<pattern>`, `classifier:<rule>`, `classifier:default` |
| CLASS-06 | `default_tier()` is named function returning `Tier.LOCAL`; Hypothesis property test | Property test: arbitrary unmatched content → `(LOCAL, CLASSIFIER_DEFAULT)` |
| SHADOW-01 | Shadows generated at dispatch time only; fresh per dispatch | No caching by design |
| SHADOW-02 | Shadow = {shadow_id (UUIDv4), content_type, abstraction, relevance (0.0–1.0), tier=1} | `str(uuid.uuid4())` pattern verified |
| SHADOW-03 | Per-content-type abstraction strategies for 6 types per v0.3 quality table | Signals table verified from spec |
| SHADOW-04 | Irreversibility = hard fail; relevance + distinguishability = soft warn to audit | Hard fail aborts dispatch; soft warn continues |
| SHADOW-05 | Tier-0 stripped; tier-1 → shadow; tier-2 passthrough | In shadow.generate() |
| SHADOW-06 | Shadows never cached, persisted, or referenced after dispatch | No shadow corpus accumulates |
| POLICY-01 | `result_policy` authored by issuer; any draft `result_policy` ignored | `policy.author()` ignores draft field |
| POLICY-02 | Policy derived from channel ceiling + `output_contract` + explicit tags | Ceiling → policy derivation rule |
| POLICY-03 | Negative test: result violating authored policy is rejected at receipt step | Phase 2 test fixture |
| AUDIT-01 | Append-only; SQLite triggers enforce; no delete API | BEFORE DELETE + BEFORE UPDATE triggers verified |
| AUDIT-02 | `algo_version="blake3-v1"` on every entry; verifier dispatches on it | Registry pattern with single entry |
| AUDIT-03 | `prev_hash` = BLAKE3 of canonical-JSON of previous entry | D-03 pattern verified in code |
| AUDIT-04 | Dispatch entry records full context: tier per block, shadow IDs, classification reasons, signature hashes | Denormalized payload column |
| AUDIT-05 | Queryable by channel, node, tier, date range, shadow ID, envelope ID, receipt status | JSON1 patterns verified |
| AUDIT-06 | Exportable as JSON Lines with chain-head proof; includes `algo_version` | `_query_rows()` streaming |
| AUDIT-07 | `AnchorTarget` Protocol + no-op default + smoke test | Protocol with `anchor(entry) -> AnchorReceipt | None` |
| AUDIT-08 | Chain integrity verifiable on read; tampered entry → verify returns False | BLAKE3 re-computation on slice |
| CLI-01 | `photophore channel new|list|show|suspend|close|set-ceiling` | click group pattern verified |
| CLI-02 | `photophore audit query|export|verify` | Subcommands with D-12 JSON Lines twist |
| CLI-04 | `photophore classify` dry-run with `(tier, reason)` output | Pure function call, no dispatch |
| CLI-05 | `photophore policy preview` shows `result_policy` without dispatching | Pure policy authoring call |
</phase_requirements>

---

## Executive Summary

Phase 2 builds Photophore's privacy-critical components from scratch in `photophore/python/` (a greenfield sibling repo). The components are ordered by dependency: audit log and channel registry land first because every subsequent component writes through them. The classifier, shadow generator, and policy authoring are pure functions testable in isolation. The CLI wires them together without dispatch.

The most consequential research findings for planning:

**python-keyring has no enumerate-by-service API.** `keyring.get_credential(service, username=None)` does not list all usernames for a service. This means D-05's "walk keystore to rebuild channels.db" is impossible without an auxiliary `_index` sentinel. The planner MUST decide whether to implement the `_index` sentinel (D-06 deferred this decision) — without it, bootstrap can only walk `channels.db` and verify each entry in the keystore, but cannot detect channels that exist in the keystore but NOT in `channels.db`. Recommendation: implement `_index` sentinel (JSON array of UUIDs stored at `photophore.channel:_index` in keystore). [VERIFIED: keyring 25.7.0 API inspection]

**`pathspec` library is required for glob matching.** Neither `fnmatch.fnmatch` nor `pathlib.PurePath.match` correctly handles `**/.env*` matching bare `.env` (no leading directory). The CONTEXT.md example `**/.env*` → `local` is a common pattern that must match bare filenames. `pathspec>=1.1.1` with `gitwildmatch` semantics handles this correctly. [VERIFIED: live test in Python 3.14.4 venv]

**SQLite `RAISE(ABORT, ...)` in triggers raises `sqlite3.IntegrityError`, not `OperationalError`.** Callers wrapping audit write operations must catch `sqlite3.IntegrityError` for trigger violations. This is a sharp edge that would produce silent failures if callers only catch `OperationalError`. [VERIFIED: live SQLite 3.53.0 test]

**`blake3` 1.0.8 is the current version (not 0.4+).** The CLAUDE.md stack table says `0.4+`; actual PyPI current is `1.0.8` with API `blake3.blake3(data).hexdigest()`. The API is stable and backwards compatible with 0.4 usage. Not currently installed in the thermocline venv — must be added to `photophore/python/pyproject.toml` as a direct dependency. [VERIFIED: PyPI index + live install test]

**The `_ResultPolicy` shape is already defined in `thermocline.envelope`** with fields `persist_to_shared`, `return_only`, `strip_before_persist` (all `list[str]`). Phase 2's `policy.author()` produces instances of this class derived from channel ceiling. The class is not currently in `thermocline`'s `__all__` — Phase 2 should import from `thermocline.envelope._ResultPolicy` or the planner should request `thermocline` expose it publicly. [VERIFIED: live import test]

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Audit log storage | Sovereign node / SQLite | Ring 2/3 (future) | Append-only local DB; spec mandates Ring 1 always |
| Channel trust store | Sovereign node / platform keystore | `channels.db` (derived index) | Platform keystore is the authoritative source; index is projection |
| Content classification | Sovereign node / pure function | — | No I/O, no network, deterministic |
| Shadow generation | Sovereign node / pure function | — | Dispatch-time only; never cached |
| Result policy authoring | Sovereign node / pure function | — | Issuer-authored before signing |
| CLI entry point | Sovereign node / click binary | — | Thin dispatcher; all logic in library modules |

---

## Plan-Mapping

### Plan 02-01: Package Scaffold + Audit + Channels

**Scope:** Greenfield `photophore/python/` package. Audit log (AUDIT-01..08 foundation) and channel registry (CHAN-01..06) are co-dependent: channels write through audit, audit has channel_id index. Both must land in 02-01.

**Key decisions to lock at planning time:**

1. **`_index` sentinel decision (D-06):** Since `python-keyring` has no enumerate-by-service API, the planner must explicitly decide: implement `_index` JSON-array sentinel (recommended) OR declare that channels.db is the sole enumeration source and halt-on-missing-channels.db. The D-05 bootstrap walk cannot verify keystore completeness without `_index`.

2. **WAL mode for SQLite:** Both `channels.db` and `audit.db` should use `PRAGMA journal_mode=WAL` from creation. Not a user-decision but must be in the Wave 0 schema init.

3. **`photophore.core` vs flat imports:** The recommended module layout puts shared types (Tier, Reason, ChannelId, ShadowId, ContentType) in `photophore.core`. This avoids circular imports where `audit` and `channels` both need these types.

**Technical risks:**
- D-05 bootstrap halt-on-unaudited-channel requires reading from BOTH keystore and audit.db. The ordering matters: if `audit.db` is missing or corrupt, bootstrap must still detect unaudited channels. Plan tasks must initialize both DBs before the channels module is imported.
- `sqlite3.IntegrityError` (not `OperationalError`) is raised by `RAISE(ABORT, ...)` triggers. Every audit write wrapper must catch `IntegrityError`.
- Keyring enumeration limitation: `_index` sentinel must be written atomically with channel creation (inside the D-07 three-step write order).

**Recommended task ordering (within 02-01):**
1. Package scaffold: `photophore/python/pyproject.toml`, `src/photophore/__init__.py`, `src/photophore/core.py` (Tier, Reason, ChannelId, ShadowId, ContentType enums/types)
2. Audit module: schema + append-only triggers + `AuditEntry` dataclass + `AuditLog.append()` + `_query_rows()` + `query()` + `verify_chain()` + `AnchorTarget` Protocol + no-op default
3. Channels module: `Channel` dataclass + `ChannelRecord` + state machine + `ChannelStore` (three-step write ordering + `_index` sentinel + D-05 bootstrap) + `channels.db` index schema
4. CLI 02-01 surface: `photophore channel` group + `photophore audit` group

**AT-* surfaces wired here:**
- AT-A6 (Audit Log Manipulation) — append-only trigger test is the primary behavioral test
- AT-A5 (Trust Store Tampering) — three-store model is the structural defense; tested by asserting audit.db and keystore are separate files
- AT-A1 (Channel Impersonation) — structural fixture only (phase-tagged to Phase 3 for behavioral wire)

**Requirements covered:** CHAN-01..06, AUDIT-01..08, CLI-01, CLI-02

---

### Plan 02-02: Classifier

**Scope:** `photophore.classifier` module — explicit tag parser, path-rule engine (YAML loading + `pathspec` matching), rule-based v0.1 classifier, `default_tier()` named function, `photophore classify` CLI, Hypothesis property test.

**Key decisions to lock at planning time:**

1. **`pathspec` dependency confirmed required.** `fnmatch` and `pathlib.PurePath.match` both fail on `**/.env*` matching bare `.env`. Add `pathspec>=1.1.1` to `pyproject.toml` with `gitwildmatch` semantics (`pathspec.PathSpec.from_lines("gitwildmatch", patterns)`).

2. **Rule-based classifier patterns (CLASS-04):** Three categories verified from spec. Planner must enumerate the specific regex/patterns for the classifier:
   - Credential patterns: API key tokens (e.g., `sk-[a-zA-Z0-9]{20,}`), PEM headers (`-----BEGIN`), `.env`-style assignments (`KEY=VALUE` with uppercase key), AWS key format (`AKIA[A-Z0-9]{16}`)
   - PII patterns: SSN (`\d{3}-\d{2}-\d{4}`), email (`[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+`), phone numbers, credit card patterns
   - Known sensitive file types: `.pem`, `.key`, `.p12`, `.pfx`, `.keychain`, `.env`, `.env.*`

3. **`classify()` function signature:** Must be a single function with explicit branch order (not a strategy pattern). The branch order IS the CLASS-01 requirement. Signature: `classify(block: ContentBlock, rules: PathRules | None = None) -> Classification`.

**Technical risks:**
- `yaml.safe_load` is mandatory (PITFALLS.md Security); `yaml.load` without safe loader is RCE via YAML tags. CI lint should flag `yaml.load(` calls.
- Path-rule catch-all must be validated at load time, not at match time (Pitfall 8). If `RulesConfigError` is raised, it must surface exit code 2 (D-14).

**Recommended task ordering:**
1. Core types in `photophore.core`: `Tier` enum, `Reason` dataclass (or similar), `Classification` type
2. Classifier module: `classify()` + explicit-tag parser + `default_tier()` named function
3. Rules config loader: YAML load + `pathspec` integration + catch-all validation
4. Hypothesis property test: CLASS-06 invariant
5. `photophore classify` CLI subcommand

**Requirements covered:** CLASS-01..06, CLI-04

---

### Plan 02-03: Shadow + Policy + Policy Preview CLI

**Scope:** `photophore.shadow` (per-type strategies + quality tests), `photophore.policy` (result_policy authoring for task envelopes), `photophore policy preview` CLI.

**Key decisions to lock at planning time:**

1. **Shadow content-type strategy shape:** Planner chooses closed enum + match OR registry. Both work; closed enum is simpler for v0.1 and easier to type-check. Recommendation: closed `ContentType` enum + `match content_type` in `generate()`. Adding a 7th type in v0.2 requires adding an enum member and a match arm (two localized changes).

2. **Irreversibility test minimum substring length:** The simple "contains any 4-char substring of source" approach produces false positives (e.g., the word "at" from source appears in many English abstractions). Recommendation: 8-char minimum for meaningful identifier detection, combined with a word-boundary check. Exact threshold is planner discretion — must be documented as a named constant `_IRREVERSIBILITY_MIN_SUBSTR_LEN = 8`.

3. **Relevance and distinguishability tests:** Spec says "soft fail — dispatch continues with warning recorded to audit." In Phase 2 (no dispatch coordinator), the shadow generator must return a warning flag or raise a soft-fail exception that the caller (in Phase 3) can catch and log to audit. Recommendation: return a `ShadowResult(shadow, warnings: list[str])` instead of bare `Shadow`.

4. **`_ResultPolicy` import:** Phase 2 should import `from thermocline.envelope import _ResultPolicy` (private but stable — established in Phase 1). The planner should note this is a private import and consider requesting `thermocline` expose it in `__all__`.

**Technical risks:**
- SHADOW-06 (no caching) must be enforced structurally: `shadow.generate()` must create a new `uuid.uuid4()` on EVERY call with no module-level state. Property test: N=100 calls with identical input produce N distinct shadow_ids.
- POLICY-03 requires a negative test fixture: a `task` envelope draft with an injected `result_policy` field must have that field silently ignored, and the returned policy must differ from the draft's injected policy.

**Recommended task ordering:**
1. Shadow core types: `ShadowId`, `Shadow`, `ContentType` enum (move from `core.py` if not already there), `ShadowResult`
2. Shadow generator: `generate(block, content_type)` + per-type abstraction strategies for all 6 types
3. Quality tests: `irreversibility_test()` (hard fail), `relevance_preservation_test()` (soft warn), `distinguishability_test()` (soft warn)
4. Hypothesis property test: SHADOW-02 uniqueness over 100 calls
5. Policy module: `author(channel, envelope_draft) -> _ResultPolicy` ignoring draft's existing policy
6. `photophore policy preview` CLI subcommand
7. POLICY-03 negative fixture

**Requirements covered:** SHADOW-01..06, POLICY-01..03, CLI-05

---

## Library + API Patterns

### SQLite Append-Only Enforcement (AUDIT-01)

**Verified trigger SQL** — raises `sqlite3.IntegrityError` (NOT `OperationalError`) in Python:

```sql
-- Create triggers on the entries table
CREATE TRIGGER entries_no_delete
    BEFORE DELETE ON entries
BEGIN
    SELECT RAISE(ABORT, 'append-only: entries table is immutable by design');
END;

CREATE TRIGGER entries_no_update
    BEFORE UPDATE ON entries
BEGIN
    SELECT RAISE(ABORT, 'append-only: entries table is immutable by design');
END;
```

**Python caller pattern:**

```python
# photophore/audit/_store.py
import sqlite3

def _append_entry(conn: sqlite3.Connection, entry_dict: dict) -> None:
    try:
        conn.execute(
            "INSERT INTO entries (id, algo_version, prev_hash, entry_hash, "
            "event_type, channel_id, envelope_id, timestamp, payload) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (entry_dict["id"], entry_dict["algo_version"], ...)
        )
    except sqlite3.IntegrityError as exc:
        # Trigger fired (should never happen via normal API — indicates
        # a bypass attempt or schema drift). Surface as AuditWriteError.
        raise AuditWriteError(
            f"audit log rejected write (append-only violation): {exc}"
        ) from exc
```

[VERIFIED: SQLite 3.53.0, `sqlite3.IntegrityError` confirmed]

---

### BLAKE3 Chain Implementation (AUDIT-02, AUDIT-03)

**API** (blake3 1.0.8): `blake3.blake3(data: bytes).hexdigest() -> str`

**Chain pattern:**

```python
# photophore/audit/_chain.py
import sys
sys.path  # blake3 in photophore deps (not thermocline-py)
import blake3
from thermocline.canonical import canonicalize

_ALGO_VERSION = "blake3-v1"  # AUDIT-02: must be in every entry

def compute_entry_hash(entry_without_hash: dict) -> str:
    """Compute the entry_hash for an audit entry.
    
    D-03: hash domain = whole-entry canonical-JSON EXCLUDING the entry_hash field.
    """
    canonical = canonicalize(entry_without_hash)
    return blake3.blake3(canonical).hexdigest()

def verify_entry_hash(entry: dict) -> bool:
    """Return True if entry_hash matches recomputed hash."""
    entry_minus_hash = {k: v for k, v in entry.items() if k != "entry_hash"}
    expected = compute_entry_hash(entry_minus_hash)
    return entry["entry_hash"] == expected

# Chain head bootstrap:
# First entry: prev_hash = ""  (empty string, not None, not sentinel hash)
# All subsequent: prev_hash = previous entry's entry_hash

# AUDIT-02 forward-compatible dispatch:
_HASH_ALGO_REGISTRY = {
    "blake3-v1": lambda data: blake3.blake3(data).hexdigest(),
    # Future: "blake3-v2": lambda data: ...
}

def compute_hash_by_version(algo_version: str, data: bytes) -> str:
    fn = _HASH_ALGO_REGISTRY.get(algo_version)
    if fn is None:
        raise UnsupportedChainAlgoError(f"unknown algo_version: {algo_version!r}")
    return fn(data)
```

[VERIFIED: blake3 1.0.8 API, rfc8785 canonicalization, chain tamper detection]

---

### JSON1 Query Patterns for AUDIT-05 Filters

**SQLite 3.53.0 ships JSON1 built-in** (merged into core in 3.38; present on macOS).

```sql
-- Filter by shadow_id (stored as JSON array in payload)
SELECT id, event_type, timestamp, payload
FROM entries
WHERE EXISTS (
    SELECT 1 FROM json_each(json_extract(payload, '$.shadow_ids'))
    WHERE value = :shadow_id
);

-- Filter by tier present in dispatch (array of tiers per block)
SELECT id FROM entries
WHERE EXISTS (
    SELECT 1 FROM json_each(json_extract(payload, '$.tiers'))
    WHERE value = :tier
);

-- Filter by receipt status (scalar in payload)
SELECT id FROM entries
WHERE json_extract(payload, '$.receipt_status') = :status;

-- Combined: channel + date range (indexed columns only, no JSON1 needed)
SELECT * FROM entries
WHERE channel_id = :channel_id
  AND timestamp >= :since
  AND timestamp <= :until
ORDER BY timestamp ASC;
```

[VERIFIED: all patterns tested against SQLite 3.53.0 in-memory DB]

---

### python-keyring Channel-Store Patterns (CHAN-04, D-04, D-06)

**Critical finding:** `python-keyring` has NO enumerate-by-service API. `keyring.get_credential(service, username=None)` does NOT return all usernames for a service. The `_index` sentinel is REQUIRED for keystore-only bootstrap.

```python
# photophore/channels/_store.py
import keyring
import json
from keyring.backends import fail as _fail_backend
from keyring.backends import null as _null_backend

_KEYSTORE_SERVICE = "photophore.channel"
_INDEX_SENTINEL_KEY = "_index"  # D-06: stores JSON array of channel_ids

def _probe_keystore() -> None:
    """Probe keystore availability at startup. Raises KeystoreUnavailableError if unavailable.
    
    Reuses Phase 1 BL-03 pattern: isinstance against PRODUCTION fail/null classes,
    not substring on class name (both are named 'Keyring').
    """
    try:
        backend = keyring.get_keyring()
    except Exception as exc:
        raise KeystoreUnavailableError("keystore unavailable") from exc
    if isinstance(backend, (_fail_backend.Keyring, _null_backend.Keyring)):
        raise KeystoreUnavailableError(
            f"refusing to start: backend is "
            f"{type(backend).__module__}.{type(backend).__name__!r}"
        )

def _get_channel(channel_id: str) -> dict | None:
    raw = keyring.get_password(_KEYSTORE_SERVICE, channel_id)
    return json.loads(raw) if raw is not None else None

def _set_channel(channel_id: str, record: dict) -> None:
    keyring.set_password(_KEYSTORE_SERVICE, channel_id, json.dumps(record))

def _get_index() -> list[str]:
    raw = keyring.get_password(_KEYSTORE_SERVICE, _INDEX_SENTINEL_KEY)
    return json.loads(raw) if raw else []

def _set_index(channel_ids: list[str]) -> None:
    keyring.set_password(_KEYSTORE_SERVICE, _INDEX_SENTINEL_KEY, json.dumps(channel_ids))

def _add_to_index(channel_id: str) -> None:
    ids = _get_index()
    if channel_id not in ids:
        ids.append(channel_id)
        _set_index(ids)

# D-07 three-step write ordering for channel create:
def create_channel(record: dict, audit_append_fn) -> str:
    channel_id = str(uuid.uuid4())
    record["id"] = channel_id
    _set_channel(channel_id, record)       # Step 1: keystore (authoritative)
    _add_to_index(channel_id)              # D-06: update _index sentinel
    audit_append_fn({"event": "channel.created", "channel_id": channel_id, ...})  # Step 2: audit
    _upsert_channels_db(channel_id, record)  # Step 3: index projection
    return channel_id
```

[VERIFIED: keyring 25.7.0 API; isinstance probe pattern from Phase 1 BL-03]

---

### Click Command-Group Architecture (D-13, D-14)

**JSON flag pattern:** `--json` as root group option passed via `ctx.obj` to subcommands.

```python
# photophore/cli/__init__.py
import click
import sys

class PhotophoreError(click.ClickException):
    """Base for structured exit codes (D-14)."""
    pass

class ConfigError(PhotophoreError):
    exit_code = 2
class AuditIntegrityError(PhotophoreError):
    exit_code = 3
class ClassifierError(PhotophoreError):
    exit_code = 4
class KeystoreError(PhotophoreError):
    exit_code = 5

@click.group()
@click.option("--json", "output_json", is_flag=True, default=False,
              help="Machine-readable JSON output.")
@click.version_option()
@click.pass_context
def photophore(ctx: click.Context, output_json: bool) -> None:
    """Photophore privacy policy engine."""
    ctx.ensure_object(dict)
    ctx.obj["json"] = output_json

# Sub-groups:
from .channel_cmds import channel
from .audit_cmds import audit
from .classify_cmds import classify
from .policy_cmds import policy

photophore.add_command(channel)
photophore.add_command(audit)
photophore.add_command(classify)
photophore.add_command(policy)
```

**JSON Lines twist for audit:** `audit query` and `audit export` emit one JSON object per line under `--json`; all other subcommands emit a single JSON document.

```python
# In audit subcommand:
def emit_audit_output(entries, *, output_json: bool) -> None:
    if output_json:
        import json
        for entry in entries:
            click.echo(json.dumps(entry))  # One line per entry = JSON Lines
    else:
        # Human-readable table
        ...
```

**Exit code verification** (all patterns tested via CliRunner):
- `raise SystemExit(N)` → exit code N
- `raise ConfigError("msg")` → exit code 2, `Error: msg` to stderr
- `raise KeystoreError("msg")` → exit code 5

[VERIFIED: click 8.3.1 CliRunner tests, all patterns confirmed]

---

### Classifier Rule Pipeline (CLASS-01 through CLASS-06)

**Single `classify()` function — branch order IS the priority:**

```python
# photophore/classifier/_engine.py
import re
from dataclasses import dataclass
from enum import Enum

class Tier(Enum):
    LOCAL = "local"
    SHARED = "shared"
    PUBLIC = "public"

@dataclass(frozen=True)
class Classification:
    tier: Tier
    reason: str  # "explicit_tag" | "path_rule:<pattern>" | "classifier:<rule>" | "classifier:default"

def default_tier() -> Tier:
    """CLASS-06: named function (not a constant) returning Tier.LOCAL.
    
    Hypothesis property test asserts this is the fallback for all unmatched content.
    Never return Tier.SHARED or Tier.PUBLIC from this function.
    """
    return Tier.LOCAL

_EXPLICIT_TAG_RE = re.compile(
    r"@photophore:(local|shared|public)", re.IGNORECASE
)

def classify(
    content: bytes,
    path: str | None = None,
    rules: "PathRules | None" = None,
) -> Classification:
    """Classify content per CLASS-01 priority order: Tag > Path > Classifier > Default."""
    
    # Priority 1: Explicit Tag (CLASS-02)
    try:
        text = content.decode("utf-8", errors="replace")
    except Exception:
        text = ""
    if match := _EXPLICIT_TAG_RE.search(text):
        tier_str = match.group(1).lower()
        return Classification(Tier(tier_str), "explicit_tag")
    
    # Priority 2: Path Rule (CLASS-03, CLASS-05)
    if path is not None and rules is not None:
        if (rule := rules.match(path)) is not None:
            return Classification(rule.tier, f"path_rule:{rule.pattern}")
    
    # Priority 3: Rule-based classifier (CLASS-04)
    if (rule_name := _rule_based_classify(content, path)) is not None:
        return Classification(default_tier(), f"classifier:{rule_name}")
    
    # CLASS-06: default_tier() is the named function — must call it, not use literal
    return Classification(default_tier(), "classifier:default")
```

**Glob matching:** Use `pathspec>=1.1.1` with gitwildmatch semantics. `fnmatch` and `pathlib.PurePath.match` both fail on common patterns like `**/.env*` matching bare `.env`.

```python
# photophore/classifier/_rules.py
import pathspec
import yaml
from pathlib import Path

def load_rules(rules_path: Path) -> "PathRules":
    with open(rules_path) as f:
        raw = yaml.safe_load(f)  # NEVER yaml.load() -- RCE risk
    rules_list = raw.get("rules", [])
    
    # D-08/D-10: loader-time validation of mandatory catch-all
    if not rules_list or not (
        rules_list[-1].get("pattern") == "**"
        and rules_list[-1].get("tier") == "local"
    ):
        raise RulesConfigError(
            "rules config missing mandatory '**' → 'local' catch-all as last rule"
        )
    
    patterns = [r["pattern"] for r in rules_list]
    spec = pathspec.PathSpec.from_lines("gitwildmatch", patterns)
    # ...build PathRules with first-match-wins semantics
```

[VERIFIED: pathspec 1.1.1 `**/.env*` matching `.env` confirmed; fnmatch/pathlib failure confirmed]

---

### Shadow Per-Content-Type Strategies (SHADOW-03)

**Spec table** (from `photophore/README.md` §"Shadow Generation Quality"):

| Content Type | MUST Include | MUST NOT Include |
|---|---|---|
| `document` | Topic category, length class (short/medium/long), temporal indicator | Filename, author, specific dates, org names, unique IDs |
| `conversation` | Participant count, topic domain, tone (formal/informal) | Participant names, quotes, specific claims, timestamps |
| `credential` | Credential type only (API key, password, certificate) | Credential value, service name, account identifier |
| `file` | File type category (image/document/code/data), approx size class | Filename, path components, EXIF, embedded metadata |
| `identity` | Identity type only (person, organization, device) | Identity value, associated accounts, contact info |
| `code` | Language, complexity (script/module/application), domain (web/data/infra) | Repo name, function names, variable names, comments |

**Implementation shape (closed enum + match — recommended):**

```python
# photophore/shadow/_strategies.py
from enum import Enum

class ContentType(Enum):
    DOCUMENT = "document"
    CONVERSATION = "conversation"
    CREDENTIAL = "credential"
    FILE = "file"
    IDENTITY = "identity"
    CODE = "code"

def _generate_abstraction(content: bytes, content_type: ContentType) -> str:
    match content_type:
        case ContentType.DOCUMENT:
            return _abstract_document(content)
        case ContentType.CONVERSATION:
            return _abstract_conversation(content)
        case ContentType.CREDENTIAL:
            return _abstract_credential(content)
        case ContentType.FILE:
            return _abstract_file(content)
        case ContentType.IDENTITY:
            return _abstract_identity(content)
        case ContentType.CODE:
            return _abstract_code(content)
        # No default: match is exhaustive over the enum; mypy --strict will
        # reject unhandled cases if enum members are added without a match arm.
```

[VERIFIED: spec table read from photophore/README.md §"Shadow Generation Quality"]

---

### Irreversibility Test (SHADOW-04)

**Hard fail rule:** The abstraction string must not contain any identifying substring from the source content. Recommended minimum substring length: 8 characters (verified: 4-char limit produces false positives on common English words).

```python
# photophore/shadow/_quality.py
_IRREVERSIBILITY_MIN_SUBSTR_LEN: int = 8  # Named constant, documented

def irreversibility_test(source_content: bytes, abstraction: str) -> None:
    """Hard fail if abstraction leaks source content substrings.
    
    Raises ShadowIrreversibilityError if any substring of source of length
    >= _IRREVERSIBILITY_MIN_SUBSTR_LEN appears in the abstraction.
    """
    try:
        source_text = source_content.decode("utf-8", errors="replace")
    except Exception:
        return  # Binary content: cannot check substring leakage
    
    for i in range(len(source_text) - _IRREVERSIBILITY_MIN_SUBSTR_LEN + 1):
        substr = source_text[i:i + _IRREVERSIBILITY_MIN_SUBSTR_LEN]
        if substr.strip() and substr in abstraction:
            raise ShadowIrreversibilityError(
                f"abstraction leaks source substring {substr!r}"
            )
```

[VERIFIED: 4-char threshold produces false positives; 8-char threshold passes all test cases]

---

### Hypothesis Property Tests (CLASS-06, AUDIT-08, SHADOW-02)

**CLASS-06 — Classifier default invariant:**

```python
# photophore/tests/test_classifier.py
from hypothesis import given, settings
from hypothesis import strategies as st

@given(content=st.binary(min_size=0, max_size=10_000))
@settings(max_examples=100)
def test_default_tier_for_unmatched_content(content: bytes) -> None:
    """Any content with no explicit tag and no path-rule match classifies as LOCAL."""
    # No explicit tag: content must not contain @photophore:
    assume(b"@photophore:" not in content)
    result = classify(content, path=None, rules=None)
    assert result.tier == Tier.LOCAL
    assert result.reason == "classifier:default"
```

**AUDIT-08 — Chain integrity tamper detection:**

```python
@given(
    n_entries=st.integers(min_value=2, max_value=10),
    tamper_index=st.integers(min_value=0, max_value=9),
    tamper_byte_offset=st.integers(min_value=0),
)
@settings(max_examples=100)
def test_audit_chain_tamper_detected(n_entries, tamper_index, tamper_byte_offset) -> None:
    """Any single-byte tamper in any entry invalidates subsequent chain."""
    assume(tamper_index < n_entries)
    # Build N entries, tamper one, verify chain -> must return False
    ...
```

**SHADOW-02 — Shadow ID uniqueness:**

```python
@given(
    content=st.binary(min_size=1, max_size=1000),
    content_type=st.sampled_from(list(ContentType)),
)
@settings(max_examples=100)
def test_shadow_id_uniqueness_per_call(content: bytes, content_type: ContentType) -> None:
    """100 calls with identical input produce 100 distinct shadow_ids."""
    ids = [generate(content, content_type).shadow.shadow_id for _ in range(100)]
    assert len(set(ids)) == 100
```

[VERIFIED: hypothesis 6.152.4 confirmed installed; all patterns syntactically valid]

---

### Conformance Fixtures AT-A1..A6 (Phase 2 scope, some phase-tagged)

Per 02-CONTEXT.md §"Claude's Discretion": fixture authorship is Phase 2 scope; behavioral wiring may be phase-tagged to Phase 3 per Phase 1 D-04 convention.

| Surface | What it tests | Phase 2 behavior | Expected error code |
|---|---|---|---|
| AT-A1 | Compromised sovereign node / channel impersonation | Structural fixture committed; behavioral wire = Phase 3 (dispatch) | `CHANNEL_IMPERSONATION` |
| AT-A2 | Shadow inference / cross-dispatch shadow ID reuse | Behavioral: SHADOW-02 uniqueness test covers this | `SHADOW_ID_REUSE` |
| AT-A3 | Classifier evasion / forged explicit tag promoting tier-0 | Behavioral: CLASS-01 priority test covers this; negative fixture | `TIER_ESCALATION_BLOCKED` |
| AT-A4 | Audit log tampering / modified prev_hash | Behavioral: AUDIT-08 Hypothesis test covers this | `AUDIT_CHAIN_BROKEN` |
| AT-A5 | Trust-store co-location (audit DB and trust DB same file) | Structural assertion: different file paths at startup | `TRUST_STORE_COLOCATION` |
| AT-A6 | Ceiling raise without human action | Behavioral: CHAN-03 distinct event type covers this | `CEILING_RAISE_UNAUTHORIZED` |

**Fixture location:** `thermocline/conformance/invalid/AT-A{N}-*.json` with phase tag in `MANIFEST.yaml` (extending Phase 1's three-level YAML manifest structure).

---

### Result Policy Authoring (POLICY-01, POLICY-02)

**`_ResultPolicy` shape** (from `thermocline.envelope._ResultPolicy` — Phase 1 defined, not yet in `__all__`):

```python
class _ResultPolicy(BaseModel):
    persist_to_shared: list[str] = []   # field names allowed to persist to shared store
    return_only: list[str] = []         # field names returned but not persisted
    strip_before_persist: list[str] = [] # field names stripped before any persistence
```

**Ceiling → policy derivation (POLICY-02):**

```python
# photophore/policy/_author.py
from thermocline.envelope import _ResultPolicy, Task

def author(channel: Channel, envelope_draft: dict) -> _ResultPolicy:
    """Author result_policy from channel ceiling. IGNORES any result_policy in draft.
    
    POLICY-01: The draft's result_policy field is never consulted.
    """
    # Derive from ceiling:
    ceiling = channel.ceiling  # "tier-0" | "tier-1" | "tier-2"
    
    if ceiling == "tier-0":
        # No content crosses. Strip everything.
        return _ResultPolicy(strip_before_persist=["*"])
    elif ceiling == "tier-1":
        # Shadows only. Return tier-1 shadow refs; strip raw content.
        return _ResultPolicy(
            return_only=["shadow_refs"],
            strip_before_persist=["content", "raw_output"]
        )
    else:  # tier-2
        # Public content crosses. Allow persist.
        return _ResultPolicy(persist_to_shared=["public_outputs"])
```

[VERIFIED: `_ResultPolicy` fields confirmed via live import; three-field structure established in Phase 1]

---

## Pitfalls + Mitigations

### Pitfall 1 (Audit chain integrity — algo lock-in)
**Phase 2 action:** `algo_version="blake3-v1"` in every `AuditEntry` from first commit. Verifier dispatches via `_HASH_ALGO_REGISTRY` dict. `UnsupportedChainAlgoError` raised for unknown versions. Test: assert `algo_version` field present on every entry type.

### Pitfall 2 (Classifier default drift)
**Phase 2 action:** `default_tier()` is a NAMED FUNCTION (not `Tier.LOCAL` literal). All unmatched branches call `default_tier()`, never return a literal. Hypothesis property test (CLASS-06) asserts invariant over 100 cases. CI lint may flag `Tier.SHARED` and `Tier.PUBLIC` appearing outside the explicit-tag and path-rule handlers.

### Pitfall 3 (Shadow caching)
**Phase 2 action:** `shadow.generate()` calls `str(uuid.uuid4())` on EVERY invocation. No module-level shadow cache, no memoization. SHADOW-02 Hypothesis property test asserts uniqueness over 100 calls with identical input. Review every call site for `@lru_cache` or `functools.cache` — forbidden on shadow generator.

### Pitfall 4 (Sensitive discipline)
**Phase 2 action:** Phase 1 already ships `Sensitive[T]`. Apply to `ContentBlock.content` (already typed in thermocline). For photophore-internal types: `Shadow.abstraction` does NOT need `Sensitive` (it IS the safe-for-transmission representation). `Channel` record values that hold raw credentials (e.g., `remote_pubkey_hex`) do NOT need `Sensitive` (they are public keys).

### Pitfall 6 (Trust store co-location)
**Phase 2 action:** D-04 three-store model: keystore (via python-keyring), `channels.db`, `audit.db` — three discrete files. AT-A5 fixture asserts `audit.db` path != keystore path at startup. Test: assert these are different storage backends.

### Pitfall 8 (Path-rule catch-all missing)
**Phase 2 action:** `load_rules()` validates catch-all at load time (before any classify call). `RulesConfigError` surfaces exit code 2 (D-14). Test fixture: load a config without `**` → assert `RulesConfigError` with the specific message.

### Pitfall 9 (In-process keys)
**Phase 2 action:** Phase 2 does not manage keys directly. Channel records store `remote_pubkey_hex` (a public key — safe to store). No signing in Phase 2. The `IdentityProvider` Protocol (Phase 1) is the signing boundary.

### Pitfall 11 (json.dumps for signing/hashing)
**Phase 2 action:** All audit chain hashing uses `thermocline.canonical.canonicalize()`. The Phase 1 `check_no_json_dumps` AST lint applies to all photophore code. No `json.dumps` calls in the audit module's hash computation path.

### Pitfall 12 (Pydantic v1 patterns)
**Phase 2 action:** `photophore/python/pyproject.toml` pins `pydantic>=2.7,<3.0`. CI lint flags `.dict(` and `.json()` method calls. `model_dump(mode="json")` everywhere.

---

## Open Questions for Planner

### OQ-1: `_index` sentinel — implement or rely solely on channels.db?

**What we know:** python-keyring has no enumerate-by-service API. D-05 requires bootstrap to detect channels in keystore but not in channels.db.

**What's unclear:** D-06 deferred this decision. Without `_index`, bootstrap can only walk `channels.db` and verify each in keystore — but cannot detect keystore entries with no corresponding channels.db row.

**Recommendation:** Implement `_index` sentinel (`photophore.channel:_index` = JSON array of channel_ids). Update it atomically with channel creation/deletion as part of the D-07 three-step write order. This is the only correct way to implement D-05 "keystore-as-truth" bootstrap without platform-specific keystore enumeration APIs.

---

### OQ-2: `_ResultPolicy` public export from thermocline-py

**What we know:** `_ResultPolicy` is defined in `thermocline.envelope` but not in `thermocline.__all__`. Phase 2 needs to import and return instances of this class.

**What's unclear:** Should Phase 2 import from the private `_ResultPolicy` path, or should a `thermocline-py` patch add it to `__all__`?

**Recommendation:** Add `_ResultPolicy` to `thermocline.__all__` and rename it `ResultPolicy` (public). This is a trivial change that improves the API surface and removes the "private import" anti-pattern. Document as a spec-driven extension (result_policy authoring is spec-mandated).

---

### OQ-3: Shadow soft-fail return type

**What we know:** SHADOW-04 says relevance + distinguishability tests are "soft fail — dispatch continues with warning recorded to audit." In Phase 2, there is no dispatch coordinator to record to audit.

**What's unclear:** How should the shadow generator signal soft-fail warnings to Phase 3?

**Recommendation:** Return `ShadowResult(shadow: Shadow, warnings: list[str])` from `generate()`. Phase 3's dispatch coordinator records non-empty `warnings` to audit. Phase 2 tests assert that leaky abstractions produce non-empty `warnings` and that the `Shadow` is still returned (not raised).

---

### OQ-4: AT-A1 fixture behavioral wiring timeline

**What we know:** AT-A1 (channel impersonation) is about a forged remote node identity. The forge-side check is Phase 3 scope.

**What's unclear:** Is there a meaningful Phase 2 behavioral wire for AT-A1, or is it purely structural?

**Recommendation:** Phase 2 commits the AT-A1 fixture with `phase: 3` tag in `MANIFEST.yaml`. The structural fixture (a task envelope with a forged channel_id) is committed in Phase 2; behavioral exercise (the dispatch coordinator rejecting it via audit-log lookup) lands in Phase 3.

---

### OQ-5: `photophore.core` module strategy

**What we know:** Multiple modules need shared types: `Tier`, `Reason`, `ChannelId`, `ShadowId`, `ContentType`, `Classification`.

**What's unclear:** Should these live in `photophore/core.py` (flat), `photophore/core/__init__.py` (package), or be distributed across modules?

**Recommendation:** Flat `photophore/core.py` for Phase 2. All shared enums and dataclasses live here. Avoids circular imports (audit imports core, channels imports core, classifier imports core — none imports from each other). A `core/` package can be introduced in Phase 4 if the file grows unwieldy.

---

## Acceptance Criteria Crosswalk

| Req ID | Plan | Acceptance Test |
|--------|------|-----------------|
| CHAN-01 | 02-01 | `channel create` produces record in keystore and channels.db with all required fields |
| CHAN-02 | 02-01 | State machine: PROPOSED→OPEN→SUSPENDED→CLOSED; double-CLOSE raises ChannelStateError |
| CHAN-03 | 02-01 | Lower ceiling: succeeds silently. Raise ceiling: produces `channel.ceiling_raised` audit event |
| CHAN-04 | 02-01 | `audit.db` and keystore are different file paths; AT-A5 structural test asserts |
| CHAN-05 | 02-01 | Audit entry exists BEFORE channel create returns; verified by interrupting after step 1 and checking audit |
| CHAN-06 | 02-01 | `photophore channel list --json` returns valid JSON array; `channel show <id>` returns single JSON object |
| CLASS-01 | 02-02 | Priority test: content with explicit tag + matching path-rule → explicit tag wins |
| CLASS-02 | 02-02 | `classify(b"@photophore:public some content")` → `(PUBLIC, "explicit_tag")` |
| CLASS-03 | 02-02 | Loading rules config without `**` → `local` raises `RulesConfigError` at load time |
| CLASS-04 | 02-02 | `classify(b"sk-abcdef1234567890")` → `(LOCAL, "classifier:credential_pattern")` |
| CLASS-05 | 02-02 | `photophore classify ./file` output includes reason string for every block |
| CLASS-06 | 02-02 | Hypothesis: 100 generated ContentBlocks with no tag/rule → all `(LOCAL, "classifier:default")` |
| SHADOW-01 | 02-03 | Two calls with identical input produce different shadow_ids; no shared state |
| SHADOW-02 | 02-03 | Hypothesis: 100 calls → 100 distinct shadow_ids; Shadow fields present and typed |
| SHADOW-03 | 02-03 | `generate(credential_content, ContentType.CREDENTIAL).abstraction` contains "credential type" phrase but not the credential value |
| SHADOW-04 | 02-03 | `generate(content_with_leak, ...)` raises `ShadowIrreversibilityError`; soft-fail returns ShadowResult with non-empty warnings |
| SHADOW-05 | 02-03 | `policy preview` fixture shows tier-0 stripped, tier-1 → shadow, tier-2 passthrough |
| SHADOW-06 | 02-03 | No Shadow object retained after `generate()` returns; verified by absence of module-level cache |
| POLICY-01 | 02-03 | Draft with `result_policy` injected → authored policy differs from draft policy |
| POLICY-02 | 02-03 | `author(tier-2 channel, draft)` → `persist_to_shared` non-empty; `author(tier-0 channel, draft)` → `strip_before_persist` covers everything |
| POLICY-03 | 02-03 | Negative fixture: policy mismatch detected (Phase 3 full wire; Phase 2 ships the fixture) |
| AUDIT-01 | 02-01 | `DELETE FROM entries` raises `sqlite3.IntegrityError`; `UPDATE` raises same |
| AUDIT-02 | 02-01 | Every entry row has `algo_version="blake3-v1"`; verifier dispatches via registry |
| AUDIT-03 | 02-01 | Entry 2's `prev_hash` == entry 1's `entry_hash`; chain head `prev_hash = ""` |
| AUDIT-04 | 02-01 | Dispatch pre-entry payload contains: `remote_node`, `tier_per_block[]`, `shadow_ids[]`, `classification_reasons[]` |
| AUDIT-05 | 02-01 | `audit.query(channel_id=X)` returns only entries for channel X; `audit.query(shadow_id=Y)` uses JSON1 |
| AUDIT-06 | 02-01 | `photophore audit export --json` emits one JSON object per line; includes `algo_version` |
| AUDIT-07 | 02-01 | `AnchorTarget` Protocol has `anchor(entry) -> AnchorReceipt | None`; no-op default returns None; smoke test passes |
| AUDIT-08 | 02-01 | Hypothesis: tamper any byte of any entry → `verify_chain()` returns False |
| CLI-01 | 02-01 | `photophore channel new --remote-node bob --ceiling tier-1 --key-scheme brine` creates channel |
| CLI-02 | 02-01 | `photophore audit query --channel <id> --json` emits JSON Lines |
| CLI-04 | 02-02 | `photophore classify ./path` prints `(tier, reason)` per block; exits 0 |
| CLI-05 | 02-03 | `photophore policy preview --channel <id> --task draft.json` prints result_policy JSON |

---

## Sources

### Primary (HIGH confidence)
- `photophore/README.md` v0.3.0-draft — normative spec for all Phase 2 behavior
- `thermocline/thermocline/python/src/thermocline/identity.py` — BrineProvider pattern lines 314–606
- `thermocline/thermocline/python/src/thermocline/canonical.py` — canonicalize() API
- `thermocline/thermocline/python/src/thermocline/sensitive.py` — Sensitive[T] pattern
- `thermocline/thermocline/python/tests/conftest.py` — brine_in_memory_keyring fixture pattern
- `thermocline/thermocline/python/src/thermocline/scripts/build_schemas.py` — schema generation pattern
- `thermocline/.planning/phases/02-photophore-privacy-primitives-foundations/02-CONTEXT.md` — locked decisions D-01 through D-14
- SQLite 3.53.0 JSON1 + trigger behavior [VERIFIED: live tests in venv]
- blake3 1.0.8 API [VERIFIED: `pip index versions blake3` + live install]
- python-keyring 25.7.0 API [VERIFIED: live API inspection]
- pathspec 1.1.1 [VERIFIED: live `**/.env*` matching test]
- pydantic 2.13.4 [VERIFIED: installed in venv]
- hypothesis 6.152.4 [VERIFIED: installed in venv]
- click 8.3.3 [VERIFIED: exit code tests via CliRunner]

### Secondary (MEDIUM confidence)
- `thermocline/.planning/research/PITFALLS.md` — pitfall-to-phase mapping
- `thermocline/.planning/research/ARCHITECTURE.md` — module boundaries, network-isolation contract
- `thermocline/.planning/phases/01-thermocline-py-foundations/01-LEARNINGS.md` — 12 decisions, BL-03 isinstance probe pattern, BL-04 clobber-safe generate, real-fixture-from-disk discipline

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all package versions verified against PyPI and venv
- SQLite trigger behavior: HIGH — live tested (RAISE(ABORT) → IntegrityError confirmed)
- Keyring enumeration limitation: HIGH — API inspection confirmed no enumerate-by-service
- Pathspec requirement: HIGH — live test confirmed fnmatch/pathlib failure on `**/.env*`
- Architecture patterns: HIGH — reusing Phase 1 established patterns (BL-01..04)
- Shadow content-type strategies: HIGH — read directly from spec §"Shadow Generation Quality"
- Result policy authoring: HIGH — `_ResultPolicy` fields confirmed via live import
- Blake3 API: HIGH — live install confirmed API; version 1.0.8 (CLAUDE.md says "0.4+" — both work)
- Irreversibility test threshold: MEDIUM — 8-char minimum is a recommendation; exact value is planner discretion

**Research date:** 2026-05-09
**Valid until:** 2026-06-09 (30 days — stable libraries)

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `_ResultPolicy` will be made public (`ResultPolicy`) in thermocline-py | Policy Authoring, OQ-2 | Phase 2 must use private import `thermocline.envelope._ResultPolicy`; minor coupling, low risk |
| A2 | AT-A1 behavioral wire is Phase 3 scope (dispatch-time) | Conformance Fixtures | If spec requires Phase 2 wiring, the fixture must include a channel-store lookup test |
| A3 | 8-char irreversibility minimum substring length is acceptable | Irreversibility Test | Too low = false positives blocking valid shadows; too high = privacy leakage. Planner should pin the constant. |

**All other claims in this research were verified or cited — no user confirmation needed for those.**
