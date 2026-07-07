"""AT-C6: Key compromise — rotation primitive documents the recovery path.

Failure mode: an adversary obtains the sovereign's signing key and can produce
valid signatures. Mitigation in v0.1 is NOT prevention (impossible if the
keystore is compromised) but RECOVERY: BrineProvider.rotate() lets the
sovereign generate a fresh key and re-register with channels.

This is a documents-only AT surface: the contract is "rotate() exists and is
callable"; the recovery procedure itself is operator-driven.
"""
# AT-SURFACE: AT-C6
from __future__ import annotations

from pathlib import Path

import pytest

from thermocline import BrineProvider, Verifier, sign_envelope, verify_envelope


def _task(node_id: str) -> dict:
    return {
        "thermocline": "0.3.1",
        "type": "task",
        "envelope_id": "a1b2c3d4-0000-4000-8000-0000000000c6",
        "issued_at": "2026-05-08T00:00:00Z",
        "issuer": node_id,
        "channel_id": "chan-x",
        "task": {"type": "data.compute", "instruction": "x", "parameters": {}},
        "context": [],
        "dispatch_signature": {
            "key_scheme": "brine",
            "node_id": node_id,
            "channel_id": "chan-x",
            "timestamp": "2026-05-08T00:00:00Z",
            "sig": "",
        },
    }


@pytest.mark.at_surface("AT-C6")
def test_rotate_recovers_and_preserves_prior_verifiability(
    brine_in_memory_keyring,
) -> None:
    """AT-C6 behavioral: rotate() gives a fresh key while pre-rotation
    envelopes remain verifiable (the recovery contract, not a hasattr check).
    """
    provider = BrineProvider(keyring_service="thermocline.test.atc6")
    provider.generate(identity="alice")
    verifier = Verifier()
    verifier.register(provider)

    signed = sign_envelope(_task("alice"), provider, signer_identity="alice")
    payload = signed.model_dump(mode="json")
    old_pub = provider.public_key(identity="alice")

    provider.rotate(identity="alice")
    assert provider.public_key(identity="alice") != old_pub
    # Envelope signed before rotation still verifies against the archived key.
    assert verify_envelope(payload, verifier) is not None


@pytest.mark.at_surface("AT-C6")
def test_revoke_rejects_compromised_key(brine_in_memory_keyring) -> None:
    """AT-C6 behavioral: a revoked key no longer produces a Receipt."""
    provider = BrineProvider(keyring_service="thermocline.test.atc6b")
    provider.generate(identity="alice")
    verifier = Verifier()
    verifier.register(provider)

    signed = sign_envelope(_task("alice"), provider, signer_identity="alice")
    payload = signed.model_dump(mode="json")
    assert verify_envelope(payload, verifier) is not None

    provider.revoke(identity="alice")
    assert verify_envelope(payload, verifier) is None


@pytest.mark.at_surface("AT-C6")
@pytest.mark.documents_only
def test_keystore_required_test_exists() -> None:
    """AT-C6: companion runtime test (test_identity_keystore_required.py) is present.

    IDENT-05 keystore-required pattern: thermocline-py refuses to fall back to
    file/env storage. The test confirming this lives at:

        thermocline/python/tests/test_identity_keystore_required.py
    """
    test_root = Path(__file__).resolve().parents[1]
    candidate = test_root / "test_identity_keystore_required.py"
    assert candidate.is_file(), (
        f"AT-C6: companion runtime test missing at {candidate}"
    )
