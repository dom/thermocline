# Architecture Research

**Domain:** Thermocline Suite v0.1 Python reference implementation across three repos
**Researched:** 2026-05-05
**Confidence:** HIGH (constrained by the three specs; this document maps spec components to Python package boundaries across repos)

## Standard Architecture

### System Overview (suite-wide)

```
┌──────────────────────────────────────────────────────────────────────┐
│                  Sovereign Node (User's Machine)                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                   `photophore` CLI (click)                      │  │
│  │  channel | audit | classify | policy | dispatch                 │  │
│  └────────────────────────────┬───────────────────────────────────┘  │
│                               │                                       │
│  ┌────────────────────────────┴───────────────────────────────────┐  │
│  │            photophore.dispatch (async coordinator)              │  │
│  │  Orchestrates: classify → shadow → policy → audit-pre → sign    │  │
│  │              → transport → verify-receipt → audit-post          │  │
│  └────┬─────────┬─────────┬─────────┬───────────┬────────┬─────────┘  │
│       │         │         │         │           │        │            │
│  ┌────┴─────┐ ┌─┴──────┐ ┌┴─────┐ ┌┴──────┐ ┌──┴─────┐ ┌┴───────┐    │
│  │photophore│ │photoph.│ │photo │ │photo  │ │thermo- │ │photo-  │    │
│  │.channels │ │.classi-│ │phore │ │phore  │ │cline.  │ │phore.  │    │
│  │          │ │fier    │ │.shad │ │.policy│ │identity│ │audit   │    │
│  │          │ │        │ │ow    │ │       │ │+ brine │ │        │    │
│  └────┬─────┘ └────────┘ └──────┘ └───────┘ └───┬────┘ └───┬────┘    │
│       │                                          │           │       │
│  ┌────┴────────────────────┐                ┌───┴────┐ ┌───┴────┐    │
│  │  Platform Keystore       │                │keystore│ │ SQLite │    │
│  │  (via python-keyring)    │                │ (sign) │ │ chain  │    │
│  │  Keychain / libsecret /  │                └────────┘ └────────┘    │
│  │  Credential Manager      │                                         │
│  └──────────────────────────┘                                         │
│                                                                       │
│  Imports `thermocline` (envelope types, canonical JSON, brine, IdP)  │
└──────────────────────────────────────────────────────────────────────┘
                              │     ▲
                              │     │  HTTP (httpx)
                              ▼     │
                          [Network Boundary]
                              │     │
                              ▼     │
                  ┌──────────────────────────────┐
                  │   Receiving Node (Forge)     │
                  │  ┌────────────────────────┐  │
                  │  │ Flask handler           │ │
                  │  │  POST /task             │ │
                  │  └─────────┬───────────────┘ │
                  │            │                 │
                  │  ┌─────────┴───────────────┐ │
                  │  │ thermocline.envelope    │ │
                  │  │  validate_task          │ │
                  │  │  build_task_result      │ │
                  │  │  (real brine via PyNaCl)│ │
                  │  └─────────┬───────────────┘ │
                  │            │                 │
                  │  ┌─────────┴───────────────┐ │
                  │  │ Forge logic              │ │
                  │  │  pi-forge: compute π    │ │
                  │  │  describe-forge: shadow │ │
                  │  │   → templated description│ │
                  │  └──────────────────────────┘ │
                  │  Holds nothing post-response │
                  └──────────────────────────────┘
```

### Repository Layout (multi-repo)

