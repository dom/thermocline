"""AT-C1: Envelope tampering in transit — any field modification invalidates signature.

Failure mode (from thermocline/README.md §"Attack Surfaces"):
    An adversary modifies any field of an in-transit envelope; the dispatch
    signature MUST cover the canonical bytes, so any mutation invalidates the
    signature. The verifier MUST refuse to construct a Receipt.

Mitigation: thermocline.canonical.canonicalize over the envelope; ed25519
signature; Verifier.verify returns None on byte-level mismatch.
"""
# AT-SURFACE: AT-C1
from __future__ import annotations

import pytest

from thermocline.canonical import canonicalize


@pytest.mark.at_surface("AT-C1")
def test_envelope_tampering_changes_canonical_bytes() -> None:
    """AT-C1: any field mutation produces different canonical bytes -> signature invalidated.

    The signature invariant: dispatch_signature is computed over canonicalize(envelope - sig).
    If any field changes, canonicalize() output differs by construction (Property 2 of
    test_canonical_properties.py is the formal proof). This test is the AT-C1 surface
    wire-in: it documents that the property-test invariant is the mitigation.
    """
    envelope = {
        "thermocline": "0.3.1",
        "type": "task",
        "envelope_id": "00000000-0000-0000-0000-00000000c100",
        "issuer": "alice-node",
        "channel_id": "chan-pi-local",
        "task": {"type": "data.compute", "parameters": {"digits": 10}},
        "context": [],
    }
    original_bytes = canonicalize(envelope)
    tampered = dict(envelope)
    tampered["envelope_id"] = "00000000-0000-0000-0000-00000000c1ff"
    tampered_bytes = canonicalize(tampered)
    assert tampered_bytes != original_bytes, (
        "AT-C1: tampering envelope_id MUST change canonical bytes; "
        "signature verifier relies on this to detect tampering"
    )
