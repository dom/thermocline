"""AT-C5: Result-policy escalation — forge cannot modify result_policy post-sign.

Failure mode: an adversarial forge modifies result_policy in-flight after the
sovereign signed the envelope. Mitigation: result_policy is inside the
canonicalize() input for dispatch_signature; any mutation invalidates the sig.
"""
# AT-SURFACE: AT-C5
from __future__ import annotations

import json
from pathlib import Path

import pytest

from thermocline.canonical import canonicalize

_CONFORMANCE = Path(__file__).resolve().parents[3] / "conformance"


@pytest.mark.at_surface("AT-C5")
def test_result_policy_modification_changes_canonical_bytes() -> None:
    """AT-C5: mutating result_policy post-signing must invalidate the signature.

    The signature covers canonicalize(envelope - sig); result_policy is part of
    envelope; any post-sign mutation makes canonicalize() yield different bytes.
    """
    envelope = {
        "thermocline": "0.3.1",
        "type": "task",
        "envelope_id": "00000000-0000-0000-0000-00000000c500",
        "issuer": "alice-node",
        "task": {"type": "data.compute", "parameters": {"digits": 100}},
        "result_policy": {"allowed_output_fields": ["pi"]},
    }
    original = canonicalize(envelope)
    mutated = json.loads(json.dumps(envelope))
    mutated["result_policy"]["allowed_output_fields"].append("result_modified_by_forge")
    assert canonicalize(mutated) != original, (
        "AT-C5: result_policy mutation MUST change canonical bytes"
    )


@pytest.mark.at_surface("AT-C5")
def test_result_policy_modified_fixture_present() -> None:
    """AT-C5 fixture: the result-policy-modified fixture is committed and well-formed."""
    fixture = _CONFORMANCE / "invalid" / "AT-C5-result-policy-modified.json"
    assert fixture.is_file(), f"AT-C5: missing fixture {fixture}"
    data = json.loads(fixture.read_text())
    assert data.get("_at_surface") == "AT-C5"
    assert "result_policy" in data, "AT-C5 fixture must carry result_policy"
