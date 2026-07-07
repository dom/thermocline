"""Brine adapter end-to-end PyNaCl Ed25519 round-trip tests (IDENT-02 / IDENT-04).

These tests exercise:

* IDENT-02: real PyNaCl Ed25519 round-trip — generate keypair, sign envelope,
  verify produces a Receipt with expected fields.
* IDENT-04: tampering any byte of the envelope between sign and verify causes
  ``verify`` to return None (no Receipt is produced).
* Signing input goes through ``canonicalize`` (RFC 8785 / JCS), never
  ``json.dumps``.
* IDENT-02: BrineProvider exposes no method whose name leaks key semantics
  (no ``get_signing_key``, no ``export_seed``, etc.).
* IDENT-03 wired end-to-end: registering BrineProvider with Verifier and
  mutating the signature to claim a different scheme triggers SchemeError.

The tests use an in-memory ``keyring`` mock so they run on any host without
needing a configured platform keystore. The IDENT-05 keystore-required guard
is exercised in :mod:`test_identity_keystore_required`.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest

from thermocline import (
    BrineProvider,
    Receipt,
    Signature,
    Verifier,
)
from thermocline.errors import KeystoreUnavailableError, SchemeError
from thermocline.schemes import KeyScheme

# ---------------------------------------------------------------------------
# In-memory keyring fake. Replaces python-keyring's get_password / set_password
# / get_keyring at module-import scope inside ``thermocline.identity``.


@pytest.fixture
def fake_keyring(monkeypatch: pytest.MonkeyPatch) -> dict[tuple[str, str], str]:
    """Patch ``thermocline.identity.keyring`` with an in-memory store.

    Returned dict is the underlying store keyed by ``(service, identity)``;
    tests can introspect it to assert that no key bytes leak elsewhere.
    """
    store: dict[tuple[str, str], str] = {}

    def get_password(service: str, identity: str) -> str | None:
        return store.get((service, identity))

    def set_password(service: str, identity: str, password: str) -> None:
        store[(service, identity)] = password

    def get_keyring() -> Any:
        backend = MagicMock()
        # The BrineProvider startup probe checks ``type(backend).__name__`` —
        # MagicMock instances report 'MagicMock', which does NOT contain
        # 'fail' or 'null', so the adapter accepts it as a working keystore.
        return backend

    monkeypatch.setattr("thermocline.identity.keyring.get_password", get_password)
    monkeypatch.setattr("thermocline.identity.keyring.set_password", set_password)
    monkeypatch.setattr("thermocline.identity.keyring.get_keyring", get_keyring)
    return store


# ---------------------------------------------------------------------------
# IDENT-02: real PyNaCl Ed25519 round-trip.


def _minimal_envelope(envelope_id: str = "env-001") -> dict[str, Any]:
    """Smallest dict the brine adapter is happy to sign + verify.

    BrineProvider treats the envelope as opaque ``dict[str, Any]`` —
    ``canonicalize`` doesn't care which fields are present, only that they're
    stable JSON-serializable values. We use a minimal Task-shaped dict so the
    test reads naturally.
    """
    return {
        "thermocline": "0.3.1",
        "type": "task",
        "envelope_id": envelope_id,
        "issuer": "alice",
        "issued_at": "2026-05-08T00:00:00Z",
        "channel_id": "chan-test",
        "task": {
            "type": "data.compute",
            "instruction": "Compute pi to 100 digits.",
            "parameters": {"digits": 100},
        },
        "context": [],
        # 0.4.0: the scheme lives in the nested signature block (the top-level
        # key_scheme fallback is now typeless-only). node_id matches the signer
        # so the node_id binding on verify is satisfied.
        "dispatch_signature": {"key_scheme": "brine", "node_id": "alice"},
    }


def test_brine_round_trip_produces_receipt(
    fake_keyring: dict[tuple[str, str], str],
) -> None:
    """IDENT-02: generate -> sign -> verify yields a Receipt with expected fields."""
    provider = BrineProvider(keyring_service="thermocline.test.brine")
    provider.generate(identity="alice")

    envelope = _minimal_envelope()
    sig = provider.sign(envelope=envelope, signer_identity="alice")

    assert isinstance(sig, Signature)
    assert sig.scheme is KeyScheme.BRINE
    assert sig.signer_identity == "alice"
    assert isinstance(sig.bytes_, bytes)
    assert len(sig.bytes_) == 64  # Ed25519 signature length

    receipt = provider.verify(envelope=envelope, signature=sig)
    assert receipt is not None
    assert isinstance(receipt, Receipt)
    assert receipt.envelope_id == "env-001"
    assert receipt.key_scheme is KeyScheme.BRINE
    assert (datetime.now(timezone.utc) - receipt.verified_at).total_seconds() < 5
    assert len(receipt.signature_hash) == 64  # blake2b(digest_size=32) hex


# ---------------------------------------------------------------------------
# IDENT-04 / Pitfall 5: tamper detection — no Receipt on signature failure.


def test_brine_tamper_detection_returns_none(
    fake_keyring: dict[tuple[str, str], str],
) -> None:
    """Mutating any byte of the envelope between sign and verify yields no Receipt."""
    provider = BrineProvider(keyring_service="thermocline.test.brine")
    provider.generate(identity="alice")

    envelope = _minimal_envelope("env-002")
    sig = provider.sign(envelope=envelope, signer_identity="alice")

    tampered = {**envelope, "envelope_id": "env-002-tampered"}
    receipt = provider.verify(envelope=tampered, signature=sig)
    assert receipt is None, (
        "tamper between sign and verify MUST produce no Receipt — Pitfall 5 / IDENT-04"
    )


def test_brine_tamper_in_nested_field_returns_none(
    fake_keyring: dict[tuple[str, str], str],
) -> None:
    """Nested mutation also surfaces as tamper — canonicalize sees through ``dict[str, Any]``."""
    provider = BrineProvider(keyring_service="thermocline.test.brine")
    provider.generate(identity="alice")

    envelope = _minimal_envelope("env-003")
    sig = provider.sign(envelope=envelope, signer_identity="alice")

    tampered = {
        **envelope,
        "task": {**envelope["task"], "parameters": {"digits": 999}},
    }
    receipt = provider.verify(envelope=tampered, signature=sig)
    assert receipt is None


# ---------------------------------------------------------------------------
# Pitfall 11: signing input goes through canonicalize, not json.dumps.


def test_brine_signs_canonical_json_input(
    fake_keyring: dict[tuple[str, str], str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``BrineProvider.sign`` MUST call ``canonicalize`` on the envelope before signing."""
    provider = BrineProvider(keyring_service="thermocline.test.brine")
    provider.generate(identity="alice")

    real_canonicalize = __import__(
        "thermocline.canonical", fromlist=["canonicalize"]
    ).canonicalize
    seen: list[Any] = []

    def spy(payload: Any) -> bytes:
        seen.append(payload)
        return real_canonicalize(payload)

    monkeypatch.setattr("thermocline.identity.canonicalize", spy)

    envelope = _minimal_envelope("env-004")
    provider.sign(envelope=envelope, signer_identity="alice")
    assert envelope in seen, "BrineProvider.sign did not call canonicalize"