```
~/Projects/dom/
├── thermocline/                    # spec + shared library + planning hub
│   ├── README.md                   # the spec (canonical)
│   ├── .planning/                  # ★ single suite-wide planning hub
│   ├── schema/                     # JSON Schema artifacts (Phase 1 deliverable)
│   │   ├── task.schema.json
│   │   ├── task_result.schema.json
│   │   ├── job.schema.json
│   │   ├── job_result.schema.json
│   │   └── error.schema.json
│   ├── python/                     # ★ thermocline-py shared library
│   │   ├── pyproject.toml
│   │   ├── src/thermocline/
│   │   │   ├── __init__.py
│   │   │   ├── envelope.py         # Pydantic models for all envelope types
│   │   │   ├── canonical.py        # rfc8785 wrapper for signing input
│   │   │   ├── identity.py         # IdentityProvider ABC + brine reference adapter
│   │   │   ├── schemes.py          # KeyScheme enum (brine/pgp/x509/none)
│   │   │   ├── version.py          # SUPPORTED_VERSIONS = {"0.3.0", "0.3.1"}
│   │   │   ├── errors.py           # EnvelopeError, IdentityError, etc.
│   │   │   └── conformance/        # JSON fixtures + harness helpers
│   │   └── tests/
│   └── conformance/                # cross-language conformance fixtures
│       ├── valid/                  # JSON pairs (request, expected response)
│       └── invalid/                # one fixture per AT-* surface, with expected error
│
├── photophore/                     # policy engine (the bulk of new code)
│   ├── README.md                   # the spec (canonical)
│   ├── python/                     # ★ photophore Python package
│   │   ├── pyproject.toml
│   │   ├── src/photophore/
│   │   │   ├── __init__.py
│   │   │   ├── core.py             # shared types: ChannelId, Tier, Reason, ShadowId
│   │   │   ├── channels.py         # trust store + lifecycle (uses python-keyring)
│   │   │   ├── classifier.py       # tag parser + path rules + rule-based default
│   │   │   ├── shadow.py           # generator + per-type strategies + quality tests
│   │   │   ├── policy.py           # result_policy authoring
│   │   │   ├── audit.py            # SQLite chained log + AnchorTarget protocol
│   │   │   ├── dispatch.py         # async coordinator (9-step flow)
│   │   │   └── cli.py              # click-based CLI
│   │   └── tests/
│   └── (CLAUDE.md absent — single hub at thermocline/.planning/)
│
└── seamount/                       # forge spec + reference forges
    ├── README.md                   # the spec (canonical)
    ├── pi-forge/                   # tier-2-only π forge (existing, upgraded)
    │   ├── pyproject.toml          # ★ new (was just requirements)
    │   ├── README.md
    │   ├── server.py               # Flask handler — uses thermocline.envelope
    │   ├── pi.py                   # π computation
    │   ├── envelope.py             # ★ replaced: now imports from thermocline-py
    │   └── examples/
    ├── describe-forge/             # ★ new: tier-1-shadow-exercising demo forge
    │   ├── pyproject.toml
    │   ├── README.md
    │   ├── server.py               # Flask handler
    │   ├── describe.py             # templated descriptor logic
    │   └── examples/
    └── conformance/                # ★ test harness — runnable against any forge
        ├── pyproject.toml
        ├── src/forge_conformance/
        │   ├── __init__.py
        │   ├── runner.py           # POSTs envelopes; validates responses
        │   ├── fixtures/           # imported from thermocline/conformance/
        │   └── checklist.py        # maps Seamount conformance checklist to tests
        └── tests/
```

### Component Responsibilities

| Component | Repo | Responsibility |
|-----------|------|----------------|
| `thermocline.envelope` | thermocline | Pydantic models for all envelope types; serialization/deserialization; field validation |
| `thermocline.canonical` | thermocline | RFC 8785 canonical JSON for signature input |
| `thermocline.identity` | thermocline | `IdentityProvider` abstract base + reference brine adapter (PyNaCl + python-keyring) |
| `thermocline.schemes` | thermocline | `KeyScheme` enum + dispatch logic (verifier picks adapter by declared scheme) |
| `thermocline.conformance` | thermocline | JSON fixtures + harness helpers shared by Photophore tests and `seamount/conformance` |
| `photophore.channels` | photophore | Trust store + channel lifecycle. Backed by `python-keyring`. NEVER touches SQLite. |
| `photophore.classifier` | photophore | Three-tier rule pipeline. Pure functions, no I/O, no async. |
| `photophore.shadow` | photophore | Shadow generator + per-content-type abstraction strategies + irreversibility/relevance/distinguishability tests. Pure functions. |
| `photophore.policy` | photophore | `result_policy` authoring from channel + envelope draft. Pure functions. |
| `photophore.audit` | photophore | SQLite chained log + `AnchorTarget` Protocol + no-op default. Append-only via SQLite triggers. |
| `photophore.dispatch` | photophore | Async coordinator orchestrating the 9-step dispatch flow. Only module that performs network I/O. |
| `photophore.cli` | photophore | `click`-based CLI; subcommands for channel/audit/classify/policy/dispatch. |
| `seamount/pi-forge/server.py` | seamount | Flask handler for `POST /task` (computes π); statelessness guard; uses `thermocline-py` for all envelope work. |
| `seamount/describe-forge/server.py` | seamount | Flask handler for `POST /task` (returns templated description from a tier-1 shadow); uses `thermocline-py`. |
| `seamount/conformance/runner.py` | seamount | Standalone test harness for any Thermocline-compliant forge. |

