"""SP-3.3 sign_envelope / verify_envelope round-trip and tamper tests.

Covers:
* Finding 2: sign an envelope, verify it, and confirm tampering any field
  makes verify return None. The wire agrees on ``sig: ""`` during
  canonicalization (SP-3.3-01/02).
* Finding 3: an envelope claiming a different ``node_id`` than the signer is
  rejected (AT-C4). The verified identity is recorded on the Receipt.
* Finding 9: ``key_scheme=none`` raises unless the caller opts into the
  unsigned path, in which case an UnsignedAck (not a Receipt) is returned.
"""
from __future__ import annotations

import copy

import pytest

from thermocline import (
    BrineProvider,
    Receipt,
    SchemeError,
    UnsignedAck,
    Verifier,
    sign_envelope,
    verify_envelope,
)
from thermocline.schemes import KeyScheme


def _task(envelope_id: str = "a1b2c3d4-0000-4000-8000-000000000001") -> dict:
    return {
        "thermocline": "0.3.1",
        "type": "task",
        "envelope_id": envelope_id,
        "issued_at": "2026-05-08T00:00:00Z",
        "issuer": "alice-node",
        "channel_id": "chan-pi-forge-local",
        "task": {
            "type": "data.compute",
            "instruction": "Compute pi to 100 digits.",
            "parameters": {"digits": 100},
        },
        "context": [
            {"tier": 2, "role": "task_background", "content": "aGVsbG8="},
        ],
        "dispatch_signature": {
            "key_scheme": "brine",
            "node_id": "alice-node",
            "channel_id": "chan-pi-forge-local",
            "policy_hash": None,
            "shadows_generated": [],
            "timestamp": "2026-05-08T00:00:00Z",
            "sig": "",
        },
    }


def _signer(brine_in_memory_keyring) -> tuple[BrineProvider, Verifier]:
    signer = BrineProvider(keyring_service="thermocline.test.sign")
    signer.generate(identity="alice-node")
    verifier = Verifier()
    verifier.register(signer)
    return signer, verifier


# ---------------------------------------------------------------------------
# SP-3.3 round-trip.


def test_sign_then_verify_round_trips(brine_in_memory_keyring):
    signer, verifier = _signer(brine_in_memory_keyring)
    signed = sign_envelope(_task(), signer, signer_identity="alice-node")
    # sig is now a hex string, not "" and not null.
    payload = signed.model_dump(mode="json")
    assert payload["dispatch_signature"]["sig"]
    assert payload["dispatch_signature"]["sig"] != ""
    receipt = verify_envelope(payload, verifier)
    assert isinstance(receipt, Receipt)
    assert receipt.envelope_id == "a1b2c3d4-0000-4000-8000-000000000001"
    assert receipt.verified_identity == "alice-node"
    assert receipt.key_scheme is KeyScheme.BRINE
    assert receipt.signature_hash_algo == "blake2b-256-v1"


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: p.__setitem__("envelope_id", "tampered-id"),
        lambda p: p["task"]["parameters"].__setitem__("digits", 999),
        lambda p: p["task"].__setitem__("instruction", "Do something else."),
        lambda p: p["context"].append({"tier": 2, "role": "x", "content": "eA=="}),
    ],
)
def test_verify_returns_none_on_tampered_field(brine_in_memory_keyring, mutate):
    signer, verifier = _signer(brine_in_memory_keyring)
    signed = sign_envelope(_task(), signer, signer_identity="alice-node")
    payload = signed.model_dump(mode="json")
    mutate(payload)
    assert verify_envelope(payload, verifier) is None


def test_verify_returns_none_when_sig_bytes_flipped(brine_in_memory_keyring):
    signer, verifier = _signer(brine_in_memory_keyring)
    signed = sign_envelope(_task(), signer, signer_identity="alice-node")
    payload = signed.model_dump(mode="json")
    sig = payload["dispatch_signature"]["sig"]
    flipped = ("f" if sig[0] != "f" else "0") + sig[1:]
    payload["dispatch_signature"]["sig"] = flipped
    assert verify_envelope(payload, verifier) is None


# ---------------------------------------------------------------------------
# Finding 3: node_id binding.


def test_sign_rejects_node_id_mismatch(brine_in_memory_keyring):
    signer, _ = _signer(brine_in_memory_keyring)
    env = _task()
    env["dispatch_signature"]["node_id"] = "someone-else"
    with pytest.raises(Exception) as exc:
        sign_envelope(env, signer, signer_identity="alice-node")
    assert "node_id" in str(exc.value)


def test_verify_rejects_envelope_claiming_different_node_id(brine_in_memory_keyring):
    """A validly-signed envelope whose node_id is swapped after signing fails.

    The signature verifies under alice-node's key, but the envelope claims a
    different node_id; the node_id binding refuses to produce a Receipt.
    """
    signer, verifier = _signer(brine_in_memory_keyring)
    # victim-node exists with its own (different) key.
    signer.generate(identity="victim-node")
    signed = sign_envelope(_task(), signer, signer_identity="alice-node")
    payload = signed.model_dump(mode="json")
    # Swap the declared node_id to impersonate the victim: the alice-node
    # signature does not verify under victim-node's key.
    payload["dispatch_signature"]["node_id"] = "victim-node"
    assert verify_envelope(payload, verifier) is None


def test_brine_verify_binds_node_id_directly(brine_in_memory_keyring):
    """Direct BrineProvider.verify also enforces the node_id binding."""
    from thermocline import Signature

    signer = BrineProvider(keyring_service="thermocline.test.sign")
    signer.generate(identity="alice-node")
    env = _task()
    env["dispatch_signature"]["sig"] = ""
    sig = signer.sign(envelope=env, signer_identity="alice-node")
    # Valid signature, but claim a different node_id in the envelope.
    env["dispatch_signature"]["node_id"] = "impostor"
    bad = Signature(scheme=KeyScheme.BRINE, bytes_=sig.bytes_, signer_identity="alice-node")
    assert signer.verify(envelope=env, signature=bad) is None


# ---------------------------------------------------------------------------
# Finding 9: none scheme.


def test_none_scheme_rejected_by_default(brine_in_memory_keyring):
    _, verifier = _signer(brine_in_memory_keyring)
    env = _task()
    env["dispatch_signature"]["key_scheme"] = "none"
    env["dispatch_signature"]["sig"] = ""
    with pytest.raises(SchemeError) as exc:
        verify_envelope(env, verifier)
    assert exc.value.code == "UNSIGNED_SCHEME_REJECTED"


def test_none_scheme_returns_unsigned_ack_when_opted_in(brine_in_memory_keyring):
    _, verifier = _signer(brine_in_memory_keyring)
    env = _task()
    env["dispatch_signature"]["key_scheme"] = "none"
    env["dispatch_signature"]["sig"] = ""
    ack = verify_envelope(env, verifier, allow_unsigned=True)
    assert isinstance(ack, UnsignedAck)
    assert ack.envelope_id == "a1b2c3d4-0000-4000-8000-000000000001"
    assert not isinstance(ack, Receipt)


def test_sign_envelope_does_not_mutate_input(brine_in_memory_keyring):
    signer, _ = _signer(brine_in_memory_keyring)
    env = _task()
    before = copy.deepcopy(env)
    sign_envelope(env, signer, signer_identity="alice-node")
    assert env == before, "sign_envelope must not mutate the caller's dict"
