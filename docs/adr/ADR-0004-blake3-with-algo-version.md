# ADR-0004: BLAKE3 with `algo_version` chain

**Status:** Accepted · 2026-05-12

## Context

The Photophore audit log is the proof artifact for every channel transition,
every dispatch, and every CLI invocation. The log MUST be append-only and
cryptographically chained so that any single-byte tamper invalidates all
subsequent entries. This is what AT-A6 protects against.

BLAKE3 is significantly faster than SHA-256, modern, and audited. Its
parallelism + tree-mode features matter less than its simplicity here, but
the speed margin makes per-entry chaining cheap. A versioned `algo_version`
field (e.g., `"blake3-v1"`) keeps the door open for a future migration without
breaking the append-only invariant of existing chains.

## Decision

The Photophore audit chain uses BLAKE3 hashing with an explicit `algo_version`
field on every entry. v0.1 ships `algo_version="blake3-v1"`. The chain's
verifier dispatches on `algo_version`; entries with unknown versions fail
verification with a structured error. The `_assert_no_sensitive` runtime
guard at `AuditLog.append()` ensures audit payloads never carry privacy-
sensitive content (defense in depth on top of `Sensitive[T]` static typing).

## Consequences

- ✓ Chain verification scales: BLAKE3 hashes a 1KB payload in microseconds.
- ✓ `algo_version` field provides a clean migration path for future hash families.
- ✓ Same hash family used for CLI arg sanitization (`blake3:<hex>` for
  file-path args records correlation without leaking content).
- ✗ Requires the `blake3` Python wheel; pure-stdlib alternatives (SHA-256) are
  the documented fallback if no wheel exists for a target platform.

## References

- AUDIT-02 in REQUIREMENTS.md
- `photophore/python/src/photophore/audit/_chain.py` `ALGO_VERSION_DEFAULT`
- BLAKE3 spec: https://github.com/BLAKE3-team/BLAKE3