## Architectural Patterns

### Pattern 1: Pure-Core / Imperative-Shell

**What:** `photophore.classifier`, `photophore.shadow`, and `photophore.policy` are pure functions with no I/O. `photophore.dispatch` is the imperative shell that performs DB writes, signing RPC, and HTTP calls.
**When to use:** Always for the privacy-critical components.
**Trade-offs:** Forces values to be passed explicitly (no module-level state) — verbose but testable. Eliminates "the classifier secretly hit the network" bugs.

**Example:**
```python
# photophore/classifier.py — pure, no I/O
def classify(block: ContentBlock, rules: PathRules) -> Classification:
    if tag := block.explicit_tag():
        return Classification(tier=tag.into_tier(), reason=Reason.EXPLICIT_TAG)
    if rule := rules.match_path(block.path):
        return Classification(tier=rule.tier, reason=Reason.path_rule(rule.pattern))
    return rule_based_default(block)  # also pure

# photophore/dispatch.py — imperative shell
async def dispatch(channel_id: ChannelId, draft: TaskDraft, ctx: DispatchContext) -> Receipt:
    channel = await ctx.channels.get(channel_id)             # I/O
    classifications = [classify(b, channel.rules) for b in draft.context]  # PURE
    shadows = generate_shadows(classifications)              # PURE
    policy = author_policy(channel, draft)                   # PURE
    await ctx.audit.append(pre_dispatch_entry(...))          # I/O
    signed = await ctx.identity.sign(canonicalize(envelope)) # I/O (delegated)
    receipt = await ctx.transport.send(signed)               # I/O (network)
    verified = await ctx.identity.verify(receipt)            # I/O — returns Receipt only on success
    await ctx.audit.append(receipt_entry(verified))          # I/O
    return verified
```

### Pattern 2: Protocol-Boundaried Adapters

**What:** Every external dependency is a `typing.Protocol` (or ABC), not a concrete class. Reference implementations ship in v0.1; alternatives slot in without changing call sites.
**When to use:** Any boundary that crosses the sovereign-node trust boundary OR has multiple legitimate implementations (HSM vs. software keystore; Arweave vs. Bitcoin anchor target).

**Example:**
```python
# thermocline/identity.py
from typing import Protocol

class IdentityProvider(Protocol):
    @property
    def scheme(self) -> KeyScheme: ...
    async def sign(self, message: bytes) -> Signature: ...
    async def verify(self, message: bytes, signature: Signature, public_key: PublicKey) -> None: ...
    async def public_key(self, node_id: NodeId) -> PublicKey: ...
```

### Pattern 3: Append-Only with Hash-Chained Verification

**What:** Audit log entries form a chain — each entry includes `prev_hash = blake3(canonical_bytes(previous_entry))`. The chain head is the "current proof". Tampering at position N invalidates positions N+1..end.
**When to use:** This is the audit log; it's not optional.
**Trade-offs:** Cannot delete or amend entries (by design). Recovery from corruption requires archiving and starting a new chain — the archive remains as evidence.

**Example:**
```python
# photophore/audit.py
class AuditEntry(BaseModel):
    seq: int
    prev_hash: bytes  # 32 bytes
    algo_version: str = "blake3-v1"
    timestamp: datetime
    kind: AuditEntryKind
    # ... fields per spec

    def canonical_bytes(self) -> bytes:
        return rfc8785.canonicalize(self.model_dump(mode="json"))

    def hash(self) -> bytes:
        if self.algo_version == "blake3-v1":
            return blake3(self.canonical_bytes()).digest()
        raise UnsupportedChainAlgoError(self.algo_version)
```

