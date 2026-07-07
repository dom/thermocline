"""Tier-semantics enforcement on ContentBlock (invariant #1 of the suite).

The privacy-tier contract from the spec README ("Privacy Tiers"):

* tier 0 (``local``): never dispatched. A tier-0 block in an envelope must
  not carry ``content`` or ``shadow``; raw local bytes in a dispatched
  envelope are a privacy-boundary violation, not a soft warning.
* tier 1 (``shared``): dispatched only as a shadow. Requires ``shadow``;
  must not carry ``content``.
* tier 2 (``public``): dispatched as-is. Requires ``content``; must not
  carry ``shadow``.

Prior to 0.4.0 these rules lived in a comment; the envelope layer now
enforces them via a Pydantic ``model_validator``, and the JSON Schema
artifacts carry matching ``if``/``then`` clauses so cross-language ports
inherit the rule.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

import jsonschema
import pytest
from pydantic import ValidationError

from thermocline import ContentBlock, Sensitive, Task

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schema"


def _shadow_dict() -> dict:
    return {
        "shadow_id": "0f1a2b3c4d5e6f7080a1b2c3d4e5f607",
        "content_type": "document",
        "abstraction": "A financial summary document",
        "relevance": 0.85,
    }


# ---------------------------------------------------------------------------
# Tier 0: local blocks must not appear with payload in a dispatched envelope.


def test_tier0_with_content_rejected() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ContentBlock(tier=0, role="local_file", content=Sensitive(b"private"))
    assert "tier-0" in str(exc_info.value)


def test_tier0_with_shadow_rejected() -> None:
    with pytest.raises(ValidationError):
        ContentBlock.model_validate(
            {"tier": 0, "role": "local_file", "shadow": _shadow_dict()}
        )


# ---------------------------------------------------------------------------
# Tier 1: shadow required, content forbidden.


def test_tier1_requires_shadow() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ContentBlock(tier=1, role="user_file")
    assert "tier-1" in str(exc_info.value)


def test_tier1_with_raw_content_rejected() -> None:
    with pytest.raises(ValidationError):
        ContentBlock(tier=1, role="user_file", content=Sensitive(b"leak"))


def test_tier1_with_shadow_and_content_rejected() -> None:
    with pytest.raises(ValidationError):
        ContentBlock.model_validate(
            {
                "tier": 1,
                "role": "user_file",
                "shadow": _shadow_dict(),
                "content": base64.b64encode(b"leak").decode("ascii"),
            }
        )


def test_tier1_with_shadow_only_accepted() -> None:
    block = ContentBlock.model_validate(
        {"tier": 1, "role": "user_file", "shadow": _shadow_dict()}
    )
    assert block.shadow is not None
    assert block.content is None


# ---------------------------------------------------------------------------
# Tier 2: content required, shadow forbidden.


def test_tier2_requires_content() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ContentBlock(tier=2, role="task_background")
    assert "tier-2" in str(exc_info.value)


def test_tier2_with_shadow_rejected() -> None:
    with pytest.raises(ValidationError):
        ContentBlock.model_validate(
            {"tier": 2, "role": "task_background", "shadow": _shadow_dict()}
        )


def test_tier2_with_content_only_accepted() -> None:
    block = ContentBlock(tier=2, role="task_background", content=Sensitive(b"public"))
    assert block.content is not None
    assert block.shadow is None


# ---------------------------------------------------------------------------
# The rule is enforced through envelope parsing, not just direct construction.


def _task_dict_with_context(context: list[dict]) -> dict:
    return {
        "thermocline": "0.3.1",
        "type": "task",
        "envelope_id": "a1b2c3d4-0000-4000-8000-000000000001",
        "issued_at": "2026-05-08T00:00:00Z",
        "issuer": "my-sovereign-node",
        "channel_id": "chan-pi-forge-local",
        "task": {
            "type": "data.compute",
            "instruction": "Compute pi to 100 digits.",
            "parameters": {"digits": 100},
        },
        "context": context,
    }


def test_task_parse_strict_rejects_tier1_block_with_raw_content() -> None:
    payload = _task_dict_with_context(
        [
            {
                "tier": 1,
                "role": "user_file",
                "content": base64.b64encode(b"raw private bytes").decode("ascii"),
            }
        ]
    )
    with pytest.raises(ValidationError):
        Task.parse_strict(payload)


def test_task_parse_strict_rejects_tier0_block_with_content() -> None:
    payload = _task_dict_with_context(
        [
            {
                "tier": 0,
                "role": "local_file",
                "content": base64.b64encode(b"local-only bytes").decode("ascii"),
            }
        ]
    )
    with pytest.raises(ValidationError):
        Task.parse_strict(payload)


# ---------------------------------------------------------------------------
# JSON Schema artifacts carry the same rule (cross-language ports inherit it).


@pytest.mark.parametrize("schema_name", ["task", "job"])
def test_schema_rejects_tier1_block_with_raw_content(schema_name: str) -> None:
    schema = json.loads((SCHEMA_DIR / f"{schema_name}.schema.json").read_text())
    block_schema = schema["$defs"]["ContentBlock"]
    validator = jsonschema.Draft202012Validator(
        {"$defs": schema["$defs"], **block_schema}
    )
    bad = {
        "tier": 1,
        "role": "user_file",
        "content": base64.b64encode(b"raw").decode("ascii"),
    }
    errors = list(validator.iter_errors(bad))
    assert errors, "schema must reject a tier-1 block carrying raw content"

    good = {"tier": 1, "role": "user_file", "shadow": _shadow_dict()}
    assert list(validator.iter_errors(good)) == []


def test_schema_rejects_tier0_block_with_content() -> None:
    schema = json.loads((SCHEMA_DIR / "task.schema.json").read_text())
    block_schema = schema["$defs"]["ContentBlock"]
    validator = jsonschema.Draft202012Validator(
        {"$defs": schema["$defs"], **block_schema}
    )
    bad = {
        "tier": 0,
        "role": "local_file",
        "content": base64.b64encode(b"raw").decode("ascii"),
    }
    assert list(validator.iter_errors(bad)), (
        "schema must reject a tier-0 block carrying content"
    )


def test_schema_rejects_tier2_block_without_content() -> None:
    schema = json.loads((SCHEMA_DIR / "task.schema.json").read_text())
    block_schema = schema["$defs"]["ContentBlock"]
    validator = jsonschema.Draft202012Validator(
        {"$defs": schema["$defs"], **block_schema}
    )
    assert list(validator.iter_errors({"tier": 2, "role": "task_background"})), (
        "schema must reject a tier-2 block without content"
    )
