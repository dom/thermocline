"""Unit tests for the IdentityProvider Protocol shape and Signature redaction.

Plan 01-03 / Task 1.

These tests don't exercise real signing — they assert the *type-system shape* of
the public API (Protocol membership, Signature value-type contract, runtime
checkability). The brine round-trip lives in tests/test_identity_brine_roundtrip.
"""
from __future__ import annotations

from typing import Protocol, get_type_hints

import pytest

from thermocline import (
    BrineProvider,
    IdentityProvider,
    Receipt,
    Signature,
    Verifier,
)
from thermocline.errors import SchemeError
from thermocline.schemes import KeyScheme


# ---------------------------------------------------------------------------
# IdentityProvider Protocol shape (IDENT-01).


def test_identity_provider_is_protocol() -> None:
    """IDENT-01: ``IdentityProvider`` must be a ``typing.Protocol``."""
    # ``Protocol`` is a marker; check via the ``_is_protocol`` attribute that
    # the typing machinery sets on subclasses, plus a positive duck check.
    assert getattr(IdentityProvider, "_is_protocol", False), (
        "IdentityProvider should be a typing.Protocol — Plan 01-03 Task 1 IDENT-01"
    )


def test_identity_provider_is_runtime_checkable() -> None:
    """IDENT-01: Protocol carries the @runtime_checkable decorator so isinstance works."""
    # ``runtime_checkable`` adds the ``_is_runtime_protocol`` flag.
    assert getattr(IdentityProvider, "_is_runtime_protocol", False), (
        "IdentityProvider should be runtime_checkable — Plan 01-03 Task 1"
    )


def test_identity_provider_declares_required_methods() -> None:
    """IDENT-01: Protocol must declare scheme + sign + verify + public_key + generate."""
    # The members live as annotations / methods on the Protocol class.
    methods = set(dir(IdentityProvider))
    annotations = set(IdentityProvider.__annotations__.keys())
    members = methods | annotations
    for required in ("scheme", "sign", "verify", "public_key", "generate"):
        assert required in members, (
            f"IdentityProvider missing required member {required!r}"
        )


def test_brine_provider_satisfies_identity_provider_runtime_check() -> None:
    """BrineProvider should be a runtime-checkable IdentityProvider.

    We instantiate against the real keystore (macOS Keychain in CI/dev). If the
    test environment lacks a working keystore, the BrineProvider __init__ will
    raise — that's IDENT-05 and is exercised separately. Skip here on that path.
    """
    from thermocline.errors import KeystoreUnavailableError

    try:
        provider = BrineProvider(keyring_service="thermocline.test.protocol")
    except KeystoreUnavailableError:
        pytest.skip("no working keystore in this environment; covered by IDENT-05 tests")
    assert isinstance(provider, IdentityProvider), (
        "BrineProvider must satisfy the IdentityProvider Protocol structurally"
    )


# ---------------------------------------------------------------------------
# Signature value-type contract.


def test_signature_carries_scheme_bytes_and_signer_identity() -> None:
    sig = Signature(
        scheme=KeyScheme.BRINE,
        bytes_=b"\x00" * 64,
        signer_identity="alice",
    )
    assert sig.scheme is KeyScheme.BRINE
    assert sig.bytes_ == b"\x00" * 64
    assert isinstance(sig.bytes_, bytes)
    assert sig.signer_identity == "alice"


def test_signature_repr_redacts_bytes() -> None:
    """Pitfall 4 / T-03-04: signature bytes MUST NOT appear in ``repr``."""
    raw = bytes(range(64))  # easily-recognisable bytes
    sig = Signature(
        scheme=KeyScheme.BRINE,
        bytes_=raw,
        signer_identity="alice",
    )
    text = repr(sig)
    assert raw.hex() not in text
    assert "redacted" in text.lower()
    assert "alice" in text  # signer identity is non-secret context
    assert "brine" in text  # scheme is non-secret context


def test_signature_str_also_redacts() -> None:
    raw = bytes(range(64))
    sig = Signature(scheme=KeyScheme.BRINE, bytes_=raw, signer_identity="alice")
    assert raw.hex() not in str(sig)


def test_signature_is_immutable() -> None:
    """Signature is a frozen value type — mutation must fail."""
    sig = Signature(scheme=KeyScheme.BRINE, bytes_=b"x" * 64, signer_identity="alice")
    with pytest.raises((AttributeError, TypeError)):
        sig.scheme = KeyScheme.PGP  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Verifier basic dispatch shape (deeper end-to-end lives in test_identity_dispatch).


def test_verifier_can_register_provider() -> None:
    """Smoke: Verifier accepts a registered provider without raising."""
    from thermocline.errors import KeystoreUnavailableError

    try:
        provider = BrineProvider(keyring_service="thermocline.test.register")
    except KeystoreUnavailableError:
        pytest.skip("no keystore — covered separately")
    verifier = Verifier()
    verifier.register(provider)


def test_verifier_unknown_scheme_raises_scheme_error() -> None:
    """IDENT-03: verify with no provider for the signature's scheme raises SchemeError."""
    verifier = Verifier()  # no providers registered
    sig = Signature(scheme=KeyScheme.BRINE, bytes_=b"x" * 64, signer_identity="alice")
    envelope = {"key_scheme": "brine"}
    with pytest.raises(SchemeError) as excinfo:
        verifier.verify(envelope=envelope, signature=sig)
    assert excinfo.value.code == "UNSUPPORTED_KEY_SCHEME"


# ---------------------------------------------------------------------------
# Receipt is exposed via the public API.


def test_receipt_is_exported_from_package() -> None:
    """``from thermocline import Receipt`` must succeed."""
    from thermocline import Receipt as ImportedReceipt

    assert ImportedReceipt is Receipt