### Pattern 4: Sensitive-Wrapper Newtypes

**What:** Wrap any value that could be tier-0 in a wrapper class that redacts on `__repr__`/`__str__`.
**When to use:** Any field that could carry private content. Easier than Rust's `secrecy` since Python doesn't have linear types — but the discipline is similar.

**Example:**
```python
# photophore/core.py
class Sensitive[T]:
    def __init__(self, value: T):
        self._value = value
    def expose(self) -> T:
        return self._value
    def __repr__(self) -> str:
        return "<Sensitive: REDACTED>"
    def __str__(self) -> str:
        return self.__repr__()

class ContentBlock(BaseModel):
    id: BlockId
    tier: Tier
    content: Sensitive[bytes]  # Pydantic accepts this with a custom validator

    model_config = {"arbitrary_types_allowed": True}
```

### Pattern 5: Receipt-as-Verification-Witness

**What:** `Receipt` is a dataclass-like type whose only public constructor is via `IdentityProvider.verify()`. Code that wants a `Receipt` *must* go through verification — there is no "build a Receipt with these fields" path.
**When to use:** Any value type that represents "this was cryptographically verified to be true".

**Example:**
```python
# thermocline/identity.py
class Receipt:
    """Receipt of a verified envelope round-trip. Constructible only via IdentityProvider.verify."""
    __slots__ = ("_envelope_id", "_responder", "_signature_hash", "_verified_at")

    @classmethod
    def _from_verified(cls, envelope_id, responder, sig_hash, verified_at):
        # Only IdentityProvider.verify calls this; module-private
        instance = cls.__new__(cls)
        instance._envelope_id = envelope_id
        instance._responder = responder
        instance._signature_hash = sig_hash
        instance._verified_at = verified_at
        return instance

    def __init__(self):
        raise TypeError("Receipt is constructible only via IdentityProvider.verify")
```

## Data Flow

### Dispatch Flow (the core protocol path)

```
[CLI: photophore dispatch --channel CH123 --task draft.json]
    ↓
[CLI parses draft → TaskDraft Pydantic model]
    ↓
[dispatch.dispatch(channel_id, draft) coroutine starts]
    ↓
[channels.get(channel_id) → Channel (from keyring)]
    ↓
[For each block in draft.context: classifier.classify(block, channel.rules)]
    ↓
[shadow.generate(classifications) → tier-0 stripped, tier-1 → shadows, tier-2 passthrough]
    ↓
[policy.author(channel, draft) → result_policy block]
    ↓
[Build TaskEnvelope; serialize]
    ↓
[audit.append(PRE_DISPATCH_ENTRY) → chain extends]
    ↓
[identity.sign(canonical_bytes) → dispatch_signature (delegated to keystore)]
    ↓
[transport.post("https://forge/task", signed_envelope)] ◄─── only network I/O
    ↓
[response = TaskResultEnvelope from forge]
    ↓
[identity.verify(response.receipt_signature) → Receipt OR raise]
    ↓
[audit.append(RECEIPT_ENTRY) → chain extends]
    ↓
[CLI prints receipt summary]
```

### Forge Flow (pi-forge / describe-forge)

```
[POST /task with TaskEnvelope JSON body]
    ↓
[thermocline.envelope.validate_task_envelope(body) → envelope_id OR EnvelopeError]
    ↓
[If dispatch_signature.key_scheme == "brine": identity.verify(canonical_bytes, sig, pubkey) OR halt]
    ↓
[Forge-specific logic]
    pi-forge:        compute_pi(digits) → str
    describe-forge:  template_for_shadow(shadow) → str
    ↓
[thermocline.envelope.build_task_result(envelope_id, outputs, ...)]
    ↓
[identity.sign(canonical_bytes) → receipt_signature (forge's keystore)]
    ↓
[Return TaskResultEnvelope JSON; flush in-memory state]
```

### Conformance Test Harness Flow

```
[forge_conformance run --target http://localhost:5100]
    ↓
[Load fixtures from thermocline/conformance/]
    ↓
[For each (request_envelope, expected_response_class) pair:
    POST request_envelope → response
    Validate response against thermocline/schema/*.json
    If response is task_result: verify receipt signature
    Compare against expected_response_class
    Record pass/fail with diagnostic]
    ↓
[Map results to Seamount conformance checklist (12 items)]
    ↓
[Print/JSON report; exit non-zero on any fail]
```

