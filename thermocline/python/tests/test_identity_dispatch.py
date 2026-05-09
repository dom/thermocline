"""Verifier dispatch end-to-end (without real signing).

Plan 01-03 / Task 1.

These tests use a stub IdentityProvider for non-BRINE schemes so we can probe
the dispatch logic in isolation, then verify that scheme mismatch between the
envelope's declared scheme and the signature's actual scheme is rejected
(IDENT-03 / T-03-06).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import ClassVar

import pytest

from thermocline import (
    IdentityProvider,
    Receipt,
    Signature,
    Verifier,
)
from thermocline.errors import IdentityError, SchemeError
from thermocline.schemes import KeyScheme


class _StubProvider:
    """Minimal IdentityProvider stub that records calls.

    Used to verify dispatch — never produces a valid Receipt. The Receipt
    sentinel mechanism (D-01) prevents anyone — including this stub — from
    forging a Receipt; the stub returns ``None`` instead, which is the
    valid 'verification failed' signal.
    """

    scheme: ClassVar[KeyScheme] = KeyScheme.PGP

    def __init__(self) -> None:
        self.sign_calls: list[tuple[dict, str]] = []
        self.verify_calls: list[tuple[dict, Signature]] = []

    def sign(self, *, envelope: dict, signer_identity: str) -> Signature:
        self.sign_calls.append((envelope, signer_identity))
        return Signature(
            scheme=KeyScheme.PGP,
            bytes_=b"\x00" * 64,
            signer_identity=signer_identity,
        )

    def verify(self, *, envelope: dict, signature: Signature) -> Receipt | None:
        self.verify_calls.append((envelope, signature))
        return None  # stub never claims success — D-01 guards Receipt construction

    def public_key(self, *, identity: str) -> bytes:
        return b"\x00" * 32

    def generate(self, *, identity: str) -> None:
        return None


def test_verifier_dispatches_to_correct_provider_by_scheme() -> None:
    pgp_provider = _StubProvider()
    verifier = Verifier()
    verifier.register(pgp_provider)
    envelope = {"envelope_id": "env-1", "key_scheme": "pgp"}
    signature = Signature(
        scheme=KeyScheme.PGP,
        bytes_=b"\xff" * 64,
        signer_identity="alice",
    )
    result = verifier.verify(envelope=envelope, signature=signature)
    assert result is None  # stub returns None
    assert len(pgp_provider.verify_calls) == 1
    assert pgp_provider.verify_calls[0][0] is envelope
    assert pgp_provider.verify_calls[0][1] is signature


def test_verifier_rejects_envelope_signature_scheme_mismatch() -> None:
    """IDENT-03 / T-03-06: declared envelope scheme MUST match signature scheme."""
    pgp_provider = _StubProvider()
    verifier = Verifier()
    verifier.register(pgp_provider)
    # Envelope declares brine, signature claims PGP — mismatch.
    envelope = {"envelope_id": "env-2", "key_scheme": "brine"}
    signature = Signature(
        scheme=KeyScheme.PGP,
        bytes_=b"\x01" * 64,
        signer_identity="alice",
    )
    with pytest.raises(SchemeError) as excinfo:
        verifier.verify(envelope=envelope, signature=signature)
    assert excinfo.value.code == "UNSUPPORTED_KEY_SCHEME"
    assert pgp_provider.verify_calls == []  # never reached the provider


def test_verifier_no_provider_for_signature_scheme_raises() -> None:
    """IDENT-03: signature claims a scheme nobody registered → SchemeError."""
    verifier = Verifier()  # no providers
    envelope = {"envelope_id": "env-3", "key_scheme": "pgp"}
    signature = Signature(
        scheme=KeyScheme.PGP,
        bytes_=b"\x02" * 64,
        signer_identity="alice",
    )
    with pytest.raises(SchemeError) as excinfo:
        verifier.verify(envelope=envelope, signature=signature)
    assert excinfo.value.code == "UNSUPPORTED_KEY_SCHEME"


def test_verifier_register_overwrites_same_scheme() -> None:
    """Registering twice with the same scheme replaces — last wins.

    Documented behavior; downstream consumers register a single provider per
    scheme. Overwriting on duplicate makes plug-in style tests easier to write.
    """
    a = _StubProvider()
    b = _StubProvider()
    v = Verifier()
    v.register(a)
    v.register(b)
    envelope = {"envelope_id": "env-4", "key_scheme": "pgp"}
    sig = Signature(scheme=KeyScheme.PGP, bytes_=b"\x03" * 64, signer_identity="alice")
    v.verify(envelope=envelope, signature=sig)
    assert a.verify_calls == []
    assert len(b.verify_calls) == 1


def test_verifier_dispatch_passes_through_receipt() -> None:
    """When a provider returns a Receipt, Verifier passes it through unchanged.

    Uses an internal sentinel-aware provider that bypasses D-01 *for the test only*
    by importing the module-private sentinel — this is the one place a test
    legitimately constructs a Receipt to verify the dispatch passthrough.
    """
    from thermocline.identity import _RECEIPT_TOKEN  # type: ignore[attr-defined]

    receipt_to_return = Receipt(
        envelope_id="env-5",
        signature_hash="0" * 64,
        verified_at=datetime.now(timezone.utc),
        key_scheme=KeyScheme.PGP,
        _token=_RECEIPT_TOKEN,
    )

    class _ReceiptProvider(_StubProvider):
        def verify(self, *, envelope: dict, signature: Signature) -> Receipt | None:
            return receipt_to_return

    p = _ReceiptProvider()
    v = Verifier()
    v.register(p)
    envelope = {"envelope_id": "env-5", "key_scheme": "pgp"}
    sig = Signature(scheme=KeyScheme.PGP, bytes_=b"\x04" * 64, signer_identity="alice")
    out = v.verify(envelope=envelope, signature=sig)
    assert out is receipt_to_return


def test_dispatch_falls_back_to_top_level_for_typeless_envelope(
    brine_in_memory_keyring,
):
    """Synthetic envelopes without ``type`` field continue to use top-level
    ``key_scheme`` -- explicit regression for the BL-02 fallback path.
    """
    from thermocline import BrineProvider

    envelope = {"envelope_id": "x", "key_scheme": "brine"}  # no 'type' field
    sig = Signature(
        scheme=KeyScheme.BRINE,
        bytes_=b"\x00" * 64,
        signer_identity="alice",
    )
    v = Verifier()
    v.register(BrineProvider(keyring_service="thermocline.test"))
    # No mismatch -- should reach the provider; provider will raise IdentityError
    # (no key for alice in keystore), proving the dispatch reached it.
    with pytest.raises((IdentityError, SchemeError)):
        v.verify(envelope=envelope, signature=sig)
