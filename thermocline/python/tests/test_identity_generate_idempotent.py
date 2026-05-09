"""BL-04 closure: generate() refuses to clobber; rotate() is the explicit
replacement path.
"""
from __future__ import annotations

import pytest

from thermocline import BrineProvider, IdentityError


def test_generate_refuses_to_clobber(brine_in_memory_keyring):
    p = BrineProvider(keyring_service="thermocline.test")
    p.generate(identity="alice")
    with pytest.raises(IdentityError) as exc_info:
        p.generate(identity="alice")
    assert exc_info.value.code == "IDENTITY_ALREADY_EXISTS"


def test_rotate_replaces_seed(brine_in_memory_keyring):
    p = BrineProvider(keyring_service="thermocline.test")
    p.generate(identity="alice")
    pub_old = p.public_key(identity="alice")

    p.rotate(identity="alice")
    pub_new = p.public_key(identity="alice")

    assert pub_old != pub_new


def test_rotate_refuses_when_no_seed(brine_in_memory_keyring):
    p = BrineProvider(keyring_service="thermocline.test")
    with pytest.raises(IdentityError) as exc_info:
        p.rotate(identity="ghost")
    assert exc_info.value.code == "IDENTITY_NOT_FOUND"


def test_rotate_preserves_registered_public_key_for_same_identity(
    brine_in_memory_keyring,
):
    """Public-key entries and seed entries are namespaced differently.
    Rotating the seed does not touch a separately-registered public key
    for the same identity. Depends on the W6 lookup-order invariant pinned
    in test_identity_cross_role.test_pubkey_store_is_consulted_before_seed:
    the public-key store is consulted FIRST, so even after rotate replaces
    the seed, public_key(identity='alice') returns the registered foreign_pub.
    """
    p = BrineProvider(keyring_service="thermocline.test")
    p.generate(identity="alice")

    foreign_pub = b"\xff" * 32
    p.register_public_key(identity="alice", verify_key=foreign_pub)

    p.rotate(identity="alice")

    # The public-key store entry is unchanged -- public_key lookup hits the
    # public-key store FIRST (BL-01 closure ordering), so it returns the
    # registered foreign_pub even after rotate replaces the seed.
    assert p.public_key(identity="alice") == foreign_pub
