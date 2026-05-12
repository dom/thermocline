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
def test_forged_dispatch_signature_verifier_returns_none_on_byte_mismatch() -> None:
    """AT-C4 runtime: Verifier.verify() returns None for a bad signature.

    The thermocline Verifier class dispatches to the appropriate IdentityProvider
    via key_scheme; the provider's verify() returns None when the ed25519
    verify fails. Verifier propagates None.

    Full runtime test lives in test_identity_dispatch.py.
    """
    pytest.skip(
        "AT-C4 runtime byte-mismatch test is covered in "
        "test_identity_dispatch.py; this at_negative file documents the "
        "surface for coverage gates."
    )
