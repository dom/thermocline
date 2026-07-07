"""AT-C2: Envelope replay — replayed envelope_id must be rejected.

Failure mode: an envelope previously processed (audit-logged) MUST be rejected
on second arrival. Mitigation in v0.1: receiver's audit log dedupe on envelope_id.
The dedupe layer itself is a Photophore concern (AT-A1 covers the channel side);
this thermocline-side test asserts the fixture is well-formed and the spec
contract is documented.
"""
# AT-SURFACE: AT-C2
from __future__ import annotations

import json
from pathlib import Path

import pytest

from thermocline import BrineProvider, Verifier, sign_envelope, verify_envelope

_CONFORMANCE = Path(__file__).resolve().parents[3] / "conformance"


@pytest.mark.at_surface("AT-C2")
def test_envelope_replay_fixture_well_formed() -> None:
    """AT-C2 fixture: replay envelope_pair has identical envelope_id across first/replay.

    The cross-impl conformance contract: any compliant impl reads the fixture,
    dispatches first_dispatch (audit-logged), attempts replay (must reject).
    """
    fixture = _CONFORMANCE / "invalid" / "AT-C1-replayed-envelope.json"
    # Note: the existing fixture is filed under AT-C1 due to an early naming
    # drift; the JSON content tests AT-C2 (replay). The MANIFEST.yaml encodes
    # the authoritative mapping. We accept this filename mismatch and surface
    # it as a documented known limitation.
    data = json.loads(fixture.read_text())
    assert "envelope_pair" in data, "AT-C2: fixture must carry envelope_pair"
    pair = data["envelope_pair"]
    first = pair["first_dispatch"]
    replay = pair["replay"]
    assert first["envelope_id"] == replay["envelope_id"], (
        "AT-C2: replay must use the same envelope_id as first_dispatch"
    )


@pytest.mark.at_surface("AT-C2")
def test_tampered_envelope_fails_verification(brine_in_memory_keyring) -> None:
    """AT-C2 behavioral: sign an envelope, tamper it, verify returns None.

    The AT-C2 fixture (AT-C2-tampered-signature.json) documents an envelope
    whose payload was mutated after signing. This wires that surface with a
    real signature: any post-sign field mutation makes verify_envelope refuse
    to produce a Receipt. Dedupe of replayed (unmodified) envelopes is a
    Photophore audit-log concern; envelope-layer integrity is proven here.
    """
    provider = BrineProvider(keyring_service="thermocline.test.atc2")
    provider.generate(identity="alice-node")
    verifier = Verifier()
    verifier.register(provider)

    envelope = {
        "thermocline": "0.3.1",
        "type": "task",
        "envelope_id": "a1b2c3d4-0000-4000-8000-000000000002",
        "issued_at": "2026-05-08T00:00:00Z",
        "issuer": "alice-node",
        "channel_id": "chan-pi-forge-local",
        "task": {
            "type": "data.compute",
            "instruction": "Compute pi to 100 digits.",
            "parameters": {"digits": 100},
        },
        "context": [],
        "dispatch_signature": {
            "key_scheme": "brine",
            "node_id": "alice-node",
            "channel_id": "chan-pi-forge-local",
            "timestamp": "2026-05-08T00:00:00Z",
            "sig": "",
        },
    }
    signed = sign_envelope(envelope, provider, signer_identity="alice-node")
    payload = signed.model_dump(mode="json")
    # Sanity: the untampered envelope verifies.
    assert verify_envelope(payload, verifier) is not None
    # Tamper: mutate a payload field after signing.
    payload["task"]["parameters"]["digits"] = 999
    assert verify_envelope(payload, verifier) is None
