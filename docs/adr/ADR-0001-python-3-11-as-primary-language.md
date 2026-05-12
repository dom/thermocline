# ADR-0001: Python 3.11 as primary language

**Status:** Accepted · 2026-05-12

## Context

The Thermocline suite ships three coordinated Python packages (`thermocline-py`,
`photophore`, `pi-forge`, `describe-forge`) plus a cross-suite conformance
harness. Choosing one primary language for the v0.1 reference implementation
reduces cross-impl drift and lets all four packages share a single envelope
type system, single canonical-JSON path, and single IdentityProvider Protocol.

Python 3.11 brings significant performance improvements and stable type-system
features (`Self`, `LiteralString`); python-keyring backs the macOS Keychain,
Linux libsecret, and Windows Credential Manager from one API; PyNaCl provides
audited ed25519; mature stdlib `sqlite3` covers the audit log requirement
without an extra dependency.

## Decision

The v0.1 reference implementation of all three Thermocline-suite specs is
written in Python 3.11+ (`requires-python = ">=3.11"` in every `pyproject.toml`).
Other-language implementations (Rust, TypeScript, Swift) are deferred to
post-v0.1 milestones.

## Consequences

- ✓ Single envelope type system shared across `thermocline-py` and `photophore`.
- ✓ Existing `seamount/pi-forge/` (Python 3.11+, Flask, mpmath) integrates without rewrite.
- ✓ `python-keyring` covers all three target platforms (macOS first-class; Linux/Windows secondary).
- ✗ Deployments needing a single binary must bundle CPython; statically-linked builds are slow.
- ✗ Cross-impl ports remain a post-v0.1 concern; the JSON Schema artifacts in
  `thermocline/schema/` keep the wire-level contract language-agnostic.

## References

- PROJECT.md §"Key Decisions"
- repository README ("Language — Python 3.11+")
- pyproject.toml files in all four packages
