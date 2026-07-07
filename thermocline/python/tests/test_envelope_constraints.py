"""Finding 10: JobResult / Task / shadow field constraints.

* JobResult.halt_reason is one of the seven defined halt codes (Literal).
* status/artifact/halt_reason coupling: artifact is non-null only when
  status=="complete"; halt_reason is required (and only allowed) on
  failed/halted per README (§"Job Result Envelope": "On failed or halted,
  artifact is null and halt_reason carries one of the defined halt codes").
* _Shadow.relevance is bounded to [0.0, 1.0].
* uuid / iso8601 pattern validation on ids and timestamps.
* receipt_signature.envelope_id (when present) matches the outer envelope_id.
"""
from __future__ import annotations

import base64

import pytest
from pydantic import ValidationError

from thermocline import ContentBlock, JobResult, Task, TaskResult


def _job_result(**overrides) -> dict:
    base = {
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
            "data": base64.b64encode(b"x").decode("ascii"),
        },
        "provenance": {
            "shadows_received": [],
            "tiers_present": [2],
            "steps_executed": ["s1"],
            "local_tiers_present": False,
        },
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Halt codes (Literal) + status coupling.


def test_halt_reason_must_be_a_defined_code() -> None:
    payload = _job_result(status="halted", artifact=None, halt_reason="NOT_A_CODE")
    with pytest.raises(ValidationError):
        JobResult.model_validate(payload)


def test_halted_requires_halt_reason() -> None:
    payload = _job_result(status="halted", artifact=None, halt_reason=None)
    with pytest.raises(ValidationError):
        JobResult.model_validate(payload)


def test_halted_with_valid_code_and_null_artifact_accepted() -> None:
    payload = _job_result(status="halted", artifact=None, halt_reason="TIMEOUT")
    jr = JobResult.model_validate(payload)
    assert jr.halt_reason == "TIMEOUT"
    assert jr.artifact is None


def test_complete_with_halt_reason_rejected() -> None:
    payload = _job_result(status="complete", halt_reason="TIMEOUT")
    with pytest.raises(ValidationError):
        JobResult.model_validate(payload)


def test_artifact_present_on_non_complete_rejected() -> None:
    payload = _job_result(status="failed", halt_reason="TIMEOUT")  # artifact still set
    with pytest.raises(ValidationError):
        JobResult.model_validate(payload)


def test_failed_with_null_artifact_and_halt_reason_accepted() -> None:
    payload = _job_result(status="failed", artifact=None, halt_reason="CONTRACT_MISMATCH")
    jr = JobResult.model_validate(payload)
    assert jr.status == "failed"


def test_complete_with_artifact_accepted() -> None:
    jr = JobResult.model_validate(_job_result())
    assert jr.status == "complete"
    assert jr.artifact is not None


# ---------------------------------------------------------------------------
# Shadow relevance bounds.


def test_shadow_relevance_above_one_rejected() -> None:
    with pytest.raises(ValidationError):
        ContentBlock.model_validate(
            {
                "tier": 1,
                "role": "user_file",
                "shadow": {
                    "shadow_id": "0" * 32,
                    "content_type": "document",
                    "abstraction": "x",
                    "relevance": 1.5,
                },
            }
        )


def test_shadow_relevance_below_zero_rejected() -> None:
    with pytest.raises(ValidationError):
        ContentBlock.model_validate(
            {
                "tier": 1,
                "role": "user_file",
                "shadow": {
                    "shadow_id": "0" * 32,
                    "content_type": "document",
                    "abstraction": "x",
                    "relevance": -0.1,
                },
            }
        )


# ---------------------------------------------------------------------------
# uuid / iso8601 patterns.


def _valid_task() -> dict:
    return {
        "thermocline": "0.3.1",
        "type": "task",
        "envelope_id": "a1b2c3d4-0000-4000-8000-000000000001",
        "issued_at": "2026-05-08T00:00:00Z",
        "issuer": "my-sovereign-node",
        "channel_id": "chan",
        "task": {"type": "data.compute", "instruction": "x", "parameters": {}},
        "context": [],
    }


def test_task_rejects_non_uuid_envelope_id() -> None:
    payload = _valid_task()
    payload["envelope_id"] = "not-a-uuid"
    with pytest.raises(ValidationError):
        Task.model_validate(payload)


def test_task_rejects_non_iso8601_issued_at() -> None:
    payload = _valid_task()
    payload["issued_at"] = "yesterday"
    with pytest.raises(ValidationError):
        Task.model_validate(payload)


def test_task_accepts_valid_uuid_and_iso8601() -> None:
    Task.model_validate(_valid_task())


# ---------------------------------------------------------------------------
# receipt_signature.envelope_id must match the outer envelope.


def _task_result(receipt_env_id: str) -> dict:
    return {
        "thermocline": "0.3.1",
        "type": "task_result",
        "envelope_id": "a1b2c3d4-0000-4000-8000-000000000001",
        "result_id": "b2c3d4e5-0000-4000-8000-000000000002",
        "completed_at": "2026-05-08T00:00:01Z",
        "responder": "pi-forge-local",
        "outputs": {"pi": "3.14"},
        "provenance": {
            "shadows_received": [],
            "tiers_present": [2],
            "local_tiers_present": False,
        },
        "receipt_signature": {
            "key_scheme": "brine",
            "node_id": "pi-forge-local",
            "envelope_id": receipt_env_id,
            "inputs_received": [],
            "timestamp": "2026-05-08T00:00:01Z",
            "sig": "",
        },
    }


def test_receipt_signature_envelope_id_mismatch_rejected() -> None:
    payload = _task_result("a1b2c3d4-0000-4000-8000-999999999999")
    with pytest.raises(ValidationError):
        TaskResult.model_validate(payload)


def test_receipt_signature_envelope_id_match_accepted() -> None:
    payload = _task_result("a1b2c3d4-0000-4000-8000-000000000001")
    TaskResult.model_validate(payload)
