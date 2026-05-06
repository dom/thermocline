# Stack Research

**Domain:** Suite-wide Python reference implementation of Thermocline (envelope spec + shared library), Photophore (policy engine), Seamount (forge upgrades — pi-forge brine, second tier-1-exercising forge)
**Researched:** 2026-05-05
**Confidence:** HIGH on language + canonical libraries; MEDIUM on individual versions (verify at install time)

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.11+ | Implementation language across all three repos | Required by `pi-forge` already; aligns with Thermocline's planned `thermocline-py` reference. 3.11 brings significant performance improvements; 3.12+ adds better type narrowing. Pin via `pyproject.toml`. |
| Pydantic | 2.7+ | Envelope types in `thermocline-py` | Fast (Rust-backed core), ergonomic, generates JSON Schema for free, integrates with FastAPI/Flask, idiomatic for typed Python. v2 is significantly faster than v1. |
| PyNaCl | 1.5+ | ed25519 signing/verifying for `brine` key scheme | Mature libsodium bindings; smaller surface than `cryptography` for our needs (sign + verify only). Audited. Ships compiled wheels for all major platforms. |
| SQLite | 3.46+ (via stdlib `sqlite3`) | Audit log storage (Photophore Ring 1) | Spec-mandated; append-only; no server. Stdlib means no extra dependency. |
| python-keyring | 25.x | Cross-platform secure keystore wrapper | Trust store backing (Keychain / libsecret / Credential Manager). Spec mandate. Mature, well-supported. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `rfc8785` | latest | Canonical JSON (JCS) for signature input | **Required** for any signing path — non-canonical JSON breaks signatures across implementations. Use everywhere signing input is computed. |
| `jsonschema` | 4.x | JSON Schema validation | For conformance testing — validate envelopes against the published Thermocline schemas. |
| `blake3` | 0.4+ (Python binding) | Audit chain hash | Faster than SHA-256, modern. Used with explicit `algo_version="blake3-v1"` field for migration safety. |
| `click` or `typer` | 8.x / 0.12+ | CLI framework for `photophore` and `tasker` (sovereign-node CLI) | Use `typer` if heavy type integration desired, `click` for stability. Lean toward `click` — it's the foundation `typer` builds on, and our CLIs are simple. |
| `httpx` | 0.27+ | HTTP transport for dispatch (async) | Modern async-first client; replaces `requests` for new code. Used only in Photophore's `dispatch` module. |
| `flask` | 3.x | Forge transport (continuation of pi-forge) | Already used by pi-forge; minimal, easy to read, fits the "as simple as possible" forge ethos. |
| `mpmath` | 1.3+ | π computation in pi-forge | Already a pi-forge dependency; no change. |
| `pytest` | 8.x | Test runner | Standard. With `pytest-asyncio` for async tests. |
| `hypothesis` | 6.x | Property-based testing (proptest equivalent) | Required for invariants: classifier default, audit chain integrity, canonical-JSON round-trip stability, shadow-ID uniqueness. |
| `pytest-asyncio` | 0.23+ | Async test support | Photophore's dispatch coordinator is async; tests need this. |
| `mypy` | 1.10+ | Static type checking | Strict mode. Privacy primitive — type discipline matters. |
| `ruff` | 0.5+ | Linter and formatter | Fast; replaces `black` + `isort` + `flake8` + many plugins. CI gate. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `uv` | Project management + virtualenv | Fast, modern Python package manager (Astral); replaces pip+venv+pip-tools. Alternative: stick with `pip` + `venv` for max compatibility. **Recommendation: uv** for development, `pip install` for end users. |
| `pyproject.toml` | Per-package configuration | One per package: `thermocline-py`, `photophore`, `pi-forge`, `describe-forge`. |
| `pip-audit` | Vulnerability scanning | Run in CI. Privacy primitive — no known-vuln deps allowed. |
| `pre-commit` | Git hook orchestration | Run `ruff` + `mypy` before commit. |
| `mkdocs` (or `mkdocs-material`) | Spec/docs site | Optional for v0.1; the READMEs may be sufficient. Promote to `mkdocs` if cross-linking grows. |
| `python -m build` | Build wheels for PyPI | Standard packaging path. |

## Installation

```bash
# Development setup with uv (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh

cd thermocline/python
uv venv
uv pip install -e ".[dev]"

cd ../../photophore
# (after photophore/python/ is created in Phase 2)
uv pip install -e ".[dev]"

cd ../seamount/pi-forge
uv pip install -e ".[dev]"
```

