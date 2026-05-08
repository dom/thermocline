"""Tests for Pydantic v2 envelope models (Task / TaskResult / Job / JobResult / ErrorEnvelope).

Behavior tests for Task 2 (TDD RED phase before implementation lands):

* Each envelope class constructs from a minimal-valid dict.
* model_dump_json round-trips through model_validate_json to an equal instance.
* Unknown ``thermocline`` version raises UnsupportedVersionError (THERMO-07).
* Extra fields raise ValidationError (THERMO-03 / extra="forbid").
* ContentBlock content typed Sensitive[bytes] redacts in repr (Pitfall 4).
* Round-tripping a ContentBlock preserves content bytes byte-for-byte.
* ErrorEnvelope exposes a ``code: str`` field carrying one of the
  thermocline.errors stable codes.
"""
from __future__ import annotations

import base64

import pytest
from pydantic import ValidationError

from thermocline import (
    ContentBlock,
    ErrorEnvelope,
    Job,
    JobResult,
    Sensitive,
    Task,
    TaskResult,
)
from thermocline.errors import UnsupportedVersionError

# ---------------------------------------------------------------------------
# Fixtures.


@pytest.fixture
def valid_task_dict() -> dict:
    """Minimal valid task envelope (mirrors pi-forge/examples/task-100-digits.json)."""
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
        "context": [
            {
                "tier": 2,
                "role": "task_background",
                "content": base64.b64encode(b"public ref text").decode("ascii"),
            }
        ],
        "result_policy": {
            "persist_to_shared": ["pi"],
            "return_only": [],
            "strip_before_persist": [],
        },
    }


@pytest.fixture
def valid_task_result_dict() -> dict:
    return {
        "thermocline": "0.3.1",
        "type": "task_result",
        "envelope_id": "a1b2c3d4-0000-4000-8000-000000000001",
        "result_id": "b2c3d4e5-0000-4000-8000-000000000002",
        "completed_at": "2026-05-08T00:00:01Z",
        "responder": "pi-forge-local",
        "outputs": {"pi": "3.14", "digits_computed": 2},
        "provenance": {
            "shadows_received": [],
            "tiers_present": [2],
            "local_tiers_present": False,
        },
    }


@pytest.fixture
def valid_job_dict() -> dict:
    return {
        "thermocline": "0.3.1",
        "type": "job",
        "job_id": "11111111-2222-4333-8444-555555555555",
        "issued_at": "2026-05-08T00:00:00Z",
        "issuer": "my-sovereign-node",
        "channel_id": "chan-job-1",
        "manifest": {
            "intent": "Generate a PNG image of a quokka.",
            "output_contract": {
                "type": "image",
                "format": "png",
                "destination": "return",
            },
            "constraints": {
                "may_access": ["comfyui"],
                "may_not_access": ["openai"],
                "privacy_fence": "no issuer-origin content may be logged",
            },
            "result_policy": {
                "persist_to_shared": [],
                "return_only": ["artifact"],
                "strip_before_persist": [],
            },
            "timeout_seconds": 300,
        },
        "steps": [
            {
                "step_id": "s1",
                "label": "Render quokka",
                "tool": "comfyui",
                "model": "flux-dev",
                "input": {"source": "manifest", "field": "intent"},
                "context": [],
                "params": {"width": 1024, "height": 1024, "steps": 20},
                "passthrough": ["output"],
                "depends_on": [],
            }
        ],
    }


@pytest.fixture
def valid_job_result_dict() -> dict:
    return {
        "thermocline": "0.3.1",
        "type": "job_result",
        "job_id": "11111111-2222-4333-8444-555555555555",
        "result_id": "99999999-0000-4000-8000-000000000099",
        "status": "complete",
        "completed_at": "2026-05-08T00:01:00Z",
        "responder": "comfyui-forge",
        "halt_reason": None,
        "artifact": {
            "type": "image",
            "format": "png",
            "data": base64.b64encode(b"\x89PNG\r\n\x1a\nfake").decode("ascii"),
        },
        "provenance": {
            "shadows_received": [],
            "tiers_present": [2],
            "steps_executed": ["s1"],
            "local_tiers_present": False,
        },
    }


@pytest.fixture
def valid_error_dict() -> dict:
    return {
        "thermocline": "0.3.1",
        "type": "task_error",
        "envelope_id": "a1b2c3d4-0000-4000-8000-000000000001",
        "error": {
            "code": "UNSUPPORTED_VERSION",
            "message": "Unsupported Thermocline version",
        },
    }


# ---------------------------------------------------------------------------
# Construction + round-trip per envelope class.


def test_task_constructs_from_valid_dict(valid_task_dict: dict) -> None:
    task = Task.model_validate(valid_task_dict)
    assert task.envelope_id == "a1b2c3d4-0000-4000-8000-000000000001"
    assert task.thermocline == "0.3.1"
    assert task.context[0].tier == 2


def test_task_round_trips_through_json(valid_task_dict: dict) -> None:
    task = Task.model_validate(valid_task_dict)
    payload = task.model_dump_json()
    rebuilt = Task.model_validate_json(payload)
    assert rebuilt == task


def test_task_result_constructs_and_round_trips(valid_task_result_dict: dict) -> None:
    tr = TaskResult.model_validate(valid_task_result_dict)
    rebuilt = TaskResult.model_validate_json(tr.model_dump_json())
    assert rebuilt == tr
    assert tr.envelope_id == valid_task_result_dict["envelope_id"]


