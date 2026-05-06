# Phase 1: `thermocline-py` Foundations - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-05
**Phase:** 1-thermocline-py-foundations
**Areas discussed:** Receipt private-constructor mechanism, JSON Schema generation pipeline, `Sensitive[T]` placement, Conformance fixture structure

---

## Receipt Private-Constructor Mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| A. Pydantic `BaseModel` + `model_config = frozen=True` + private token in `__init__` | Reuse Pydantic for consistency with envelope types | |
| B. Frozen `@dataclass` + module-private sentinel token in `__post_init__` | Independent of Pydantic; closes both `__init__` and `model_validate` escape hatches | ✓ |
| C. `typing.NamedTuple` with factory function | Immutable by default; smallest surface | |
| D. Frozen dataclass + thread-local "verify in progress" flag | Runtime gate without sentinel parameter | |

**User's choice:** B (frozen dataclass + sentinel token).
**Notes:** Pydantic exposes three public construction paths (`__init__`, `model_validate`, `model_construct`) — closing all three is fragile. Receipt is an internal verification witness, not wire format, so loss of Pydantic schema/serialization features doesn't matter. Frozen dataclass + sentinel gives both static (mypy --strict) and runtime enforcement with one trivial `pytest.raises` test.

---

## JSON Schema Generation Pipeline

| Option | Description | Selected |
|--------|-------------|----------|
| A. Generate-and-commit with CI drift check | Schemas are versioned artifacts; CI runs `--check` and fails on drift | ✓ |
| B. Generate-on-build (regenerated each install/test) | Schemas are ephemeral; no commit overhead | |
| C. Hand-authored, validated against Pydantic models in tests | Schemas are spec artifacts; Pydantic models conform to them | |

**User's choice:** A (generate-and-commit + CI drift check).
**Notes:** Schemas are public cross-language artifacts; future `thermocline-ts` / `thermocline-rs` impls reference them at stable paths under `thermocline/schema/`. Generate-on-build makes them ephemeral and unstable across Pydantic patch versions. Hand-authored re-introduces drift bug class. Generate-and-commit + CI drift check is the standard protobuf/OpenAPI pattern.

---

## `Sensitive[T]` Wrapper Placement

| Option | Description | Selected |
|--------|-------------|----------|
| A. Phase 1, in `thermocline-py` (new module `thermocline.sensitive`); apply to envelope content fields | Establish discipline before any downstream importer inherits the leak | ✓ |
| B. Phase 2, in `photophore.core`; thermocline-py envelope content stays raw `bytes` | Closer to first use; smaller Phase 1 surface | |
| C. Phase 1 in `thermocline-py` but don't apply to content fields yet — let Photophore opt-in | Half-measure | |

**User's choice:** A (Phase 1, in thermocline-py, applied to content fields from day 1).
**Notes:** Pitfall 4 (research/PITFALLS.md) explicitly assigns this discipline to Phase 1. If `thermocline-py` ships with raw `bytes` content, every downstream Python importer (Photophore in Phase 2, pi-forge upgrade in Phase 3, describe-forge in Phase 3, future cross-language Python users) inherits the leak by default. Putting `Sensitive[T]` in thermocline-py also signals it as suite-wide library hygiene, not Photophore-only policy. Wire format is unaffected because Pydantic custom serializer unwraps `Sensitive[bytes]` → base64 string for `model_dump(mode='json')`.

---

## Conformance Fixture AT-* Annotation

| Option | Description | Selected |
|--------|-------------|----------|
| A. `_meta` block inside the fixture JSON | Single file per fixture; metadata co-located | |
| B. Sidecar `meta.json` per fixture | Fixture stays clean JSON; metadata in parallel file | |
| C. Filename convention only (`AT-C3-malformed-sig.json`) | Simplest; harness derives surface from filename | |
| D. YAML `MANIFEST.yaml` per directory + filename convention for grep | Single source of truth; cross-language readable | ✓ |

**User's choice:** D (YAML MANIFEST + filename convention).
**Notes:** `_meta` block contaminates the envelope so it no longer parses as a real Thermocline envelope (defeats the test's purpose under strict Pydantic validation). Sidecar `.meta.json` doubles file count and risks drift on rename. Filename-only loses expected-error-code. Manifest YAML is language-agnostic (TS/Rust impls parse YAML easily), single-source-of-truth for `forge_conformance` harness in Phase 4, and directly maps to CONF-02 surface coverage counting. Phase 1 deliverable: manifest schema + at least one fixture per AT-C* surface (6 fixtures).

---

## Claude's Discretion

The following sub-decisions were noted as planner discretion (no user input required):

- Exact layout of `thermocline/python/scripts/` directory (single `build_schemas.py` vs. small CLI module)
- Whether the brine adapter exposes `generate()` as a Protocol method or a separate `keygen` utility
- `python-keyring` service-name convention (recommended default: service `"thermocline.brine"`, username = identity ID)
- Whether `thermocline-py` ships any CLI utilities (default library-only unless planner identifies strong dev-loop need)
- Pydantic `ConfigDict` options beyond mandatory `extra="forbid"`

## Deferred Ideas

- `Sensitive[T]` `logging.Filter` → Phase 4 (CONF-06)
- Apple Silicon Secure Enclave coverage → Phase 4 (testing on physical hardware)
- `thermocline-py` CLI utilities → Phase 1 if added, otherwise Phase 4 ops docs
- Cross-language `thermocline-ts` / `thermocline-rs` → out of v0.1 scope (deferred suite milestone)
- Spec patches discovered during Phase 1 → land as separate commits in this phase (not deferred)