```toml
# Representative pyproject.toml for thermocline/python/
[project]
name = "thermocline"
version = "0.3.1"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.7",
    "pynacl>=1.5",
    "rfc8785",
    "jsonschema>=4.0",
    "keyring>=25.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "hypothesis>=6.0",
    "mypy>=1.10",
    "ruff>=0.5",
    "pip-audit",
]
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Pydantic v2 | `attrs` + `cattrs` | If avoiding the Pydantic v2 Rust core matters for some reason (e.g., pure-Python audit). Trade-off: more boilerplate. |
| Pydantic v2 | `dataclasses` (stdlib) | For the simplest possible envelope types with no validation. Not recommended — validation is exactly what we need at the boundary. |
| PyNaCl | `cryptography` | If we eventually need broader crypto (X.509 cert handling for the `x509` key scheme). For brine (ed25519) only, PyNaCl is simpler. |
| python-keyring | Direct platform calls (`pyobjc` for macOS, `secretstorage` for Linux) | Only if `keyring` proves insufficient on Apple Silicon Secure Enclave. Test early. |
| BLAKE3 | SHA-256 | If interop with an existing SHA-256 system mandates it. The `algo_version` field makes either work. |
| `httpx` | `aiohttp` | If we need WebSocket support later (jobs streaming, etc.). For v0.1 task dispatch over HTTP, `httpx` is sufficient. |
| `click` | `argparse` (stdlib) | For maximum simplicity. We pick `click` for ergonomics + nested subcommands (channel, audit, dispatch, classify, policy). |
| `uv` | `pip` + `venv` | If contributors require strict stdlib-only tooling. uv is recommended for dev; not strictly required. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Cloud or remote inference for content classification | Direct violation of Photophore Design Constraint 1 (sovereign-node-only). Even one cloud call breaks the threat model. | Local rule pipeline (v0.1); local model classifier (v0.3, opt-in). |
| Storing the trust store inside SQLite alongside the audit log | Spec explicitly forbids co-location (Photophore AT-A5). | `python-keyring` (platform keystore) for trust store; `sqlite3` for audit log. **Always separate backing stores.** |
| `requests` (sync HTTP) in Photophore's dispatch path | Sync HTTP blocks the event loop; modern async-first design wants `httpx`. | `httpx.AsyncClient` for dispatch. |
| `json.dumps` for signature input | Non-canonical JSON breaks signatures across implementations. | `rfc8785` (`canonicalize`) for signing input. **Never** sign over `json.dumps` output. |
| `pickle` anywhere | Massive deserialization-vulnerability surface. | JSON via Pydantic for everything that crosses a boundary or hits disk. |
| `random.random()` for shadow IDs | Not cryptographic; correlatable across dispatches. | `secrets.token_hex(16)` or UUIDv4 over `os.urandom`. |
| `print()` in library code | Hard to control; leaks to stdout in unexpected contexts. | `logging` with a privacy-aware filter that redacts fields tagged `sensitive`. |
| `dotenv` / env-var-based key material | Spec mandates IdP delegation; keys never live in env. | `IdentityProvider` interface; reference adapter calls keystore per signature. |
| Storing `bytes` content in `__repr__`-able types without a redacting wrapper | Content leaks via accidental `print(envelope)` or log statements. | Custom `__repr__` that redacts; or wrap in a sentinel `Sensitive[T]` newtype. |
| Vendored Python 3.x | Hard to keep secure-keystore bindings working across Python versions | Pin to system Python 3.11+; use `uv` to manage venvs. |

## Stack Patterns by Variant

**If targeting macOS-first (recommended for v0.1 dev preview):**
- Default `keyring` backend works; Apple Silicon Secure Enclave entries may need explicit attribute setting
- Test biometric-gated entries early — code-signing requirement may apply for distribution
- Recommend Homebrew-installed Python or `uv`-managed Python

**If targeting Linux server-side use (uncommon but possible):**
- `keyring` requires D-Bus session for `libsecret`; document gracefully on headless servers (refuse to start vs. silent file-based fallback — refuse, per spec)
- Document a "containerized forge" deployment path (pi-forge in a minimal image) where keystore isn't needed because `key_scheme=none` is acceptable for tier-2-only forges

**If a contributor wants a non-Python impl later:**
- The JSON Schema artifacts in `thermocline/schema/` are language-agnostic; they're the contract
- Conformance fixtures (request/response JSON pairs) operate purely on JSON, no Python required
- A Rust, TypeScript, or Swift impl can be added in a future milestone without changing the spec

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| Python 3.11 | Pydantic 2.7+ | 3.11 minimum for performance; 3.12 better type narrowing; 3.13 fine. |
| Pydantic 2.7+ | `jsonschema` 4.x | Pydantic generates Draft 2020-12 schemas; jsonschema validates them natively. |
| PyNaCl 1.5+ | All Python 3.11+ | Stable API; ed25519 functions haven't changed. |
| `blake3` 0.4 | Python 3.11+ | Compiled wheels available. |
| `python-keyring` 25 | macOS 12+, Linux libsecret 0.20+, Windows 10+ | Older platforms may lack required APIs. |
| Flask 3.x | Werkzeug 3.x | Pi-forge pins both; do not mix Flask 2.x with Werkzeug 3.x. |

## Sources

- Specs: `thermocline/README.md`, `photophore/README.md`, `seamount/README.md` (all v0.3.0-draft) — the only normative sources
- Existing reference impl: `seamount/pi-forge/` (Python 3.11+, Flask, mpmath) — sets language precedent
- Pydantic v2 docs (https://docs.pydantic.dev/) — for envelope type idioms
- PyNaCl docs (https://pynacl.readthedocs.io/) — for ed25519 sign/verify
- RFC 8785 (https://www.rfc-editor.org/rfc/rfc8785) — JSON Canonicalization Scheme
- BLAKE3 spec (https://github.com/BLAKE3-team/BLAKE3) — chain-hash properties
- Confidence: HIGH on language + canonical libraries; MEDIUM on exact patch versions (re-verify at install time)

---
*Stack research for: Thermocline Suite v0.1 Python reference implementation*
*Researched: 2026-05-05*