def test_job_constructs_and_round_trips(valid_job_dict: dict) -> None:
    job = Job.model_validate(valid_job_dict)
    rebuilt = Job.model_validate_json(job.model_dump_json())
    assert rebuilt == job
    assert job.steps[0].step_id == "s1"


def test_job_result_constructs_and_round_trips(valid_job_result_dict: dict) -> None:
    jr = JobResult.model_validate(valid_job_result_dict)
    rebuilt = JobResult.model_validate_json(jr.model_dump_json())
    assert rebuilt == jr


def test_error_envelope_constructs_and_round_trips(valid_error_dict: dict) -> None:
    err = ErrorEnvelope.model_validate(valid_error_dict)
    rebuilt = ErrorEnvelope.model_validate_json(err.model_dump_json())
    assert rebuilt == err
    assert err.error.code == "UNSUPPORTED_VERSION"


# ---------------------------------------------------------------------------
# Version validation (THERMO-07).


def test_task_rejects_unknown_version(valid_task_dict: dict) -> None:
    valid_task_dict["thermocline"] = "0.0.1"
    with pytest.raises(ValidationError) as exc_info:
        Task.model_validate(valid_task_dict)
    # Pydantic wraps the UnsupportedVersionError. Inspect the chain.
    err_str = str(exc_info.value)
    assert "Unsupported Thermocline version" in err_str or "UNSUPPORTED_VERSION" in err_str


def test_task_parse_strict_raises_unsupported_version_error_directly(valid_task_dict: dict) -> None:
    """parse_strict re-raises Pydantic ValidationError as the typed subclass for version errors."""
    valid_task_dict["thermocline"] = "9.9.9"
    with pytest.raises(UnsupportedVersionError) as exc_info:
        Task.parse_strict(valid_task_dict)
    assert exc_info.value.code == "UNSUPPORTED_VERSION"


def test_task_result_rejects_unknown_version(valid_task_result_dict: dict) -> None:
    valid_task_result_dict["thermocline"] = "0.4.0"
    with pytest.raises(ValidationError):
        TaskResult.model_validate(valid_task_result_dict)


# ---------------------------------------------------------------------------
# Strict validation (THERMO-03 / extra="forbid").


@pytest.mark.parametrize(
    "envelope_cls,fixture_name",
    [
        ("Task", "valid_task_dict"),
        ("TaskResult", "valid_task_result_dict"),
        ("Job", "valid_job_dict"),
        ("JobResult", "valid_job_result_dict"),
        ("ErrorEnvelope", "valid_error_dict"),
    ],
)
def test_envelopes_reject_extra_fields(
    envelope_cls: str,
    fixture_name: str,
    request: pytest.FixtureRequest,
) -> None:
    """Every envelope class rejects unknown top-level fields (THERMO-03)."""
    cls = {
        "Task": Task,
        "TaskResult": TaskResult,
        "Job": Job,
        "JobResult": JobResult,
        "ErrorEnvelope": ErrorEnvelope,
    }[envelope_cls]
    payload = dict(request.getfixturevalue(fixture_name))
    payload["__extra_unexpected_field__"] = "should be rejected"
    with pytest.raises(ValidationError) as exc_info:
        cls.model_validate(payload)
    assert "extra" in str(exc_info.value).lower() or "forbidden" in str(exc_info.value).lower() or "extra_forbidden" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# Sensitive[bytes] discipline on ContentBlock (D-03 / Pitfall 4).


def test_content_block_redacts_bytes_in_repr() -> None:
    block = ContentBlock(
        tier=2,
        role="task_background",
        content=Sensitive(b"DO-NOT-LEAK-XYZZY-PRIVATE"),
    )
    rendered = repr(block)
    assert "DO-NOT-LEAK-XYZZY-PRIVATE" not in rendered
    assert "<Sensitive: bytes>" in rendered


def test_content_block_round_trips_bytes_through_json() -> None:
    secret = b"\x00\x01\x02important payload\xff\xfe"
    block = ContentBlock(
        tier=1,
        role="user_file",
        content=Sensitive(secret),
    )
    payload = block.model_dump_json()
    rebuilt = ContentBlock.model_validate_json(payload)
    assert rebuilt.content.reveal() == secret
    assert rebuilt == block


def test_content_block_accepts_raw_bytes_via_validation() -> None:
    block = ContentBlock.model_validate(
        {"tier": 2, "role": "task_background", "content": b"hello"}
    )
    assert isinstance(block.content, Sensitive)
    assert block.content.reveal() == b"hello"


# ---------------------------------------------------------------------------
# ErrorEnvelope code field carries a stable string code.


def test_error_envelope_code_is_stable_string(valid_error_dict: dict) -> None:
    err = ErrorEnvelope.model_validate(valid_error_dict)
    assert isinstance(err.error.code, str)
    # Codes used elsewhere in this library:
    assert err.error.code in {
        "UNSUPPORTED_VERSION",
        "MALFORMED_ENVELOPE",
        "UNSUPPORTED_TASK_TYPE",
        "SIGNATURE_INVALID",
        "CANONICALIZATION_FAILED",
        "IDENTITY_ERROR",
        "UNSUPPORTED_KEY_SCHEME",
        "KEYSTORE_UNAVAILABLE",
        "ENVELOPE_ERROR",
    }