## Scaling Considerations

The Thermocline Suite v0.1 is single-node by design. "Scale" means dispatches/sec on one sovereign node; audit-log size over time; concurrent forge requests for pi-forge.

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1–100 dispatches/day | No optimization needed. Default SQLite WAL. Single httpx client. |
| 100–10k dispatches/day | Index audit log on `(channel_id, ts)` and `(envelope_id)`; prepared statements; periodic `wal_checkpoint(TRUNCATE)`. |
| 10k+ dispatches/day | Reconsider — Photophore is not designed as a multi-tenant gateway. v0.5+ may add batching. |

## Anti-Patterns

### Anti-Pattern 1: Trust Store in SQLite Alongside Audit Log
**Mitigation:** Trust store ALWAYS in `python-keyring`. Audit log ALWAYS in `sqlite3`. Document in ADR.

### Anti-Pattern 2: Caching Shadows
**Mitigation:** Each dispatch generates fresh shadows. Cache *classification result* if needed; never the shadow.

### Anti-Pattern 3: Optional Audit Writes
**Mitigation:** Audit writes are mandatory. If write fails, dispatch fails. No `--quiet` flag.

### Anti-Pattern 4: Generic Abstractions in Shadow Strings
**Mitigation:** Per-content-type strategies; irreversibility test gate.

### Anti-Pattern 5: HTTP in `classifier` or `audit`
**Mitigation:** Lint check (CI gate) — `import requests/httpx/aiohttp` is forbidden in `photophore/{classifier,audit,shadow,policy,channels}.py` and in `thermocline/*.py`.

### Anti-Pattern 6: `print()` in library code
**Mitigation:** CI lint forbids `print(` in `thermocline/src/` and `photophore/src/`. Use `logging` with redacting filter.

### Anti-Pattern 7: `json.dumps` for signing input
**Mitigation:** All signing paths go through `thermocline.canonical.canonicalize` (RFC 8785). Property test asserts round-trip stability.

### Anti-Pattern 8: `Exception` raised from audit-write failure
**Mitigation:** Specific `AuditWriteError`; dispatch catches and converts to `DispatchError.AUDIT_FAILED` so the envelope is never sent.

## Integration Points

### External Services

| Service | Integration | Notes |
|---------|-------------|-------|
| Platform keystore | `python-keyring` | Trust store backing + IdP key material. |
| Forge | `httpx` from Photophore's dispatch | The only network I/O in the entire Photophore codebase. |
| Anchoring target (Ring 3) | `AnchorTarget` Protocol; v0.1 ships only no-op | Future Arweave adapter slots in here. |
| Identity provider | `IdentityProvider` Protocol; v0.1 ships PyNaCl-based brine | Future HSM/hardware-token adapters slot in here. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `thermocline` ↔ `photophore` | Direct import (`pip install thermocline-py`) | Photophore depends on thermocline-py. |
| `thermocline` ↔ `pi-forge` / `describe-forge` | Direct import | Forges depend on thermocline-py for envelope handling. |
| `photophore.classifier` ↔ `photophore.dispatch` | Direct sync function calls | Pure; no need for async. |
| `photophore.audit` ↔ everywhere that writes | `await audit.append(...)` | Audit is async-ready; SQLite via `aiosqlite` or `asyncio.to_thread`. |
| `photophore.identity` ↔ `photophore.dispatch` | Async Protocol calls | Keystore RPC may take >100ms (biometric prompt). |
| `photophore.dispatch` ↔ Forge | `httpx` async | Only HTTP. CI gate enforces. |

## Sources

- Specs: `thermocline/README.md`, `photophore/README.md`, `seamount/README.md`
- Existing code: `seamount/pi-forge/` Flask + envelope.py
- Pure Core / Imperative Shell (Gary Bernhardt) — applied to privacy-critical components
- Confidence: HIGH on architecture (constrained by specs); HIGH on multi-repo Python layout (informed by existing pi-forge convention)

---
*Architecture research for: Thermocline Suite v0.1 Python reference implementation*
*Researched: 2026-05-05*