# ---------------------------------------------------------------------------
# IDENT-02 / Pitfall 9: no key-leaking method names on BrineProvider.


def test_brine_provider_exposes_no_key_leaking_methods() -> None:
    """Reflection check: no public method whose name suggests private-key access."""
    forbidden = ("private", "secret", "seed", "signing_key")
    public_methods = [m for m in dir(BrineProvider) if not m.startswith("_")]
    for method in public_methods:
        for token in forbidden:
            assert token not in method.lower(), (
                f"BrineProvider exposes a method whose name leaks key semantics: "
                f"{method!r} contains {token!r}"
            )


# ---------------------------------------------------------------------------
# Signature redaction in repr (Pitfall 4 — defense in depth).


def test_brine_signature_repr_redacts_bytes(
    fake_keyring: dict[tuple[str, str], str],
) -> None:
    provider = BrineProvider(keyring_service="thermocline.test.brine")
    provider.generate(identity="alice")
    envelope = _minimal_envelope("env-005")
    sig = provider.sign(envelope=envelope, signer_identity="alice")

    text = repr(sig)
    assert sig.bytes_.hex() not in text, "raw signature bytes leaked in repr"
    assert "redacted" in text.lower()


# ---------------------------------------------------------------------------
# IDENT-03 wired end-to-end via Verifier.


def test_verifier_dispatch_round_trips_brine_signature(
    fake_keyring: dict[tuple[str, str], str],
) -> None:
    """Verifier registered with BrineProvider produces a Receipt for a fresh signature."""
    provider = BrineProvider(keyring_service="thermocline.test.brine")
    provider.generate(identity="alice")
    verifier = Verifier()
    verifier.register(provider)

    envelope = _minimal_envelope("env-006")
    sig = provider.sign(envelope=envelope, signer_identity="alice")
    receipt = verifier.verify(envelope=envelope, signature=sig)
    assert receipt is not None
    assert receipt.envelope_id == "env-006"


def test_verifier_rejects_signature_scheme_mismatch_after_real_signing(
    fake_keyring: dict[tuple[str, str], str],
) -> None:
    """Mutate a real brine Signature to claim PGP — Verifier MUST raise SchemeError."""
    provider = BrineProvider(keyring_service="thermocline.test.brine")
    provider.generate(identity="alice")
    verifier = Verifier()
    verifier.register(provider)

    envelope = _minimal_envelope("env-007")
    sig = provider.sign(envelope=envelope, signer_identity="alice")
    forged = Signature(
        scheme=KeyScheme.PGP, bytes_=sig.bytes_, signer_identity="alice"
    )
    with pytest.raises(SchemeError) as excinfo:
        verifier.verify(envelope=envelope, signature=forged)
    assert excinfo.value.code == "UNSUPPORTED_KEY_SCHEME"


# ---------------------------------------------------------------------------
# Smoke: BrineProvider startup raises on a manifestly broken keyring before
# the IDENT-05 dedicated tests run. (Symmetric mirror to confirm the fake
# keyring is the right shape — if it weren't, BrineProvider's __init__ would
# raise KeystoreUnavailableError and the round-trip tests above would all skip.)


def test_brine_starts_with_working_fake_keyring(
    fake_keyring: dict[tuple[str, str], str],
) -> None:
    """The in-memory keyring fake satisfies BrineProvider's startup probe."""
    try:
        BrineProvider(keyring_service="thermocline.test.brine")
    except KeystoreUnavailableError as exc:  # pragma: no cover - signals fixture drift
        pytest.fail(f"in-memory keyring fake should satisfy startup probe; got {exc!r}")
