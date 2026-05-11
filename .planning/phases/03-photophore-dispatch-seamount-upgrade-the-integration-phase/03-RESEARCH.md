# Phase 3: Photophore Dispatch + Seamount Upgrade — Research

**Researched:** 2026-05-10
**Domain:** Async HTTP dispatch coordinator, Flask forge upgrade, cross-suite integration testing, AST-lint enforcement
**Confidence:** HIGH

## Summary

Phase 3 is the integration phase: everything built in Phases 1–2 converges into a real, working privacy-receipt round trip. The core deliverable is `photophore.dispatch` — an async coordinator implementing the 9-step flow defined in the Photophore spec — paired with upgraded forges (`pi-forge` with real brine signing, new `describe-forge` with tier-1 shadow handling), and a cross-suite conformance harness.

All key technologies are verified as installed and functional on the target machine: Python 3.14.4 (3.11+ compatible), `httpx` 0.28.1 with `AsyncClient`, `asyncio.to_thread` for sync-to-async bridging, `keyring` 25.7.0 on macOS Keychain, `jsonschema` 4.26.0 with `Draft202012Validator`, `hypothesis` 6.152.4, `pytest` 9.0.3. Flask is NOT installed in the shared venv — each forge has its own venv requirement (pi-forge has no venv yet; describe-forge will be created). The `asyncio.to_thread` shim (~20 LOC) wrapping Phase 2's sync APIs is verified feasible.

The three plans split cleanly: 03-01 (Photophore-only — dispatch coordinator + CLI + AST lint) is parallelizable with 03-02 (Seamount-only — pi-forge upgrade + describe-forge); 03-03 (E2E + conformance harness) depends on both. The AT-A1 fixture is committed at `thermocline/conformance/invalid/AT-A1-channel-impersonation.json` with `_phase_wired: 3`; the dispatch coordinator wires its behavioral check in 03-01. The `compare_result_against_policy()` function exists and is fully implemented in `photophore.policy._author`; POLICY-03 closure requires only the wiring call in step 9 of the dispatch coordinator.

**Primary recommendation:** Build 03-01 and 03-02 in parallel (different repos, no shared file edits), then 03-03 sequentially after both land. The shim pattern (`asyncio.to_thread` wrappers for sync Phase 2 APIs) is the lowest-risk async approach given Phase 2's sync-first discipline.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01 (Forge bootstrap UX = `init` subcommand + `GET /pubkey` endpoint + TOFU register on the sovereign side):**
  Each forge ships an `init` subcommand calling `BrineProvider.create()` under `seamount.piforge` / `seamount.describeforge` keystore namespaces. `GET /pubkey` returns `{"identity": "<name>", "key_scheme": "brine", "pubkey": "<hex>"}`. `photophore channel new --fetch-pubkey-from <url>` GETs that endpoint and calls `BrineProvider.register_public_key(channel.remote_node, pubkey_hex)` via Phase 1 BL-01 cross-role API. TOFU: pubkey locked at channel-new time; no re-fetch on rotation (rotation = new channel).

- **D-02 (describe-forge multi-shadow + tier-1-required + mixed-tier ignore-inline):**
  Accepted: `task` with ≥1 `context[]` block of `tier=1, kind="shadow"`. Per shadow: `"This forge received a shadow of type '<content_type>' with relevance <relevance>."` (normative string). Refuse zero-tier-1-shadows (`UNSUPPORTED_TASK_TYPE`). Mixed-tier: describe shadows only, do NOT echo inline content, record `provenance.tiers_present` with all seen tiers, set `outputs.note` when inline blocks were ignored.

- **D-03 (Single exit code 6 + 11 `DispatchError` subcodes; no auto-retry; `retryable: bool` advisory):**
  11 subcodes: `CHANNEL_RESOLVE_FAILED` (step 1), `CLASSIFICATION_FAILED` (2), `SHADOW_GENERATION_FAILED` (3), `POLICY_AUTHORING_FAILED` (4), `AUDIT_FAILED_PRE` (5, retryable), `SIGNING_FAILED` (6, retryable), `TRANSPORT_TIMEOUT`/`TRANSPORT_REFUSED` (7, retryable), `RECEIPT_MALFORMED` (8a), `RECEIPT_INVALID` (8b), `POLICY_VIOLATED` (8c), `AUDIT_FAILED_POST` (9, retryable). No automatic retries. `retryable: bool` advisory in CLI and JSON output. `audit_entry_hash` field in JSON error when failure occurred after audit-pre succeeded.

- **D-04 (Hybrid: subprocess for happy-path + receipt-verify; `app.test_client()` for fast unit-level negative paths):**
  Subprocess fixture `subprocess_forge(role)`: spawn forge on ephemeral port, run `<role> init` in test keystore namespace `seamount.<role>.test-<uuid>`, readiness probe via `GET /pubkey`, yield `(url, pubkey, role)`, SIGTERM on teardown + delete test namespace entries. Fast negative tests (malformed envelope, missing-tier-1, mixed-tier) use Flask `app.test_client()`. Forged-receipt test: separate tiny Flask app via subprocess returning known-invalid sig.

