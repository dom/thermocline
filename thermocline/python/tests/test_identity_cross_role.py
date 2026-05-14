"""Cross-role verification must work without the verifier holding the
signer's private seed.

These tests prove that:

* A verifier-role BrineProvider whose keystore contains ONLY a registered
  public key for ``alice`` can verify a Signature produced by a different
  BrineProvider whose keystore contains the SEED for ``alice``.
* The signer-role provider does not need to be aware that the verifier role
  exists; only the public key crosses.
* Single-node self-signing flows (the original behaviour) continue to work.
* Lookup order: when a node holds BOTH a registered public key AND a seed
  for the same identity, the registered public key is returned
  (verify-role takes precedence).
"""
from __future__ import annotations

import keyring as _kr
import pytest

from thermocline import (
    BrineProvider,
    IdentityError,
    KeyScheme,
    Receipt,
    Verifier,
)


def test_verifier_only_role_verifies_foreign_signature(brine_in_memory_keyring):
    signer = BrineProvider(keyring_service="thermocline.test.signer")
    signer.generate(identity="alice")

    pub = signer.public_key(identity="alice")
    assert len(pub) == 32

    verifier_role = BrineProvider(keyring_service="thermocline.test.verifier")
    verifier_role.register_public_key(identity="alice", verify_key=pub)

    # Sanity: verifier_role does NOT have a seed for alice.
    assert _kr.get_password("thermocline.test.verifier", "alice") is None

    # Dual-form key_scheme (top-level AND nested under dispatch_signature):
    # the _declared_scheme helper reads the nested location first and the
    # top-level field is a tolerated fallback. The same envelope passes
    # under both code paths.
    envelope = {
        "type": "task",
        "envelope_id": "test-1",
        "key_scheme": "brine",
        "dispatch_signature": {"key_scheme": "brine"},
    }
    sig = signer.sign(envelope=envelope, signer_identity="alice")

    v = Verifier()
    v.register(verifier_role)
    receipt = v.verify(envelope=envelope, signature=sig)
    assert isinstance(receipt, Receipt)
    assert receipt.key_scheme is KeyScheme.BRINE


def test_public_key_lookup_falls_back_to_seed_when_no_pubkey_registered(
    brine_in_memory_keyring,
):
    """Single-node self-signing: provider has only a seed, public_key() must
    still work (backward compat -- original behaviour preserved).
    """
    p = BrineProvider(keyring_service="thermocline.test")
    p.generate(identity="bob")
    pub = p.public_key(identity="bob")
    assert len(pub) == 32  # derived from the seed


def test_pubkey_store_is_consulted_before_seed(brine_in_memory_keyring):
    """When a node holds BOTH a registered foreign public key AND a seed for
    the same identity, ``public_key`` returns the registered foreign public
    key (NOT the seed-derived verify key).

    This pins the load-bearing lookup-order invariant --
    ``test_rotate_preserves_registered_public_key_for_same_identity`` in
    ``test_identity_generate_idempotent.py`` depends on this ordering.
    """
    p = BrineProvider(keyring_service="thermocline.test")

    foreign_pub = b"\xee" * 32
    p.register_public_key(identity="alice", verify_key=foreign_pub)

    # Now also generate a seed for the same identity.
    p.generate(identity="alice")

    # The registered foreign public key takes precedence over the seed-derived
    # verify key.
    returned = p.public_key(identity="alice")
    assert returned == foreign_pub


def test_public_key_raises_when_neither_pubkey_nor_seed_present(
    brine_in_memory_keyring,
):
    p = BrineProvider(keyring_service="thermocline.test")
    with pytest.raises(IdentityError) as exc_info:
        p.public_key(identity="ghost")
    assert exc_info.value.code == "IDENTITY_NOT_FOUND"


def test_register_public_key_rejects_wrong_length(brine_in_memory_keyring):
    p = BrineProvider(keyring_service="thermocline.test")
    with pytest.raises(IdentityError):
        p.register_public_key(identity="alice", verify_key=b"\x00" * 31)
    with pytest.raises(IdentityError):
        p.register_public_key(identity="alice", verify_key=b"\x00" * 33)


def test_register_public_key_overwrites_idempotently(brine_in_memory_keyring):
    """Re-registering the same (identity, verify_key) is a no-op; re-registering
    with a different verify_key overwrites -- the documented foreign-key-rotation
    path. No warning is emitted (rotation of foreign keys is routine).
    """
    p = BrineProvider(keyring_service="thermocline.test.verifier")
    pub_a = b"\x01" * 32
    pub_b = b"\x02" * 32
    p.register_public_key(identity="alice", verify_key=pub_a)
    p.register_public_key(identity="alice", verify_key=pub_a)  # idempotent
    p.register_public_key(identity="alice", verify_key=pub_b)  # rotated

    # Verify the latest registration is what's stored.
    assert p.public_key(identity="alice") == pub_b
