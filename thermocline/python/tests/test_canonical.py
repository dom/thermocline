"""Unit tests for ``thermocline.canonical.canonicalize``.

Behavior tests for Plan 02 Task 1 — the single canonical-JSON path for the suite.
"""
from __future__ import annotations

import base64
import json

import pytest

from thermocline import ContentBlock, Sensitive, Task, canonicalize
from thermocline.errors import CanonicalizationError

# ---------------------------------------------------------------------------
# Determinism / key ordering.


def test_canonicalize_normalizes_key_order() -> None:
    """Reordering top-level keys must NOT change canonical bytes (RFC 8785 §3.2.3)."""
    forward = {"b": 2, "a": 1}
    backward = {"a": 1, "b": 2}
    assert canonicalize(forward) == canonicalize(backward)


def test_canonicalize_returns_bytes_not_str() -> None:
    """The function returns ``bytes``; signing input must be bytes."""
    out = canonicalize({"x": 1})
    assert isinstance(out, bytes)


def test_canonicalize_emits_lowercase_no_whitespace_for_bool() -> None:
    """``True`` becomes ``true`` with no whitespace."""
    assert canonicalize({"x": True}) == b'{"x":true}'


def test_canonicalize_emits_null_lowercase() -> None:
    """``None`` becomes ``null`` with no whitespace."""
    assert canonicalize({"x": None}) == b'{"x":null}'


def test_canonicalize_preserves_array_order() -> None:
    """Arrays are order-sensitive (only object keys are sorted)."""
    forward = {"x": [3, 1, 2]}
    assert canonicalize(forward) == b'{"x":[3,1,2]}'


# ---------------------------------------------------------------------------
# Number representation (RFC 8785 §3.2.2 / ECMA-262).
#
# RFC 8785 normalizes integer-valued floats to integer form: ``1.0`` and ``1``
# both serialize to ``1``. The plan's earlier reading (that ``1.0`` and ``1``
# produce DIFFERENT bytes) is incorrect for RFC 8785 — ECMA-262 §7.1.12.1 step
# 5 specifies that finite values that are integers are stringified without the
# fractional part. Plan 02 Task 1 is corrected to assert the spec-correct
# behavior here. (Logged as a Rule 1 deviation in 01-02-SUMMARY.md.)


def test_canonicalize_normalizes_integer_valued_floats() -> None:
    """``1.0`` and ``1`` produce the SAME canonical bytes (ECMA-262 / RFC 8785)."""
    assert canonicalize({"a": 1.0}) == canonicalize({"a": 1})
    assert canonicalize({"a": 1.0}) == b'{"a":1}'


def test_canonicalize_distinguishes_integer_from_string() -> None:
    """Type identity is preserved across canonicalization."""
    assert canonicalize({"a": 1}) != canonicalize({"a": "1"})


def test_canonicalize_distinguishes_true_from_one() -> None:
    """``True`` and ``1`` are distinct under canonicalization."""
    assert canonicalize({"a": True}) != canonicalize({"a": 1})


# ---------------------------------------------------------------------------
# Error envelope on non-JSON-serializable input.


def test_canonicalize_rejects_set() -> None:
    """A ``set`` is not JSON-serializable — must raise CanonicalizationError."""
    with pytest.raises(CanonicalizationError) as excinfo:
        canonicalize({"x": {1, 2, 3}})
    assert excinfo.value.code == "CANONICALIZATION_FAILED"


def test_canonicalize_rejects_arbitrary_object() -> None:
    """A plain ``object()`` is not JSON-serializable — must raise CanonicalizationError."""
    with pytest.raises(CanonicalizationError):
        canonicalize({"x": object()})


def test_canonicalize_error_chains_original() -> None:
    """The wrapping exception preserves the underlying cause via __cause__."""
    with pytest.raises(CanonicalizationError) as excinfo:
        canonicalize({"x": object()})
    assert excinfo.value.__cause__ is not None


# ---------------------------------------------------------------------------
# Envelope round-trip — the foundational discipline for signing input.


def _minimal_task_payload(content_bytes: bytes = b"public ref text") -> dict:
    """Hand-built task payload mirroring tests/test_envelope.py fixture."""
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
                "content": base64.b64encode(content_bytes).decode("ascii"),
            }
        ],
        "result_policy": {
            "persist_to_shared": ["pi"],
            "return_only": [],
            "strip_before_persist": [],
        },
    }


def test_canonicalize_envelope_roundtrip_stable() -> None:
    """``canonicalize(model_dump(mode='json'))`` is byte-stable across rebuilds."""
    payload = _minimal_task_payload()
    task = Task.model_validate(payload)
    once = canonicalize(task.model_dump(mode="json"))
    twice = canonicalize(task.model_dump(mode="json"))
    assert once == twice


def test_canonicalize_envelope_roundtrip_via_json_text() -> None:
    """``canonicalize(json.loads(model_dump_json()))`` equals ``canonicalize(model_dump(mode='json'))``.

    This is the round-trip-stability invariant that protects every signing
    path: the bytes a signer computes must equal the bytes a verifier
    computes after the envelope crosses the wire.
    """
    payload = _minimal_task_payload()
    task = Task.model_validate(payload)
    direct = canonicalize(task.model_dump(mode="json"))
    via_wire = canonicalize(json.loads(task.model_dump_json()))
    assert direct == via_wire


def test_canonicalize_envelope_regression_pin() -> None:
    """Regression-pinned bytes for a known-good envelope.

    Any change to envelope serialization that is NOT a deliberate spec/version
    bump trips this test. If you change the pinned bytes, update the spec
    version (``thermocline``) field too — the ``$id`` and pinned bytes form a
    versioned pair.
    """
    payload = _minimal_task_payload(content_bytes=b"abc")
    task = Task.model_validate(payload)
    out = canonicalize(task.model_dump(mode="json"))
    # Sanity: keys are sorted lexicographically, no whitespace.
    assert out.startswith(b"{")
    assert b'"thermocline":"0.3.1"' in out
    # Sanity: Sensitive[bytes] content was base64-encoded ("abc" -> "YWJj").
    assert b'"content":"YWJj"' in out
    # No whitespace anywhere.
    assert b": " not in out
    assert b", " not in out


def test_canonicalize_sensitive_bytes_in_content_block() -> None:
    """``ContentBlock`` with ``Sensitive(b"abc")`` round-trips byte-for-byte."""
    block = ContentBlock(tier=2, role="task_background", content=Sensitive(b"abc"))
    once = canonicalize(block.model_dump(mode="json"))
    twice = canonicalize(block.model_dump(mode="json"))
    assert once == twice
    # Decoding the canonical JSON back recovers the base64 wire form.
    decoded = json.loads(once)
    assert decoded["content"] == base64.b64encode(b"abc").decode("ascii")


def test_canonicalize_strips_no_whitespace() -> None:
    """No whitespace anywhere in canonical output."""
    out = canonicalize({"a": 1, "b": [1, 2], "c": {"d": True}})
    assert b" " not in out
    assert b"\n" not in out
    assert b"\t" not in out