- **D-05 (Split ROADMAP's 2 plans into 3):**
  03-01: `photophore.dispatch` + CLI + AST lint. 03-02: pi-forge upgrade + describe-forge (both with init + /pubkey). 03-03: E2E + conformance harness + CI hook. Plan-phase MUST update ROADMAP.md plan list.

### Claude's Discretion

- Process-startup protocol for `subprocess_forge` fixture — recommended: `PIFORGE_READY port=<n>` stdout line; fixture polls until line appears or 5s timeout.
- AST-lint file location — recommended: `photophore/tools/ast_lint_network_isolation.py` invoked from `photophore/python/Makefile` and from CI.
- Conformance fixture corpus per forge.
- `describe-forge` keystore identity string — recommended: `"describe-forge"`.
- CI matrix — recommended: single matrix with `forge` axis = `[pi-forge, describe-forge]`.

### Deferred Ideas (OUT OF SCOPE)

- Forge pubkey rotation protocol (TOFU only; rotation = new channel).
- Auto-retry with backoff for retryable subcodes.
- Photophore daemon mode (no long-running process in v0.1).
- Conformance harness against external (non-reference) forges.
- `pi-forge job` support (spec v0.2).
- Job-envelope dispatch path in Photophore (spec v0.2).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DISP-01 | Full 9-step dispatch coordinator | §Architecture Patterns: 9-Step Flow; §Code Examples: dispatch coordinator skeleton |
| DISP-02 | Pre-dispatch audit write fail → no signing, no send | §Architecture Patterns: `AUDIT_FAILED_PRE` abort gate |
| DISP-03 | Receipt verification before audit-post; integration test with forged receipt | §Architecture Patterns: receipt verification; §Code Examples: Verifier usage |
| DISP-04 | Signing input = `thermocline.canonical.canonicalize` | §Standard Stack: `rfc8785` 0.1.4 verified; `canonicalize()` confirmed in `thermocline.canonical` |
| DISP-05 | Network-isolation AST lint — httpx forbidden outside dispatch | §Architecture Patterns: AST lint; §Code Examples: AST walk pattern |
| DISP-06 | Dispatch coordinator is async (`asyncio` + `httpx`); sync writes via `asyncio.to_thread` | §Standard Stack: `httpx` 0.28.1 AsyncClient verified; `asyncio.to_thread` verified |
| CLI-03 | `photophore dispatch` subcommand | §Architecture Patterns: CLI attachment point; §Code Examples: click command pattern |
| FORGE-01 | `pi-forge` upgraded to `thermocline-py` for all envelope handling | §Architecture Patterns: pi-forge upgrade targets; §Pitfalls: editable install drift |
| FORGE-02 | `pi-forge` regression-tested via `examples/task-100-digits.json` | §Code Examples: existing fixture shape confirmed |
| FORGE-03 | `describe-forge` with tier-1 shadow handling + templated description | §Architecture Patterns: describe-forge structure |
| FORGE-04 | Cross-suite conformance harness `forge_conformance` package | §Architecture Patterns: conformance harness; `jsonschema` 4.26.0 verified |
| FORGE-05 | Harness maps to Seamount 12-item conformance checklist | §Architecture Patterns: 12-item checklist mapping |
| POLICY-03 | `compare_result_against_policy()` called in dispatch step 9 | §POLICY-03 Closure: function exists and is fully implemented; only wiring is needed |
</phase_requirements>

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| 9-step dispatch coordination | API/Policy Engine (Photophore sovereign node) | — | Dispatch is entirely on the issuer side; no receiver involvement until HTTP send |
| Envelope signing | Identity Provider (platform keystore) | — | BrineProvider delegates to keystore per signature; dispatch calls `sign()` |
| Receipt verification | Identity Provider (BrineProvider.verify) → Policy Engine (dispatch coordinator) | — | `Verifier.verify()` returns `Receipt | None`; dispatch maps `None` to `RECEIPT_INVALID` |
| POLICY-03 check | Policy Engine (dispatch coordinator step 9) | — | `compare_result_against_policy()` called before audit-post |
| Audit writes (pre-dispatch + receipt) | Audit Log (SQLite Ring 1) via async shim | — | `asyncio.to_thread(audit.append, ...)` wraps sync write |
| Network I/O | Dispatch module only (`httpx.AsyncClient`) | — | AST lint enforces; sole cross-boundary HTTP in Photophore |
| Forge receipt signing | Identity Provider (forge-side BrineProvider) | — | Each forge holds its own keystore entry under `seamount.<role>` |
| Forge dispatch-sig verification | Identity Provider (forge-side, via `thermocline.identity.Verifier`) | — | Forge must verify dispatch signature before executing (FORGE conformance §2) |
| Tier-1 shadow templating | Forge (describe-forge application logic) | — | Deterministic; no policy engine involved at the forge |
| Conformance fixture validation | Conformance harness (standalone package) | — | `forge_conformance` POSTs envelopes, validates against JSON Schema, verifies receipts |
| AST network-isolation enforcement | Lint tool (AST visitor) | CI | Statically checked per file; CI gates on violation |
| Ephemeral forge keypair | Forge keystore (`seamount.<role>` keyring service) | — | `BrineProvider(keyring_service="seamount.piforge")` |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `httpx` | 0.28.1 [VERIFIED: pip show] | Async HTTP client for dispatch coordinator | Async-first, `AsyncClient` with timeout/retry control, `TimeoutException`/`ConnectError` hierarchy maps cleanly to DispatchError subcodes |
| `asyncio` | stdlib (Python 3.14.4) | Event loop; `asyncio.to_thread` for sync bridges | Zero-dep; `to_thread` available since 3.9; bridges Phase 2 sync core to async dispatch |
| `thermocline-py` | 0.3.1 [VERIFIED: importlib.metadata] | Envelope types, `BrineProvider`, `Verifier`, `canonicalize()` | Phase 1 locked dependency; all signing/verifying goes through here |
| `python-keyring` | 25.7.0 [VERIFIED: pip show] | Platform secure keystore (macOS Keychain on dev machine) | Spec-mandated; each forge uses distinct `keyring_service` string |
| `flask` | NOT in shared venv [VERIFIED: ModuleNotFoundError] | Forge HTTP server | Each forge has its own venv with Flask; must be installed per-forge venv |
| `pydantic` | 2.13.3 [VERIFIED: pip show] | `ResultPolicy`, `Task`, `TaskResult` envelope types from thermocline-py | Phase 1 locked; `ConfigDict(extra='forbid', frozen=True)` is load-bearing |
| `jsonschema` | 4.26.0 [VERIFIED: pip show] | Draft 2020-12 schema validation in conformance harness | Validates received envelopes against `thermocline/schema/*.schema.json` artifacts |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `rfc8785` | 0.1.4 [VERIFIED: pip show] | RFC 8785 JCS canonical JSON via `thermocline.canonical.canonicalize` | All signing input; never `json.dumps` |
| `hypothesis` | 6.152.4 [VERIFIED: pip show] | Property-based testing for smoke tests | Canonical-JSON round-trip smoke (deferred full property tests to Phase 4) |
| `pytest` | 9.0.3 [VERIFIED: pip show] | Test runner | All test files |
| `pytest-asyncio` | not verified in shared venv | Async test support for dispatch coordinator tests | Required for `async def test_*` in dispatch tests |
| `blake3` | 1.0.8 [VERIFIED: pip show] | Audit chain hash | Already used by audit log; no new use in dispatch |
| `PyNaCl` | 1.6.2 [VERIFIED: pip show] | ed25519 sign/verify backing for BrineProvider | Used indirectly via `thermocline.identity.BrineProvider` |
| `click` | >=8.3 [VERIFIED: pyproject.toml] | CLI framework | `photophore dispatch` adds to the existing click group |
| `pathspec` | >=1.1.1 [VERIFIED: pyproject.toml] | Glob matching for AST lint file-path allow-list | Use `"gitignore"` pattern name (not deprecated `"gitwildmatch"`) |

### Alternatives Considered

| Recommended | Alternative | Tradeoff |
|-------------|-------------|----------|
| `asyncio.to_thread` for sync bridges | `aiosqlite` | `to_thread` is zero-dep and keeps Phase 2 sync APIs unmodified (D-11); `aiosqlite` would require rewrites |
| `asyncio.to_thread` shim | Full async rewrite of Phase 2 | Phase 2 intentionally sync-first (D-11); rewrite would break all existing Phase 2 tests |
| subprocess.Popen for E2E tests | Docker-based forge isolation | Docker adds CI complexity; Popen is sufficient for local port isolation with ephemeral keystore namespaces |
| Flask `app.test_client()` for negative tests | Full subprocess for all tests | Subprocess is slow (~100ms+ startup); test_client is ms-fast for envelope-level rejection tests |
| stdlib `ast` module for lint | `libcst` or `pyflakes` | stdlib `ast` is zero-dep; walking `Import`/`ImportFrom` nodes is sufficient; no dependency bloat in lint tool |

**Installation for photophore pyproject.toml update (03-01):**
```bash
# Add to photophore/python/pyproject.toml dependencies:
# "httpx>=0.27",
# Add to dev dependencies:
# "pytest-asyncio>=0.23",
pip install -e /Users/dom/Projects/dom/photophore/python/
```

**pi-forge venv setup (03-02):**
```bash
python3 -m venv /Users/dom/Projects/dom/seamount/pi-forge/.venv
/Users/dom/Projects/dom/seamount/pi-forge/.venv/bin/pip install flask mpmath
/Users/dom/Projects/dom/seamount/pi-forge/.venv/bin/pip install -e /Users/dom/Projects/dom/thermocline/thermocline/python/
```

**describe-forge venv setup (03-02):**
```bash
python3 -m venv /Users/dom/Projects/dom/seamount/describe-forge/.venv
/Users/dom/Projects/dom/seamount/describe-forge/.venv/bin/pip install flask
/Users/dom/Projects/dom/seamount/describe-forge/.venv/bin/pip install -e /Users/dom/Projects/dom/thermocline/thermocline/python/
```

---

## Architecture Patterns

### System Architecture Diagram

```
[photophore dispatch CLI]
  ↓ asyncio.run(dispatch_async(...))
[photophore.dispatch.coordinator] ←── asyncio.to_thread shim
  │                                         │
  ├── Step 1: channels.show(channel_id) ─────┘ [channels.db / keystore]
  ├── Step 2: classifier.classify(blocks)         [pure CPU, sync]
  ├── Step 3: shadow.generate(blocks) → strip tier-0, replace tier-1
  ├── Step 4: policy.author(channel, draft) → ResultPolicy
  ├── Step 5: audit.append(pre_dispatch_event) ──→ [audit.db]  ← ABORT GATE
  ├── Step 6: identity.sign(envelope) ──────────→ [platform keystore]
  ├── Step 7: httpx.AsyncClient.post(forge_url) ──→ [forge HTTP server]
  │                                                      │
  │           [pi-forge / describe-forge]                │
  │             ↓ validate dispatch_signature            │
  │             ↓ BrineProvider.verify(envelope)         │
  │             ↓ execute task                           │
  │             ↓ BrineProvider.sign(receipt)            │
  │             → task_result envelope ─────────────────┘
  │
  ├── Step 8: Verifier.verify(result, receipt_sig) → Receipt | None
  │             └── None → DispatchError.RECEIPT_INVALID (no audit-post)
  │             └── policy.compare_result_against_policy(result, policy)
  │                   → False → DispatchError.POLICY_VIOLATED (no audit-post)
  └── Step 9: audit.append(receipt_event) ──────→ [audit.db]  ← REPLAY-SAFE
```

### Recommended Project Structure

```
photophore/python/src/photophore/
├── dispatch/              # NEW — Plan 03-01
│   ├── __init__.py       # public: dispatch_async(), DispatchError, DispatchSubcode
│   ├── _coordinator.py   # 9-step async flow implementation
│   ├── _aio.py           # ~20 LOC asyncio.to_thread shim wrappers
│   └── _errors.py        # DispatchError(PhotophoreError) + DispatchSubcode(StrEnum)
├── cli/
│   └── dispatch_cmds.py  # NEW — photophore dispatch subcommand
├── tools/
│   └── ast_lint_network_isolation.py  # NEW — Plan 03-01

seamount/
├── pi-forge/             # MODIFIED — Plan 03-02
│   ├── server.py         # Add GET /pubkey, add init subcommand, upgrade handle_task
│   ├── envelope.py       # RETIRED — replaced by thermocline-py calls
│   ├── forge_identity.py # NEW — BrineProvider(keyring_service="seamount.piforge")
│   └── pyproject.toml    # NEW — add thermocline-py dependency
│
├── describe-forge/       # NEW — Plan 03-02
│   ├── server.py         # Flask app, GET /pubkey, POST /task, describe logic
│   ├── describe.py       # Templated description from tier-1 shadows
│   └── pyproject.toml
│
└── conformance/          # NEW — Plan 03-03
    └── forge_conformance/
        ├── __init__.py
        ├── __main__.py   # CLI entry: python -m forge_conformance --target <url> --role <role>
        ├── _harness.py   # POST fixtures, validate JSON Schema, verify receipts
        └── _checklist.py # Map results to Seamount 12-item conformance checklist
```

### Pattern 1: asyncio.to_thread Shim (DISP-06, D-11)

**What:** ~20 LOC module wrapping Phase 2 sync APIs for use inside the async dispatch coordinator.

**When to use:** Every Phase 2 sync call inside `_coordinator.py`. Pure-CPU calls (classify, shadow.generate) can run in threads without concern; SQLite calls (audit.append) MUST be in threads to avoid blocking the event loop.

**Example:**
```python
# Source: Phase 2 D-11, verified asyncio.to_thread behavior
# photophore/dispatch/_aio.py

import asyncio
from typing import Any

from ..audit._store import AuditLog
from ..audit._types import AuditEntry
from ..channels._store import ChannelStore
from ..channels._types import Channel


async def audit_append_async(log: AuditLog, entry: AuditEntry) -> str:
    """Async wrapper: audit.append via asyncio.to_thread (DISP-06, D-11)."""
    return await asyncio.to_thread(log.append, entry)


async def channel_show_async(store: ChannelStore, channel_id: str) -> Channel:
    """Async wrapper: channels.show via asyncio.to_thread."""
    return await asyncio.to_thread(store.show, channel_id)


# Note: classify() and shadow.generate() are CPU-bound but
# also wrapped via to_thread to keep coordinator fully non-blocking.
```

**Footguns:**
- `asyncio.to_thread` runs in the default executor (ThreadPoolExecutor). SQLite connections are NOT thread-safe when shared; each `to_thread` call must use a connection opened in the thread OR the `AuditLog` must serialize internally. The existing `AuditLog` opens a connection per call (check `_store.py` — use `check_same_thread=False` or per-call connection if needed).
- Do not share a single `httpx.AsyncClient` across concurrent dispatches without an explicit `async with` guard; use context manager per dispatch.

### Pattern 2: DispatchError with StrEnum Subcodes (D-03)

**What:** Single exception class extending `PhotophoreError`, with `StrEnum` for subcodes, `retryable: bool` advisory field.

**When to use:** Raised at every step of the 9-step flow when the step fails; caught in the CLI command to set exit code 6 and format the human/JSON error message.

**Example:**
```python
# Source: Phase 2 D-03, D-14; Python 3.11+ StrEnum
# photophore/dispatch/_errors.py

from enum import StrEnum
from ..errors import PhotophoreError


class DispatchSubcode(StrEnum):
    CHANNEL_RESOLVE_FAILED = "CHANNEL_RESOLVE_FAILED"
    CLASSIFICATION_FAILED = "CLASSIFICATION_FAILED"
    SHADOW_GENERATION_FAILED = "SHADOW_GENERATION_FAILED"
    POLICY_AUTHORING_FAILED = "POLICY_AUTHORING_FAILED"
    AUDIT_FAILED_PRE = "AUDIT_FAILED_PRE"
    SIGNING_FAILED = "SIGNING_FAILED"
    TRANSPORT_TIMEOUT = "TRANSPORT_TIMEOUT"
    TRANSPORT_REFUSED = "TRANSPORT_REFUSED"
    RECEIPT_MALFORMED = "RECEIPT_MALFORMED"
    RECEIPT_INVALID = "RECEIPT_INVALID"
    POLICY_VIOLATED = "POLICY_VIOLATED"
    AUDIT_FAILED_POST = "AUDIT_FAILED_POST"


_RETRYABLE = {
    DispatchSubcode.AUDIT_FAILED_PRE,
    DispatchSubcode.SIGNING_FAILED,
    DispatchSubcode.TRANSPORT_TIMEOUT,
    DispatchSubcode.TRANSPORT_REFUSED,
    DispatchSubcode.AUDIT_FAILED_POST,
}


class DispatchError(PhotophoreError):
    def __init__(
        self,
        message: str,
        *,
        subcode: DispatchSubcode,
        stage: int,
        envelope_id: str | None = None,
        channel_id: str | None = None,
        audit_entry_hash: str | None = None,
    ) -> None:
        super().__init__(message, code=str(subcode))
        self.subcode = subcode
        self.stage = stage
        self.retryable = subcode in _RETRYABLE
        self.envelope_id = envelope_id
        self.channel_id = channel_id
        self.audit_entry_hash = audit_entry_hash
```

### Pattern 3: httpx Async Dispatch with Timeout/Error Mapping (DISP-01, DISP-06)

**What:** `httpx.AsyncClient.post()` with `httpx.Timeout` config; exception hierarchy maps to DispatchError subcodes.

**Error mapping verified against httpx 0.28.1:**
- `httpx.TimeoutException` (base for `ReadTimeout`, `ConnectTimeout`, `WriteTimeout`, `PoolTimeout`) → `TRANSPORT_TIMEOUT`
- `httpx.ConnectError` (base class: `httpx.NetworkError`) → `TRANSPORT_REFUSED`
- Any other `httpx.HTTPError` → `TRANSPORT_REFUSED` (conservative)

**Example:**
```python
# Source: httpx docs, verified against httpx 0.28.1 exception hierarchy
import httpx

async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
    try:
        response = await client.post(
            forge_url,
            json=signed_envelope,
            headers={"Content-Type": "application/json"},
        )
    except httpx.TimeoutException as exc:
        raise DispatchError(
            f"forge unreachable: {exc}",
            subcode=DispatchSubcode.TRANSPORT_TIMEOUT,
            stage=7,
            envelope_id=envelope_id,
            channel_id=channel_id,
            audit_entry_hash=pre_audit_hash,
        ) from exc
    except httpx.ConnectError as exc:
        raise DispatchError(
            f"forge connection refused: {exc}",
            subcode=DispatchSubcode.TRANSPORT_REFUSED,
            stage=7,
            ...
        ) from exc
```

### Pattern 4: BrineProvider Multi-Namespace (D-01, FORGE-01)

**What:** Multiple `BrineProvider` instances with distinct `keyring_service` strings coexist in the same process. Verified: `keyring.set_password(service_name, username, password)` is keyed on `(service_name, username)` — distinct service names are separate namespaces. macOS Keychain confirms this (verified `keyring.backends.macOS.Keyring`).

**Service namespaces:**
- `"thermocline.brine"` — sovereign node's own signing key (Photophore default from Phase 1)
- `"seamount.piforge"` — pi-forge's signing key
- `"seamount.describeforge"` — describe-forge's signing key
- `"seamount.piforge.test-<uuid>"` — ephemeral test namespace (subprocess_forge fixture)
- `"seamount.describeforge.test-<uuid>"` — ephemeral test namespace

**Example forge init pattern:**
```python
# Source: thermocline.identity.BrineProvider verified in Phase 1
from thermocline.identity import BrineProvider

FORGE_KEYRING_SERVICE = "seamount.piforge"
FORGE_IDENTITY = "pi-forge"

def forge_init(identity: str = FORGE_IDENTITY) -> None:
    """Idempotent keypair bootstrap (D-01)."""
    provider = BrineProvider(keyring_service=FORGE_KEYRING_SERVICE)
    try:
        provider.generate(identity=identity)
        print(f"Keypair created for {identity!r}")
    except IdentityError as exc:
        if exc.code == "IDENTITY_ALREADY_EXISTS":
            print(f"Keypair already exists for {identity!r} (no-op)")
        else:
            raise
```

### Pattern 5: GET /pubkey Endpoint (D-01)

**What:** Unauthenticated read-only endpoint on each forge returning the public key in hex.

**Example:**
```python
# Source: Phase 1 BrineProvider.public_key() API
@app.get("/pubkey")
def pubkey():
    provider = BrineProvider(keyring_service=FORGE_KEYRING_SERVICE)
    pub_bytes = provider.public_key(identity=FORGE_IDENTITY)  # 32 bytes
    return jsonify({
        "identity": FORGE_IDENTITY,
        "key_scheme": "brine",
        "pubkey": pub_bytes.hex(),
    })
```

**Sovereign-side TOFU registration (in `channel new --fetch-pubkey-from`):**
```python
# photophore/cli/channel_cmds.py addition
import httpx

resp = httpx.get(f"{fetch_url}/pubkey", timeout=10.0)  # sync; one-time setup call
resp.raise_for_status()
data = resp.json()
pubkey_hex = data["pubkey"]
pubkey_bytes = bytes.fromhex(pubkey_hex)
# Call register_public_key via the sovereign's BrineProvider:
sovereign_provider.register_public_key(
    identity=channel.remote_node,
    verify_key=pubkey_bytes,
)
```

Note: this is a one-time sync `httpx.get()` in the CLI (not the async dispatch coordinator). The AST lint allows-list must include `photophore.cli.channel_cmds` for this single carve-out.

### Pattern 6: AST Lint for Network-Isolation Contract (DISP-05)

**What:** stdlib `ast` module visitor walking each Python source file, rejecting `import httpx`, `import requests`, `import aiohttp` in modules outside the allow-list.

**Verified approach:**
```python
# Source: Phase 1 AST-lint precedent (check_no_json_dumps); verified with stdlib ast
# photophore/tools/ast_lint_network_isolation.py

import ast, sys
from pathlib import Path

FORBIDDEN = {"httpx", "requests", "aiohttp"}
ALLOWLIST_PATHS = {
    "photophore/dispatch",
    "photophore/cli/dispatch_cmds.py",
    "photophore/cli/channel_cmds.py",  # single carve-out for --fetch-pubkey-from
}

def check_file(path: Path) -> list[str]:
    """Return list of violation messages for this file."""
    # Check if file is in allow-list
    for allowed in ALLOWLIST_PATHS:
        if allowed in str(path):
            return []
    source = path.read_text()
    tree = ast.parse(source, filename=str(path))
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top in FORBIDDEN:
                    violations.append(
                        f"{path}:{node.lineno}: forbidden import {alias.name!r}"
                    )
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.split(".")[0] in FORBIDDEN:
                violations.append(
                    f"{path}:{node.lineno}: forbidden import from {node.module!r}"
                )
    return violations
```

**Registration:** Invoke from `Makefile` as `python photophore/tools/ast_lint_network_isolation.py src/` and from CI as a step before `pytest`.

### Pattern 7: subprocess_forge Fixture (D-04)

**What:** pytest fixture that spawns a real Flask forge process on an ephemeral port with a test-scoped keystore namespace.

**Ephemeral port allocation:** `socket.socket(); s.bind(('', 0)); port = s.getsockname()[1]; s.close()` — then pass `--port <port>` to the forge. The port is free between `s.close()` and forge startup; on macOS this race is acceptable for tests.

**Readiness probe:** Poll `GET /pubkey` until 200 or 5s timeout (not `GET /health`, because `GET /pubkey` proves the brine key is ready, which is the actual readiness gate).

**Example:**
```python
# Source: D-04 design; subprocess.Popen + httpx.get verified in Python 3.14
import uuid, subprocess, time, httpx, socket, pytest
from pathlib import Path

@pytest.fixture
def subprocess_forge(tmp_path, request):
    """Hybrid subprocess fixture: spawns a real forge process with ephemeral keystore."""
    role = request.param  # "pi-forge" or "describe-forge"
    test_ns = f"seamount.{role.replace('-', '')}.test-{uuid.uuid4().hex[:8]}"

    # Find free port
    with socket.socket() as s:
        s.bind(('', 0))
        port = s.getsockname()[1]

    forge_dir = Path(f"/path/to/seamount/{role}")
    venv_python = forge_dir / ".venv/bin/python3"

    # Step 1: init (creates keypair in test namespace)
    subprocess.run(
        [str(venv_python), "-m", role.replace("-", "_"), "init",
         "--keyring-service", test_ns],
        cwd=forge_dir, check=True, timeout=10
    )

    # Step 2: spawn server
    proc = subprocess.Popen(
        [str(venv_python), "-m", role.replace("-", "_"), "serve",
         "--port", str(port), "--keyring-service", test_ns],
        cwd=forge_dir,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )

    # Step 3: readiness probe via GET /pubkey
    url = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + 5.0
    pubkey_hex = None
    while time.monotonic() < deadline:
        try:
            resp = httpx.get(f"{url}/pubkey", timeout=1.0)
            if resp.status_code == 200:
                pubkey_hex = resp.json()["pubkey"]
                break
        except Exception:
            time.sleep(0.1)
    else:
        proc.terminate()
        raise RuntimeError(f"{role} did not become ready within 5s on port {port}")

    yield url, pubkey_hex, role

    # Teardown: SIGTERM + namespace cleanup
    proc.terminate()
    proc.wait(timeout=5)
    # Delete test keystore entries via keyring API
    import keyring
    try:
        keyring.delete_password(test_ns, role.replace("-", ""))
    except Exception:
        pass
```

### Pattern 8: POLICY-03 Closure (Dispatch Step 9)

**What:** `compare_result_against_policy()` is fully implemented in `photophore.policy._author`. Phase 3 wires it into the dispatch coordinator at step 8b (after receipt verification, before audit-post).

**Exact API (verified from source):**
```python
# Source: photophore/python/src/photophore/policy/_author.py — confirmed
from photophore.policy import compare_result_against_policy, ResultPolicy

# In dispatch coordinator step 8b:
complies = compare_result_against_policy(
    received_result=result_dict,   # dict with "persisted_fields" and "returned_fields"
    authored_policy=authored_policy,  # ResultPolicy from step 4
)
if not complies:
    raise DispatchError(
        "result violates authored result_policy",
        subcode=DispatchSubcode.POLICY_VIOLATED,
        stage=8,
        envelope_id=envelope_id,
        channel_id=channel_id,
        audit_entry_hash=pre_audit_hash,  # pre-dispatch audit hash only
    )
```

**Important:** `compare_result_against_policy` inspects `received_result.get("persisted_fields", [])` and `received_result.get("returned_fields", [])`. The forge result dict from the forge's `task_result` envelope shape does NOT have these keys by default — the dispatch coordinator must extract/derive them from the result envelope before calling. For v0.1, this means either (a) the forge returns a `persisted_fields`/`returned_fields` metadata block in `provenance`, or (b) the dispatcher infers from `outputs` keys. The v0.1 approach should be documented clearly in the plan.

**Recommendation for v0.1:** Define `persisted_fields = list(result.get("outputs", {}).keys())` as a conservative approximation — everything in `outputs` is treated as potentially-persisted. This is the safe direction (false positives are violations, but in the POLICY-VIOLATED direction which is the safe failure mode). The policy-violation negative test (Plan 03-03) needs to construct a result that violates the authored policy under this scheme.

### Pattern 9: AT-A1 Behavioral Wire-In (Plan 03-01)

**What:** The AT-A1 fixture at `thermocline/thermocline/conformance/invalid/AT-A1-channel-impersonation.json` carries `_phase_wired: 3`. The dispatch coordinator in step 1 must check that the envelope's declared `key_scheme` matches the keystore-stored `key_scheme` for the resolved channel. Mismatch → `DispatchError.CHANNEL_RESOLVE_FAILED`.

**Fixture payload structure (verified from file):**
```json
{
  "_at_surface": "AT-A1",
  "_expect_error_code": "CHANNEL_IMPERSONATION",
  "_phase_wired": 3,
  "envelope": {
    "channel_id": "at-a1-channel-impersonated-id",
    "dispatch_signature": {"scheme": "brine", ...}
  },
  "violating_condition": {
    "keystore_key_scheme": "none",
    "envelope_declared_key_scheme": "brine"
  }
}
```

**Dispatch step 1 implementation:**
```python
# In _coordinator.py step 1
channel = await channel_show_async(channel_store, channel_id)
envelope_scheme = envelope.get("dispatch_signature", {}).get("key_scheme")
if envelope_scheme and envelope_scheme != channel.key_scheme:
    raise DispatchError(
        f"key_scheme mismatch: envelope declares {envelope_scheme!r} "
        f"but channel {channel_id!r} was created with {channel.key_scheme!r}",
        subcode=DispatchSubcode.CHANNEL_RESOLVE_FAILED,
        stage=1,
        ...
    )
```

**Integration test (Plan 03-03):** Load the AT-A1 fixture JSON, create a mock channel with `key_scheme="none"`, run dispatch, assert `DispatchError.subcode == CHANNEL_RESOLVE_FAILED`.

### Pattern 10: describe-forge Normative Template String (D-02, FORGE-03)

**What:** The templated description string is normative per CONTEXT.md D-02.

**Exact string (treat as immutable spec):**
```
"This forge received a shadow of type '<content_type>' with relevance <relevance>."
```

**Python implementation:**
```python
def _describe_shadow(shadow: dict) -> dict:
    content_type = shadow["content_type"]
    relevance = shadow["relevance"]
    return {
        "shadow_id": shadow["shadow_id"],
        "content_type": content_type,
        "relevance": relevance,
        "description": (
            f"This forge received a shadow of type {content_type!r} "
            f"with relevance {relevance}."
        ),
    }
```

Note: `{relevance}` is the raw float value from the shadow block. Do not round, truncate, or reformat. The test must assert exact string equality.

### Pattern 11: Conformance Harness Package (FORGE-04, FORGE-05)

**What:** `forge_conformance` Python package that loads fixtures from `thermocline/conformance/`, POSTs to a target forge URL, validates responses against `thermocline/schema/*.schema.json`, verifies receipt signatures, and maps results to Seamount's 12-item conformance checklist.

**CLI invocation (from CONTEXT.md):**
```bash
python -m forge_conformance --target http://localhost:5100 --role pi-forge
python -m forge_conformance --target http://localhost:5200 --role describe-forge
```

**12-item checklist mapping (Seamount README §"Forge Conformance Requirements"):**
1. Envelope Handling — schema validate + version check
2. Signature Verification — dispatch_sig verify
3. Privacy Fence / Logging — no-persistence assertion (behavioral, honor-system in v0.1)
4. Statelessness — no persistent state between requests
5. Task Execution — task type routing
6. Job Execution — not applicable for task-only forges
7. Receipt Signatures — receipt_signature block shape + sig field non-null
8. Error and Halt Codes — minimum required error codes present
9-12: AT-E1..AT-E5 surfaces (fixture-driven)

**Fixture loading:**
```python
# Source: thermocline/thermocline/conformance/MANIFEST.yaml schema; jsonschema 4.26.0
from pathlib import Path
import json, jsonschema

CONFORMANCE_ROOT = Path("/path/to/thermocline/thermocline/conformance")
SCHEMA_ROOT = Path("/path/to/thermocline/thermocline/schema")

def load_valid_fixtures():
    manifest_path = CONFORMANCE_ROOT / "valid" / "MANIFEST.yaml"
    # ... load and yield fixtures
```

### Anti-Patterns to Avoid

- **`json.dumps` for signing input:** Never. Always `thermocline.canonical.canonicalize()`. The lint already enforces this for the Thermocline library; the dispatch coordinator and forges must also comply.
- **Sharing SQLite connections across threads:** Phase 2's `AuditLog` likely opens per-call connections. Verify before wrapping in `asyncio.to_thread`. If not, pass `check_same_thread=False` to `sqlite3.connect()`.
- **Caching the `Receipt` object:** `Receipt` is a frozen dataclass and can be passed around, but it must only be constructed via `Verifier.verify()`. No mock receipts in tests — use `app.test_client()` with a real brine verify instead.
- **Echoing inline content in describe-forge:** Mixed-tier handling must explicitly skip tier-2 blocks. No reflection of public content in describe-forge output (D-02 privacy constraint).
- **Using `"gitwildmatch"` in pathspec:** Deprecated — use `"gitignore"` (Phase 2 LEARNINGS lesson).
- **`CliRunner(mix_stderr=True)` for JSON tests:** Phase 2 LEARNINGS: error lines bleed into output. Use `CliRunner(mix_stderr=False)` for all dispatch CLI tests.
- **Synthetic flat-dict test envelopes:** Phase 1 LEARNINGS: these mask production lookup bugs. For dispatch tests, use real `thermocline.Task` model instances serialized via `model.model_dump(mode="json")`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Ed25519 sign/verify | Custom ed25519 impl | `thermocline.identity.BrineProvider` + `Verifier` | Phase 1 locked API; handles keystore, nonce, scheme dispatch |
| Canonical JSON for signing | `json.dumps(sort_keys=True)` | `thermocline.canonical.canonicalize()` | RFC 8785 / JCS; cross-impl signature compatibility |
| Envelope type validation | Custom dict schema checking | `thermocline` Pydantic models + `Task.model_validate()` | `ConfigDict(extra='forbid', frozen=True)` catches AT-C6; Pydantic v2 generates JSON Schema |
| BLAKE3 chain hash | Custom hash | `blake3` package (already in Phase 2 audit) | Faster than SHA-256; `algo_version="blake3-v1"` field for forward migration |
| Platform keystore access | File-based key storage | `python-keyring` 25.7.0 | Spec-mandated; macOS Keychain verified functional |
| JSON Schema validation in conformance harness | Custom schema validator | `jsonschema.Draft202012Validator` (4.26.0 verified) | Draft 2020-12 schemas in `thermocline/schema/`; `$defs`, `$ref` handling built-in |
| Glob pattern matching for AST lint allow-list | Custom path matching | `pathlib.Path.is_relative_to()` or string containment | Simpler than glob for the allow-list; lint has only ~3 allowed paths |

**Key insight:** The entire cryptographic surface (key generation, signing, verification, keystore) is fully encapsulated in `thermocline-py` Phase 1. Phase 3's only job is to wire the `BrineProvider` at the right `keyring_service` string. Any custom crypto is both unnecessary and a security regression.

---

## POLICY-03 Closure

The `compare_result_against_policy()` function is **fully implemented** in `photophore/python/src/photophore/policy/_author.py` and exported from `photophore.policy`. Confirmed from source read.

**Function signature:**
```python
def compare_result_against_policy(
    received_result: Mapping[str, Any],
    authored_policy: ResultPolicy,
) -> bool:
    # Returns True = complies, False = violation
```

**Phase 3 wiring obligation:**
- Call in dispatch coordinator between step 8a (receipt-signature verification) and step 9 (audit-post).
- If `False` → raise `DispatchError(subcode=POLICY_VIOLATED)` → no audit-post.
- Plan 03-01 frontmatter MUST list `POLICY-03` in requirements (per Phase 2 LEARNINGS POLICY-03 partial-closure obligation).

**v0.1 result-fields derivation:** The `received_result` dict needs `persisted_fields` and `returned_fields` keys. These are not standard fields in the `task_result` envelope schema. For v0.1: derive from `result_envelope["outputs"].keys()` treating all output keys as returned (conservative). The policy-violation negative test in Plan 03-03 must be designed around this derivation.

---

## Common Pitfalls

### Pitfall 1: Stale `.pth` Editable Install in Forge Venvs

**What goes wrong:** `import thermocline` fails in the forge venv because the editable `.pth` file points to a deleted worktree path.

**Why it happens:** Phase 2 LEARNINGS surprise #10 — executor sessions create worktrees that get cleaned up, leaving stale `.pth` references. Forge venvs are created by plan executors who may run in worktrees.

**How to avoid:** Every plan task that creates or uses a forge venv must run `pip install -e /Users/dom/Projects/dom/thermocline/thermocline/python/` with the CANONICAL path (not a worktree-relative path). Add as Wave 0 task.

**Warning signs:** `ImportError: No module named 'thermocline'` inside a forge venv at any point.

### Pitfall 2: SQLite Thread Safety in asyncio.to_thread

**What goes wrong:** `ProgrammingError: SQLite objects created in a thread can only be used in that same thread` when the `AuditLog` holds a persistent connection object and `asyncio.to_thread` runs it in a different thread.

**Why it happens:** Python's `sqlite3` module has thread-affinity for connection objects by default.

**How to avoid:** Verify `AuditLog._store.py` connection lifetime. If connections are per-method (open → query → close), `to_thread` is safe. If a connection is stored as an instance attribute, pass `check_same_thread=False` to `sqlite3.connect()` OR open a new connection per `to_thread` call.

**Warning signs:** `ProgrammingError` in tests that call `audit_append_async` from an async test function.

### Pitfall 3: Receipt Construction Outside verify()

**What goes wrong:** Tests construct `Receipt(...)` directly to avoid running real crypto, defeating Phase 1 D-01 sentinel mechanism and masking the `verify()` path.

**Why it happens:** Direct construction looks simpler for unit tests.

**How to avoid:** For unit tests of the dispatch coordinator: mock `Verifier.verify` to return a pre-constructed `Receipt` created in a trusted test helper that DOES call `BrineProvider.verify()` with a real in-memory keyring. For integration tests: use `app.test_client()` with real brine keys in test keystore namespace. Never use `# type: ignore` to bypass the `_token` parameter.

**Warning signs:** `TypeError: Receipt is constructible only by IdentityProvider.verify()` in tests — this is the system working correctly; don't suppress it.

### Pitfall 4: describe-forge Reflecting Inline Content

**What goes wrong:** Mixed-tier handling code iterates all `context[]` blocks and accidentally includes tier-2 inline `content` strings in the description output.

**Why it happens:** Easy to write `for block in context: if block.get("shadow"): describe...` but forget to explicitly skip tier-2.

**How to avoid:** Filter explicitly: `tier1_shadows = [b["shadow"] for b in context if b.get("tier") == 1 and "shadow" in b]`. The describe loop operates only on `tier1_shadows`. Any other block type is counted for `provenance.tiers_present` only.

**Warning signs:** Integration test shows forge returning `outputs.descriptions` entries that reference content_type values from inline blocks, not shadow blocks.

### Pitfall 5: CliRunner Mix-Stderr in Dispatch CLI Tests

**What goes wrong:** `json.loads(result.output)` fails because CliRunner appended error lines after the JSON in the exit-code-6 path.

**Why it happens:** Phase 2 LEARNINGS: `CliRunner(mix_stderr=True)` is the default.

**How to avoid:** All dispatch CLI tests use `CliRunner(mix_stderr=False)`. Applies to all success and error path tests.

**Warning signs:** `json.decoder.JSONDecodeError` in dispatch CLI tests on the error-code-6 path.

### Pitfall 6: Ephemeral Port Race in subprocess_forge Fixture

**What goes wrong:** Port allocation via `socket.bind(('', 0))` then `socket.close()` leaves a window where another process grabs the port before the forge starts.

**Why it happens:** OS reuses ports in LIFO order; concurrent test runs or system daemons can grab the freed port.

**How to avoid:** The forge server must actually bind the port via `FORGE_PORT=<port>` env var (not use a default). The fixture should pass `--port <port>` explicitly. For macOS this race is rare enough in CI to be acceptable without further mitigation.

**Warning signs:** `OSError: [Errno 48] Address already in use` on forge startup during parallel test runs.

### Pitfall 7: `compare_result_against_policy` Receives Wrong Field Names

**What goes wrong:** POLICY-03 negative test always passes (never detects a violation) because `received_result` doesn't have `persisted_fields`/`returned_fields` keys — `compare_result_against_policy` gets empty sets and everything looks compliant.

**Why it happens:** The `task_result` envelope schema doesn't include `persisted_fields`/`returned_fields`; the dispatch coordinator must derive them from `outputs`.

**How to avoid:** Implement derivation explicitly in the dispatch coordinator before calling `compare_result_against_policy`. Document the derivation rule in the plan. The policy-violation negative test (Plan 03-03) must be designed to trigger an actual violation under the chosen derivation rule.

**Warning signs:** Policy-violation test passes when using a result that should violate; check the `received_result` dict passed to `compare_result_against_policy`.

---

## Code Examples

### Receipt Verification in Dispatch Step 8

```python
# Source: thermocline.identity.Verifier verified from identity.py source
from thermocline.identity import Verifier, BrineProvider

# Verifier setup (once at coordinator init or per-dispatch):
verifier = Verifier()
verifier.register(BrineProvider(keyring_service="thermocline.brine"))

# In dispatch step 8:
receipt_sig_block = result_dict.get("receipt_signature", {})
sig_bytes = bytes.fromhex(receipt_sig_block.get("sig", ""))
from thermocline.schemes import KeyScheme
from thermocline.identity import Signature

sig = Signature(
    scheme=KeyScheme.BRINE,
    bytes_=sig_bytes,
    signer_identity=receipt_sig_block.get("node_id", ""),
)
receipt = verifier.verify(envelope=result_dict, signature=sig)
if receipt is None:
    raise DispatchError(
        "receipt signature verification failed",
        subcode=DispatchSubcode.RECEIPT_INVALID,
        stage=8,
        ...
    )
# receipt is a Receipt instance (frozen dataclass, verify-only constructor)
# receipt.signature_hash is available for audit logging
```

### Forge Dispatch-Signature Verification (pi-forge upgrade)

```python
# Source: thermocline.identity.Verifier; FORGE conformance §2
# Replaces the _verify_brine stub in pi-forge/envelope.py

from thermocline.identity import BrineProvider, Verifier, Signature
from thermocline.schemes import KeyScheme

def verify_dispatch_signature(body: dict, sig_block: dict, keyring_service: str) -> None:
    """Real brine dispatch-signature verification (replaces _verify_brine stub)."""
    scheme = sig_block.get("key_scheme")
    if scheme == "none":
        return  # dev mode; no verification
    if scheme != "brine":
        raise EnvelopeError("SIGNATURE_INVALID", f"Unrecognized key_scheme: {scheme!r}")

    node_id = sig_block.get("node_id", "")
    sig_hex = sig_block.get("sig", "")
    if not sig_hex:
        raise EnvelopeError("SIGNATURE_INVALID", "dispatch_signature.sig is empty")

    provider = BrineProvider(keyring_service=keyring_service)
    verifier = Verifier()
    verifier.register(provider)

    sig = Signature(
        scheme=KeyScheme.BRINE,
        bytes_=bytes.fromhex(sig_hex),
        signer_identity=node_id,
    )
    receipt = verifier.verify(envelope=body, signature=sig)
    if receipt is None:
        raise EnvelopeError("SIGNATURE_INVALID", "dispatch signature verification failed")
```

### pi-forge Upgrade: _sign_receipt Replacement

```python
# Source: thermocline.identity.BrineProvider.sign() API; thermocline.canonical.canonicalize()
# Replaces _sign_receipt stub in pi-forge/envelope.py

from thermocline.identity import BrineProvider
from thermocline.canonical import canonicalize

def sign_receipt(
    result_dict: dict,
    keyring_service: str,
    forge_identity: str,
) -> dict:
    """Real brine receipt signing (replaces _sign_receipt stub)."""
    provider = BrineProvider(keyring_service=keyring_service)
    sig = provider.sign(envelope=result_dict, signer_identity=forge_identity)
    return {
        "key_scheme": "brine",
        "node_id": forge_identity,
        "envelope_id": result_dict.get("envelope_id"),
        "result_id": result_dict.get("result_id"),
        "inputs_received": result_dict.get("provenance", {}).get("shadows_received", []),
        "timestamp": result_dict.get("completed_at"),
        "sig": sig.bytes_.hex(),
    }
```

### Conformance Harness: Checklist Mapping

```python
# Source: Seamount README §"Forge Conformance Requirements" (12 items)
CHECKLIST = [
    ("1-envelope-handling",   "Envelope schema validation and version rejection"),
    ("2-sig-verification",    "dispatch_signature verification before processing"),
    ("3-privacy-fence",       "No persistent logging of context/prompts/outputs"),
    ("4-statelessness",       "No state retained between requests"),
    ("5-task-execution",      "Task type routing and TASK_TYPE_UNAVAILABLE error"),
    ("6-job-execution",       "Job execution engine (N/A for task-only forges)"),
    ("7-receipt-signatures",  "receipt_signature block with valid sig on every result"),
    ("8-error-codes",         "Minimum required error codes present in rejections"),
    ("AT-E1",                 "Malicious envelope payload rejection"),
    ("AT-E2",                 "Resource exhaustion / DoS handling"),
    ("AT-E3",                 "Tool escape / shell breakout prevention"),
    ("AT-E4",                 "Forge impersonation prevention (receipt sig verify)"),
    ("AT-E5",                 "Timing side-channel mitigation"),
]
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `pi-forge` stubs (`_verify_brine`, `_sign_receipt`) | Real `BrineProvider` sign/verify via `thermocline-py` | Phase 3 (this phase) | Closes FORGE-01; removes the only security gap in the reference impl |
| `key_scheme="none"` as default in `pi-forge` | `key_scheme="brine"` as default; `FORGE_KEY_SCHEME=none` for dev mode | Phase 3 | Forges now ship with real crypto by default |
| No `describe-forge` reference impl | New `describe-forge` exercising tier-1 shadow handling | Phase 3 | First forge that exercises the core privacy primitive (shadow → description) |
| All dispatch errors as untyped exceptions | `DispatchError` with `StrEnum` subcodes + `retryable` advisory | Phase 3 | Machine-readable error surfacing; operator retry decisions |
| No network-isolation enforcement | Custom AST lint as CI gate | Phase 3 | DISP-05 closes; network I/O structurally isolated to dispatch module |

**Deprecated/outdated in this phase:**
- `pi-forge/envelope.py:_verify_brine` (lines 87–99) — retired by FORGE-01; replaced by `thermocline.identity.Verifier`
- `pi-forge/envelope.py:_sign_receipt` (lines 139–165) — retired by FORGE-01; replaced by `BrineProvider.sign()`
- `key_scheme="none"` as a production default — still valid for dev mode (`FORGE_KEY_SCHEME=none`) but not the default

---

## Assumptions Log

> All claims tagged `[ASSUMED]` in this research. The planner and discuss-phase use this section to identify decisions that need user confirmation.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `AuditLog` opens per-method SQLite connections (not a persistent connection attribute), making it safe for `asyncio.to_thread` without `check_same_thread=False` | §Common Pitfalls: Pitfall 2 | If wrong: `ProgrammingError` in async audit writes; fix by adding `check_same_thread=False` to the connection open in `_store.py` |
| A2 | Flask is not installed in the shared myenv (`/Users/dom/myenv`) — confirmed by `ModuleNotFoundError: No module named 'flask'`; each forge must use its own venv | §Standard Stack | If wrong: forge venvs are unnecessary; but the finding is `[VERIFIED]` so this assumption is actually a confirmed fact |
| A3 | The POLICY-03 `compare_result_against_policy` derivation approach (treating `outputs.keys()` as `returned_fields`) is acceptable for v0.1 negative testing | §POLICY-03 Closure | If wrong: the policy-violation test may not trigger under the conservative derivation; fix by adding explicit `persisted_fields`/`returned_fields` fields to forge results |
| A4 | `pytest-asyncio` is not yet installed in the photophore test environment (not in pyproject.toml) — required for `async def test_*` dispatch tests | §Standard Stack | If wrong: async dispatch tests fail with collection error; fix by adding `pytest-asyncio>=0.23` to dev dependencies |

**Note on A2:** This is a verified fact, not an assumption. Flask unavailability in shared venv is confirmed.

---

## Open Questions

1. **`AuditLog` connection lifetime**
   - What we know: Phase 2 tests pass; audit operations work.
   - What's unclear: Whether `_store.py` holds a persistent connection or opens per-call.
   - Recommendation: Read `_store.py` in Plan 03-01 Wave 0; if persistent, add `check_same_thread=False`.

2. **`channel_cmds.py` `--fetch-pubkey-from` carve-out for sync httpx.get**
   - What we know: This is the one allowed cross-boundary HTTP call in the CLI (not in dispatch).
   - What's unclear: Whether the AST lint's allow-list for `channel_cmds.py` opens an unintentional hole.
   - Recommendation: The allow-list should be path-AND-endpoint scoped: allow `httpx` import in `channel_cmds.py` but the lint comment should document that only `GET /pubkey` calls are sanctioned.

3. **Forge result envelope shape and `persisted_fields`/`returned_fields` derivation**
   - What we know: `compare_result_against_policy` expects these keys; the `task_result` schema doesn't include them.
   - What's unclear: Whether the plan should add these fields to the forge result shape or derive them in dispatch.
   - Recommendation: Derive in dispatch (conservative approximation); do not change the forge result schema to avoid a cross-impl contract change in Phase 3.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | All | ✓ | 3.14.4 | — |
| `httpx` | DISP-01, DISP-06 | ✓ | 0.28.1 | — |
| `asyncio.to_thread` | DISP-06 | ✓ | stdlib (3.14) | — |
| `python-keyring` (macOS Keychain) | D-01, FORGE-01 | ✓ | 25.7.0 | — |
| `pynacl` | FORGE-01 via BrineProvider | ✓ | 1.6.2 | — |
| `jsonschema` | FORGE-04 | ✓ | 4.26.0 | — |
| `hypothesis` | smoke tests | ✓ | 6.152.4 | — |
| `pytest` | all tests | ✓ | 9.0.3 | — |
| `pytest-asyncio` | dispatch async tests | ✗ | — | Add to pyproject.toml dev deps |
| `Flask` | forge servers | ✗ in shared venv | — | Install per-forge venv (required) |
| `rfc8785` | canonicalize() | ✓ | 0.1.4 | — |
| `blake3` | audit log chain | ✓ | 1.0.8 | — |
| `click` | CLI | ✓ | via photophore pyproject | — |
| `thermocline-py` (editable) | all | ✓ | 0.3.1 | — |
| `photophore` (editable) | dispatch tests | ✓ | 0.3.1 | — |

**Missing dependencies with no fallback:**
- Flask (per-forge venv) — blocking for forge server startup; must be installed in each forge's `.venv` before any forge integration test can run.

**Missing dependencies with fallback:**
- `pytest-asyncio` — add to `photophore/python/pyproject.toml` `[project.optional-dependencies].dev`; install before writing async dispatch tests.

---

## Security Domain

> `security_enforcement` key is absent from `.planning/config.json` — treated as enabled per documented default.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes — forge receipt signing | `BrineProvider.sign()` via platform keystore; private key never leaves keystore |
| V3 Session Management | no | Stateless dispatch; each call is independent |
| V4 Access Control | yes — dispatch checks channel state (OPEN required) | `channels.show()` → state check → `CHANNEL_RESOLVE_FAILED` if not OPEN |
| V5 Input Validation | yes — envelope validation before dispatch; forge receipt validation | `thermocline.Task.model_validate()` (Pydantic v2, `extra='forbid'`); receipt_signature field presence checks |
| V6 Cryptography | yes — ed25519 signing + verification | `BrineProvider` (PyNaCl + keystore); never hand-rolled; `canonicalize()` for signing input |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Forged receipt signature (AT-E4) | Spoofing | `Verifier.verify()` returns `None` → `DispatchError.RECEIPT_INVALID`; no audit-post on forged receipt |
| Channel impersonation (AT-A1) | Spoofing | Dispatch step 1 checks `envelope.dispatch_signature.key_scheme == channel.key_scheme`; mismatch → abort |
| Result policy escalation (AT-C5) | Elevation of Privilege | `compare_result_against_policy()` called before audit-post; violation → `DispatchError.POLICY_VIOLATED` |
| Network module contamination (DISP-05) | Tampering | AST lint rejects httpx/requests/aiohttp import outside dispatch module; CI gate |
| Pre-dispatch audit bypass (DISP-02) | Repudiation | `AUDIT_FAILED_PRE` aborts before signing; no signed envelope without audit trail |
| Credential leakage via describe-forge reflection | Information Disclosure | Mixed-tier: inline content explicitly skipped; only shadow metadata (content_type, relevance) in output |
| Non-canonical JSON signing input | Tampering (cross-impl) | `canonicalize()` enforced; `json.dumps` lint from Phase 1 |

**Each plan MUST include a `<threat_model>` block covering the above patterns relevant to its scope (D-03 security requirement, `security_enforcement: true` default).**

---

## Sources

### Primary (HIGH confidence)

- `thermocline.identity` source — `/Users/dom/Projects/dom/thermocline/thermocline/python/src/thermocline/identity.py` — `BrineProvider`, `Verifier`, `_PUBKEY_PREFIX`, `register_public_key` API, `Receipt` sentinel mechanism
- `photophore.policy` source — `/Users/dom/Projects/dom/photophore/python/src/photophore/policy/_author.py` — `compare_result_against_policy` function signature and semantics confirmed
- `photophore.errors` source — `PhotophoreError` hierarchy base for `DispatchError` confirmed
- `photophore.cli.__init__` — click Group structure, existing add_command pattern
- AT-A1 fixture — `/Users/dom/Projects/dom/thermocline/thermocline/conformance/invalid/AT-A1-channel-impersonation.json` — `_phase_wired: 3`, `_expect_error_code: "CHANNEL_IMPERSONATION"`, violating_condition shape
- `pi-forge/envelope.py` lines 87–99, 139–165 — retirement targets confirmed
- `pi-forge/examples/task-100-digits.json` — regression fixture shape confirmed
- Python stdlib `ast` module — `Import`/`ImportFrom` node detection verified in Python 3.14
- `asyncio.to_thread` — verified functional for sync SQLite wrapping
- `httpx` 0.28.1 exception hierarchy — `TimeoutException`, `ConnectError` confirmed

### Secondary (MEDIUM confidence)

- Phase 2 D-11 decision — sync core + async shim; `~20 LOC` estimate [CITED: 03-CONTEXT.md]
- Phase 1 BL-01 — `register_public_key` cross-role API; `_PUBKEY_PREFIX` namespace [CITED: 01-LEARNINGS.md]
- Phase 2 LEARNINGS — `CliRunner(mix_stderr=False)` for JSON tests; `"gitignore"` pathspec pattern name; stale `.pth` editable install footgun [CITED: 02-LEARNINGS.md]
- Seamount README §"Forge Conformance Requirements" — 12-item checklist mapping [CITED: /Users/dom/Projects/dom/seamount/README.md]
- Photophore README §"Dispatch" / §"AT-A1..A6" — 9-step flow spec; threat surfaces [CITED: /Users/dom/Projects/dom/photophore/README.md]

### Tertiary (LOW confidence)

- `pytest-asyncio` version compatibility — not verified in venv; [ASSUMED] 0.23+ compatible with pytest 9.0.3.
- macOS Keychain port-race behavior for subprocess_forge — [ASSUMED] acceptable for sequential test runs; may fail under parallel pytest-xdist.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all key packages verified via `pip show` and live Python 3.14.4 imports
- Architecture: HIGH — verified from source code of all Phase 1+2 components
- Pitfalls: HIGH — derived from Phase 1+2 LEARNINGS (46 items); directly applicable patterns
- Policy-03 closure: HIGH — function confirmed fully implemented in source
- AT-A1 fixture: HIGH — fixture file read and shape confirmed

**Research date:** 2026-05-10
**Valid until:** 2026-06-10 (stable stack; 30-day window)
