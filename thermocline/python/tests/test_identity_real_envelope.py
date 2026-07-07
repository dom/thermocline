"""Behavioral regression tests: Verifier.verify must read ``key_scheme`` from
the canonical nested location for real envelope shapes.

These tests load real conformance fixtures from disk to close the synthetic
loophole where flat-dict envelopes with top-level ``key_scheme`` masked the
production lookup path through ``dispatch_signature`` / ``receipt_signature``.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from thermocline import (
    BrineProvider,
    KeyScheme,
    Receipt,
    SchemeError,
    Signature,
    Verifier,
)
from thermocline.identity import Verifier as _Verifier  # for _declared_scheme tests

# ---------------------------------------------------------------------------
# Helpers -- the test file lives at thermocline/python/tests/, so parents[3]
# is the repo root (thermocline/). Run from anywhere; no cwd assumptions.

REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_fixture(rel_path: str) -> dict:
    """Load a JSON fixture under ``thermocline/conformance/`` from disk."""
    path = REPO_ROOT / rel_path
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# ``_declared_scheme`` is exhaustive over all five envelope types.


def test_declared_scheme_task():
    env = {"type": "task", "dispatch_signature": {"key_scheme": "brine"}}
    assert _Verifier._declared_scheme(env) == "brine"


def test_declared_scheme_job():
    env = {"type": "job", "dispatch_signature": {"key_scheme": "brine"}}
    assert _Verifier._declared_scheme(env) == "brine"


def test_declared_scheme_task_result():
    env = {"type": "task_result", "receipt_signature": {"key_scheme": "brine"}}
    assert _Verifier._declared_scheme(env) == "brine"


def test_declared_scheme_job_result():
    env = {"type": "job_result", "receipt_signature": {"key_scheme": "brine"}}
    assert _Verifier._declared_scheme(env) == "brine"


def test_declared_scheme_task_error_returns_none():
    """Error envelopes are unsigned by spec; ``_declared_scheme`` returns None."""
    assert _Verifier._declared_scheme({"type": "task_error"}) is None


def test_declared_scheme_job_error_returns_none():
    """Error envelopes are unsigned by spec; ``_declared_scheme`` returns None."""
    assert _Verifier._declared_scheme({"type": "job_error"}) is None


# ---------------------------------------------------------------------------
# Fallback for typed envelopes without a populated nested block.


def test_declared_scheme_task_with_top_level_keyscheme_no_dispatch_signature():
    """0.4.0 (Finding 6): a typed envelope with NO dispatch_signature block
    is malformed for verification. The non-spec top-level ``key_scheme``
    fallback no longer rescues it; ``_declared_scheme`` raises SchemeError.
    """
    env = {"type": "task", "key_scheme": "brine"}  # NO dispatch_signature
    with pytest.raises(SchemeError) as exc:
        _Verifier._declared_scheme(env)
    assert exc.value.code == "UNSUPPORTED_KEY_SCHEME"


def test_declared_scheme_task_with_empty_dispatch_signature_block():
    """0.4.0 (Finding 6): an empty nested block has no key_scheme, so a typed
    envelope still raises SchemeError rather than reading a top-level fallback.
    """
    env = {"type": "task", "dispatch_signature": {}, "key_scheme": "brine"}
    with pytest.raises(SchemeError):
        _Verifier._declared_scheme(env)


def test_declared_scheme_typeless_envelope_uses_top_level():
    """No type field -> top-level fallback (synthetic flat-dict test path)."""
    env = {"envelope_id": "x", "key_scheme": "brine"}
    assert _Verifier._declared_scheme(env) == "brine"


# ---------------------------------------------------------------------------
# Real-envelope round-trip.


def test_verify_real_task_envelope_through_nested_key_scheme(brine_in_memory_keyring):
    """Verifier.verify reads ``dispatch_signature.key_scheme`` for ``type='task'``."""
    envelope = _load_fixture("thermocline/conformance/valid/task-pi-100-digits.json")
    # Fixture ships with key_scheme='none' -- overwrite to brine for the round-trip.
    envelope["dispatch_signature"]["key_scheme"] = "brine"
    # 0.4.0 node_id binding: sign as the identity the envelope declares.
    node_id = envelope["dispatch_signature"]["node_id"]

    signer = BrineProvider(keyring_service="thermocline.test")
    signer.generate(identity=node_id)
    signature = signer.sign(envelope=envelope, signer_identity=node_id)

    verifier_role = BrineProvider(keyring_service="thermocline.test.verifier")
    verifier_role.register_public_key(
        identity=node_id,
        verify_key=signer.public_key(identity=node_id),
    )

    v = Verifier()
    v.register(verifier_role)

    receipt = v.verify(envelope=envelope, signature=signature)
    assert isinstance(receipt, Receipt)
    assert receipt.envelope_id == "a1b2c3d4-0000-4000-8000-000000000001"
    assert receipt.key_scheme is KeyScheme.BRINE


def test_verify_real_task_result_envelope_through_nested_key_scheme(
    brine_in_memory_keyring,
):
    """Verifier.verify reads ``receipt_signature.key_scheme`` for ``type='task_result'``."""
    envelope = _load_fixture(
        "thermocline/conformance/valid/task-result-pi-100-digits.json"
    )
    envelope["receipt_signature"]["key_scheme"] = "brine"
    node_id = envelope["receipt_signature"]["node_id"]

    signer = BrineProvider(keyring_service="thermocline.test")
    signer.generate(identity=node_id)
    signature = signer.sign(envelope=envelope, signer_identity=node_id)

    verifier_role = BrineProvider(keyring_service="thermocline.test.verifier")
    verifier_role.register_public_key(
        identity=node_id,
        verify_key=signer.public_key(identity=node_id),
    )

    v = Verifier()
    v.register(verifier_role)

    receipt = v.verify(envelope=envelope, signature=signature)
    assert isinstance(receipt, Receipt)
    assert receipt.key_scheme is KeyScheme.BRINE


def test_at_c4_fixture_raises_scheme_error_through_verifier(brine_in_memory_keyring):
    """AT-C4 wired BEHAVIORALLY. The fixture's
    ``dispatch_signature.key_scheme`` is 'brine' and its
    ``_signature_actual_scheme`` metadata field is 'pgp' (documented
    mismatch). Construct a Signature with ``scheme=KeyScheme.PGP`` so
    declared='brine' mismatches actual='pgp' -- that is exactly what AT-C4
    detects.

    (Using ``KeyScheme.BRINE`` here would NOT trigger the mismatch path; the
    test would pass for the wrong reason or raise IdentityError instead of
    SchemeError.)
    """
    envelope = _load_fixture(
        "thermocline/conformance/invalid/AT-C4-key-scheme-mismatch.json"
    )
    assert envelope["dispatch_signature"]["key_scheme"] == "brine"
    assert envelope.get("_signature_actual_scheme") == "pgp"

    bogus_sig = Signature(
        scheme=KeyScheme.PGP,            # PGP -- mismatches the fixture's 'brine'
        bytes_=b"\x00" * 64,
        signer_identity="attacker",
    )

    v = Verifier()
    v.register(BrineProvider(keyring_service="thermocline.test"))

    with pytest.raises(SchemeError) as exc_info:
        v.verify(envelope=envelope, signature=bogus_sig)
    assert exc_info.value.code == "UNSUPPORTED_KEY_SCHEME"


def test_synthetic_flat_dict_envelope_still_works(brine_in_memory_keyring):
    """The top-level fallback is preserved for tests that build minimal flat dicts."""
    bogus_sig = Signature(
        scheme=KeyScheme.BRINE,
        bytes_=b"\x00" * 64,
        signer_identity="alice",
    )

    v = Verifier()
    v.register(BrineProvider(keyring_service="thermocline.test"))

    # Mismatch detection still works: change the top-level key_scheme.
    mismatched = {"envelope_id": "test", "key_scheme": "pgp"}
    with pytest.raises(SchemeError):
        v.verify(envelope=mismatched, signature=bogus_sig)
