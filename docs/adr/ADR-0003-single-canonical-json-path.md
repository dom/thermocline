# ADR-0003: Single canonical JSON path

**Status:** Accepted · 2026-05-12

## Context

Every signature in the Thermocline suite is computed over a canonicalized JSON
serialization of the envelope. Two implementations of "canonical JSON" that
disagree on a single byte produce signatures that no third party can verify. That is
the cross-impl drift the suite exists to prevent. RFC 8785 (JSON Canonicalization
Scheme, JCS) fixes the canonicalization. The reference implementation must use
a single library call site for every signing path AND every verify path, so
divergence can be ruled out structurally.

A negative lint (`check_no_json_dumps.py`) runs in CI to forbid `json.dumps`
in library code paths. The only sanctioned path to bytes is `canonicalize()`,
which calls `rfc8785.canonicalize()` exactly once.

## Decision

`thermocline.canonicalize(value)` is the ONLY function in the suite that converts
a Python value to canonical-JSON bytes. It delegates to `rfc8785.canonicalize`.
All signature input MUST flow through this function. `json.dumps` is forbidden
in library code (CI lint `check_no_json_dumps.py` enforces); CLI subcommands MAY
use `json.dumps` for human-readable output only.

## Consequences

- ✓ Cross-impl signature interop is structural: a Rust or TypeScript port that
  also uses an RFC 8785 library will produce byte-identical canonical forms.
- ✓ A single lint asserts the property at CI time (T+0 catch on regression).
- ✓ The `rfc8785` Python package is small, audited, and stable.
- ✗ A `json.dumps` of an envelope (for debugging) is structurally different from
  the canonical form; developers must remember this. The `__repr__` of envelope
  models is independent of canonical form by design.
- ✗ Schema generation (Pydantic → JSON Schema 2020-12) uses a different path
  (model introspection, not canonicalization); the two paths are tested for
  agreement via `tests/test_schema_drift.py`.

## References

- THERMO-04 in REQUIREMENTS.md
- `thermocline/python/src/thermocline/canonical.py` (single call site)
- `thermocline/python/src/thermocline/scripts/check_no_json_dumps.py` (CI lint)
- RFC 8785 (JSON Canonicalization Scheme)
