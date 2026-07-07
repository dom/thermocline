"""Generate JSON Schema Draft 2020-12 artifacts from the Pydantic v2 envelope models.

Schemas are generated from the canonical Pydantic models and committed under
``thermocline/schema/``. CI runs ``--check`` and fails on drift (deleting a
Pydantic field locally and re-running --check exits non-zero with a diff
naming the changed file).

Modes
-----
``--write``
    Regenerate every schema in :data:`SCHEMA_DIR`.

``--check``
    Compare on-disk schemas against freshly-generated ones; exit 1 on diff
    with a unified diff naming each changed file (printed to stderr).

Run as
------
::

    thermocline-build-schemas --check          # console script
    python -m thermocline.scripts.build_schemas --check
"""
from __future__ import annotations

import argparse
import difflib
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from thermocline.envelope import (
    ErrorEnvelope,
    Job,
    JobResult,
    Task,
    TaskResult,
)

# ``parents[4]`` from src/thermocline/scripts/build_schemas.py resolves to the
# ``thermocline/`` repo root. The schema artifacts are committed under
# ``thermocline/schema/`` (sibling of ``thermocline/python/``).
SCHEMA_DIR: Path = Path(__file__).resolve().parents[4] / "schema"

# Stable identifier used as the schema $id. This URL is NOT served at v0.1 — it
# is a stable string used for $ref resolution in cross-language consumers
# (thermocline-ts / thermocline-rs ports). Kept under a domain we control so
# we can host the artifacts later without breaking IDs.
SCHEMA_BASE_ID = "https://thermocline.spec/schema/v0.3.1"
SCHEMA_DRAFT = "https://json-schema.org/draft/2020-12/schema"

ENVELOPES: dict[str, type] = {
    "task": Task,
    "task_result": TaskResult,
    "job": Job,
    "job_result": JobResult,
    "error": ErrorEnvelope,
}


# --- Tier-semantics if/then clauses (invariant #1) -------------------------
#
# Pydantic does not emit conditional keywords for a ``model_validator``, so we
# inject the tier rules into every ``ContentBlock`` $def by hand. This keeps
# the JSON Schema artifacts (the language-agnostic contract) in lockstep with
# ``ContentBlock._enforce_tier_semantics`` so cross-language ports inherit the
# rule. "Absent" tolerates an explicit JSON ``null`` so a model_dump that emits
# ``"shadow": null`` on a tier-2 block still validates.

_CONTENT_PRESENT: dict[str, Any] = {
    "required": ["content"],
    "properties": {"content": {"not": {"type": "null"}}},
}
_CONTENT_ABSENT: dict[str, Any] = {
    "anyOf": [
        {"not": {"required": ["content"]}},
        {"properties": {"content": {"type": "null"}}},
    ]
}
_SHADOW_PRESENT: dict[str, Any] = {
    "required": ["shadow"],
    "properties": {"shadow": {"not": {"type": "null"}}},
}
_SHADOW_ABSENT: dict[str, Any] = {
    "anyOf": [
        {"not": {"required": ["shadow"]}},
        {"properties": {"shadow": {"type": "null"}}},
    ]
}


def _tier_rule(tier: int, *clauses: dict[str, Any]) -> dict[str, Any]:
    return {
        "if": {"properties": {"tier": {"const": tier}}, "required": ["tier"]},
        "then": {"allOf": list(clauses)},
    }


_CONTENT_BLOCK_TIER_RULES: list[dict[str, Any]] = [
    # tier 0 (local): no content, no shadow -- never in a dispatched envelope.
    _tier_rule(0, _CONTENT_ABSENT, _SHADOW_ABSENT),
    # tier 1 (shared): shadow required, content forbidden.
    _tier_rule(1, _SHADOW_PRESENT, _CONTENT_ABSENT),
    # tier 2 (public): content required, shadow forbidden.
    _tier_rule(2, _CONTENT_PRESENT, _SHADOW_ABSENT),
]


def _inject_tier_rules(schema: dict[str, Any]) -> None:
    """Attach the tier if/then clauses to every ContentBlock $def in ``schema``."""
    defs = schema.get("$defs")
    if not isinstance(defs, dict):
        return
    block = defs.get("ContentBlock")
    if isinstance(block, dict):
        existing = block.get("allOf")
        rules = [dict(rule) for rule in _CONTENT_BLOCK_TIER_RULES]
        block["allOf"] = (list(existing) if isinstance(existing, list) else []) + rules


def generate_schema(name: str, model_cls: type) -> dict[str, Any]:
    """Return a JSON Schema dict for ``model_cls`` with stable $id + $schema."""
    schema: dict[str, Any] = model_cls.model_json_schema(mode="validation")  # type: ignore[attr-defined]
    schema["$schema"] = SCHEMA_DRAFT
    schema["$id"] = f"{SCHEMA_BASE_ID}/{name}.schema.json"
    _inject_tier_rules(schema)
    return schema


def _serialize_schema(schema: dict[str, Any]) -> str:
    """Format a schema as deterministic on-disk JSON.

    sort_keys=True + indent=2 + trailing newline gives a stable byte sequence
    that diff cleanly across regenerations and across third-party reviewers.
    """
    # OK: emits a schema artifact to disk (not a signing input). The
    # no-json-dumps lint forbids json.dumps as signing input only —
    # canonical JSON via rfc8785 is used wherever a signature is produced.
    # pitfall-11 OK: schema artifact, not signing input.
    return json.dumps(  # not a signing path
        schema, indent=2, sort_keys=True
    ) + "\n"


def write_all() -> None:
    """Regenerate every schema in :data:`SCHEMA_DIR`."""
    SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
    for name, cls in ENVELOPES.items():
        target = SCHEMA_DIR / f"{name}.schema.json"
        target.write_text(_serialize_schema(generate_schema(name, cls)))


def check_all() -> int:
    """Return 0 if on-disk schemas match the models; 1 otherwise.

    Drift output goes to stderr so CI logs surface the failure naturally.
    """
    drift: list[str] = []
    for name, cls in ENVELOPES.items():
        target = SCHEMA_DIR / f"{name}.schema.json"
        fresh = _serialize_schema(generate_schema(name, cls))
        if not target.exists():
            drift.append(f"missing: {target}")
            continue
        existing = target.read_text()
        if existing != fresh:
            diff = "\n".join(
                difflib.unified_diff(
                    existing.splitlines(),
                    fresh.splitlines(),
                    fromfile=str(target),
                    tofile="(generated)",
                    lineterm="",
                )
            )
            drift.append(f"drift in: {target}\n{diff}")
    if drift:
        for entry in drift:
            sys.stderr.write(entry + "\n")
        return 1
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Console-script entry point.

    Returns the process exit code (0 for success, 1 for drift / failure).
    """
    parser = argparse.ArgumentParser(
        prog="thermocline-build-schemas",
        description="Generate or check JSON Schema artifacts for Thermocline envelopes.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--write",
        action="store_true",
        help="Regenerate every schema under thermocline/schema/.",
    )
    group.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if on-disk schemas differ from the Pydantic models.",
    )
    args = parser.parse_args(argv)
    if args.write:
        write_all()
        sys.stderr.write(f"wrote schemas to {SCHEMA_DIR}\n")
        return 0
    return check_all()


if __name__ == "__main__":
    sys.exit(main())
