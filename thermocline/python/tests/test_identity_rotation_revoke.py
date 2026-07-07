"""Finding 5: key rotation archives the old verify key; revoke rejects.

README §"Required Capabilities" / §"Constraints":
* ``key.rotate`` archives the old key; a rotated key remains valid for
  verification of envelopes signed before the rotation.
* ``key.revoke`` marks a key revoked; verifiers must reject its signatures.
"""
from __future__ import annotations

import pytest

from thermocline import BrineProvider, IdentityError, Verifier
from thermocline.schemes import KeyScheme
from thermocline.signing import sign_envelope, verify_envelope


def _task(node_id: str) -> dict:
    return {
        "thermocline": "0.3.1",
        "type": "task",
        "envelope_id": "a1b2c3d4-0000-4000-8000-000000000042",
        "issued_at": "2026-05-08T00:00:00Z",
        "issuer": node_id,
        "channel_id": "chan-x",
        "task": {"type": "data.compute", "instruction": "pi", "parameters": {}},
        "context": [],
        "dispatch_signature": {
            "key_scheme": "brine",
            "node_id": node_id,
            "channel_id": "chan-x",
            "timestamp": "2026-05-08T00:00:00Z",
            "sig": "",
        },
    }


def test_envelope_signed_before_rotation_still_verifies(brine_in_memory_keyring):
    provider = BrineProvider(keyring_service="thermocline.test.rot")
    provider.generate(identity="alice")
    verifier = Verifier()
    verifier.register(provider)

    signed = sign_envelope(_task("alice"), provider, signer_identity="alice")
    payload = signed.model_dump(mode="json")

    # Rotate: the current key changes, the old verify key is archived.
    provider.rotate(identity="alice")

    # The pre-rotation signature still verifies against the archived key.
    receipt = verify_envelope(payload, verifier)
    assert receipt is not None
    assert receipt.verified_identity == "alice"


def test_rotate_archives_and_current_key_changes(brine_in_memory_keyring):
    provider = BrineProvider(keyring_service="thermocline.test.rot")
    provider.generate(identity="alice")
    old_pub = provider.public_key(identity="alice")
    provider.rotate(identity="alice")
    assert provider.public_key(identity="alice") != old_pub


def test_revoked_current_key_is_rejected(brine_in_memory_keyring):
    provider = BrineProvider(keyring_service="thermocline.test.rev")
    provider.generate(identity="alice")
    verifier = Verifier()
    verifier.register(provider)

    signed = sign_envelope(_task("alice"), provider, signer_identity="alice")
    payload = signed.model_dump(mode="json")
    # Sanity: verifies before revocation.
    assert verify_envelope(payload, verifier) is not None

    provider.revoke(identity="alice")
    assert verify_envelope(payload, verifier) is None


def test_public_key_raises_after_revocation(brine_in_memory_keyring):
    provider = BrineProvider(keyring_service="thermocline.test.rev")
    provider.generate(identity="alice")
    provider.revoke(identity="alice")
    with pytest.raises(IdentityError) as exc:
        provider.public_key(identity="alice")
    assert exc.value.code == "KEY_REVOKED"


def test_revoked_archived_version_is_rejected(brine_in_memory_keyring):
    """Revoking a specific archived version stops it verifying old envelopes."""
    provider = BrineProvider(keyring_service="thermocline.test.rev2")
    provider.generate(identity="alice")
    verifier = Verifier()
    verifier.register(provider)

    signed = sign_envelope(_task("alice"), provider, signer_identity="alice")
    payload = signed.model_dump(mode="json")
    provider.rotate(identity="alice")  # old key becomes archive version 0
    assert verify_envelope(payload, verifier) is not None  # archive verifies

    provider.revoke(identity="alice", key_version=0)
    assert verify_envelope(payload, verifier) is None


def test_revoke_unknown_identity_raises(brine_in_memory_keyring):
    provider = BrineProvider(keyring_service="thermocline.test.rev3")
    with pytest.raises(IdentityError) as exc:
        provider.revoke(identity="ghost")
    assert exc.value.code == "IDENTITY_NOT_FOUND"


def test_brine_provider_still_satisfies_protocol(brine_in_memory_keyring):
    """rotate + revoke are part of the IdentityProvider Protocol now."""
    from thermocline import IdentityProvider

    provider = BrineProvider(keyring_service="thermocline.test.proto")
    assert isinstance(provider, IdentityProvider)
    assert provider.scheme is KeyScheme.BRINE
