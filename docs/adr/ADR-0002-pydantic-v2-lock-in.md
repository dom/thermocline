# ADR-0002: Pydantic v2 lock-in

**Status:** Accepted · 2026-05-12

## Context

Every envelope type in `thermocline-py` (`Task`, `TaskResult`, `Job`, `JobResult`,
`Error`) and every audit-payload type in `photophore` is a typed model with
strict validation at the boundary (no extra fields, no missing required fields,
type-checked content). Pydantic v2's Rust-backed core delivers the validation
performance the suite needs while generating JSON Schema artifacts for free
(used in `thermocline/schema/`).

Pydantic v1 and v2 are not API-compatible in important ways (validator decorators,
config keys, `model_dump`/`model_validate` rename). Mixing versions across
sub-packages would multiply maintenance.

## Decision

All Pydantic dependencies in the suite are pinned to `pydantic>=2.7,<3.0`.
v0.1 will not support v1 callers; envelope models use v2 features
(`model_config = ConfigDict(extra="forbid")`, `Annotated[...]` validators,
`field_validator` rather than `validator`).

## Consequences

- ✓ Single rust-backed validation core; one validation pattern across packages.
- ✓ JSON Schema 2020-12 generation matches what's in `thermocline/schema/`.
- ✓ THERMO-05 (`pyproject.toml` Pydantic v2 pin) is enforced.
- ✗ Downstream applications still on Pydantic v1 cannot consume `thermocline-py` directly.
- ✗ Major version bumps to Pydantic v3 will require a coordinated suite migration.

## References

- THERMO-03, THERMO-05 in REQUIREMENTS.md
- pyproject.toml `pydantic>=2.7,<3.0` pin
- Pydantic v2 release notes (https://docs.pydantic.dev/)
