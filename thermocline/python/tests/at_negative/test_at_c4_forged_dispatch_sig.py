"""AT-C4: Forged dispatch signature — signature signed with wrong key must fail verification.

Failure mode: an adversary signs an envelope with a key that's not the issuer's
declared key. Mitigation: Verifier.verify() looks up the issuer's public key
via the IdentityProvider and rejects on byte-mismatch; returns None.
"""
# AT-SURFACE: AT-C4
from __future__ import annotations

import json
from pathlib import Path

import pytest

from thermocline import BrineProvider, Signature, Verifier, sign_envelope, verify_envelope
from thermocline.schemes import KeyScheme

_CONFORMANCE = Path(__file__).resolve().parents[3] / "conformance"


@pytest.mark.at_surface("AT-C4")
def test_forged_dispatch_signature_fixture_well_formed() -> None:
    """AT-C4 fixture: key_scheme-mismatch envelope demonstrates the scheme dispatch defense.

    The fixture's dispatch_signature.scheme MUST NOT match the channel's
    declared key_scheme; Verifier rejects via SchemeError or returns None
    when the provider for the claimed scheme is not registered.
    """
    fixture = _CONFORMANCE / "invalid" / "AT-C4-key-scheme-mismatch.json"
    data = json.loads(fixture.read_text())
    sig = data.get("dispatch_signature")
    assert sig is not None, "AT-C4: fixture must carry dispatch_signature"
    assert "scheme" in sig or "key_scheme" in sig, (
        "AT-C4: dispatch_signature must declare its scheme"
    )


@pytest.mark.at_surface("AT-C4")
def test_forged_dispatch_signature_returns_none(brine_in_memory_keyring) -> None:
    """AT-C4 behavioral: a signature forged with the wrong key fails verification.

    An attacker signs with their own key but claims to be alice-node. The
    verifier looks up alice-node's registered public key; the forged bytes do
    not verify against it, so no Receipt is produced.
    """
    alice = BrineProvider(keyring_service="thermocline.test.atc4.alice")
    alice.generate(identity="alice-node")

    attacker = BrineProvider(keyring_service="thermocline.test.atc4.attacker")
    attacker.generate(identity="attacker")

    # Verifier role knows only alice-node's public key.
    verifier_role = BrineProvider(keyring_service="thermocline.test.atc4.verifier")
    verifier_role.register_public_key(
        identity="alice-node", verify_key=alice.public_key(identity="alice-node")
    )
    verifier = Verifier()
    verifier.register(verifier_role)

    envelope = {
        "thermocline": "0.3.1",
        "type": "task",
        "envelope_id": "a1b2c3d4-0000-4000-8000-000000000004",
        "issued_at": "2026-05-08T00:00:00Z",
        "issuer": "alice-node",
        "channel_id": "chan-x",
        "task": {"type": "data.compute", "instruction": "x", "parameters": {}},
        "context": [],
        "dispatch_signature": {
            "key_scheme": "brine",
            "node_id": "alice-node",
            "channel_id": "chan-x",
            "timestamp": "2026-05-08T00:00:00Z",
            "sig": "",
        },
    }
    # Attacker signs the envelope (which claims node_id=alice-node) with the
    # attacker's key, then presents it as alice-node's signature.
    forged = sign_envelope(
        {**envelope, "dispatch_signature": {**envelope["dispatch_signature"], "node_id": "attacker"}},
        attacker,
        signer_identity="attacker",
    )
    payload = forged.model_dump(mode="json")
    payload["dispatch_signature"]["node_id"] = "alice-node"
    assert verify_envelope(payload, verifier) is None


@pytest.mark.at_surface("AT-C4")
def test_scheme_mismatch_raises(brine_in_memory_keyring) -> None:
    """AT-C4 companion: a signature claiming a scheme the envelope did not
    declare is rejected by the Verifier scheme-dispatch (SchemeError)."""
    from thermocline.errors import SchemeError

    provider = BrineProvider(keyring_service="thermocline.test.atc4b")
    verifier = Verifier()
    verifier.register(provider)
    envelope = {"type": "task", "dispatch_signature": {"key_scheme": "brine", "node_id": "a"}}
    pgp_sig = Signature(scheme=KeyScheme.PGP, bytes_=b"\x00" * 64, signer_identity="a")
    with pytest.raises(SchemeError):
        verifier.verify(envelope=envelope, signature=pgp_sig)
