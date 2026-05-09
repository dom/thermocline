"""Identity primitives for the Thermocline suite.

This module is the cryptographic boundary between callers (envelope authors,
forge handlers, the dispatch coordinator) and the platform secure keystore.
It ships:

* :class:`Signature` — opaque value type wrapping raw signature bytes.
  ``__repr__`` is redacted so signatures cannot leak via accidental ``print``
  or ``logger.info`` calls (Pitfall 4 / T-03-04).
* :class:`Receipt` — verification witness. Constructible **only** via
  :meth:`IdentityProvider.verify` returning success — the constructor takes a
  module-private sentinel ``_token`` parameter that has no default and whose
  type (:class:`_ReceiptConstructorToken`) is module-private. Direct
  construction raises ``TypeError`` at runtime AND fails ``mypy --strict``
  (D-01 / IDENT-04 / T-03-01 / T-03-10).
* :class:`IdentityProvider` — runtime-checkable :class:`typing.Protocol` with
  the locked method signatures every adapter must implement (IDENT-01).
* :class:`Verifier` — multi-scheme dispatcher. Refuses signatures whose
  declared scheme does not match the envelope's declared ``key_scheme``
  (IDENT-03 / T-03-06).
* :class:`BrineProvider` — Ed25519 reference adapter (PyNaCl + ``python-keyring``).
  Refuses to start if the platform keystore is unavailable (IDENT-05); never
  returns key bytes from any method (IDENT-02 / Pitfall 9).

Reading order matches the trust model: scheme types -> Receipt mechanism ->
Protocol -> Verifier -> reference adapter.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, ClassVar, Final, Protocol, runtime_checkable

import keyring
import nacl.exceptions
import nacl.signing
from keyring.backends import fail as _fail_backend
from keyring.backends import null as _null_backend
from keyring.errors import NoKeyringError

from .canonical import canonicalize
from .errors import IdentityError, KeystoreUnavailableError, SchemeError
from .schemes import KeyScheme

__all__ = [
    "Signature",
    "Receipt",
    "IdentityProvider",
    "Verifier",
    "BrineProvider",
]


# ---------------------------------------------------------------------------
# Signature value type.


@dataclass(frozen=True, slots=True)
class Signature:
    """Opaque signature value returned by :meth:`IdentityProvider.sign`.

    Attributes
    ----------
    scheme
        Key scheme that produced the signature. Verifiers dispatch on this.
    bytes_
        Raw signature bytes (e.g., 64 bytes for Ed25519). Redacted in
        ``__repr__`` and ``__str__`` so accidental ``logger.info(sig)`` cannot
        leak the bytes — Pitfall 4 / T-03-04.
    signer_identity
        Stable identity string for whoever produced the signature; the
        verifier uses this to look up the public key.
    """

    scheme: KeyScheme
    bytes_: bytes
    signer_identity: str

    def __repr__(self) -> str:
        return (
            f"<Signature scheme={self.scheme.value} signer={self.signer_identity!r} "
            f"bytes=<redacted len={len(self.bytes_)}>>"
        )

    def __str__(self) -> str:
        return self.__repr__()


# ---------------------------------------------------------------------------
# Receipt — D-01 sentinel mechanism.


class _ReceiptConstructorToken:
    """Module-private witness that Receipt construction came from a verified path.

    The class is defined in this module and **never exported**. Any caller that
    wants to construct a :class:`Receipt` must pass an instance of this class —
    but the class is not in the public namespace, so external code cannot
    legitimately reference it. ``mypy --strict`` rejects external Receipt
    construction because the only valid type for ``_token`` is this class.
    """

    __slots__ = ()


_RECEIPT_TOKEN: Final[_ReceiptConstructorToken] = _ReceiptConstructorToken()


@dataclass(frozen=True, slots=True)
class Receipt:
    """Verification witness. Constructible only via the verify path.

    See module docstring for the D-01 mechanism. The constructor's ``_token``
    parameter is required (no default) and typed against the module-private
    sentinel class — both gates fire:

    * Runtime: a non-:data:`_RECEIPT_TOKEN` value raises ``TypeError``.
    * Static: ``mypy --strict`` rejects calls that omit ``_token`` because the
      parameter has no default and the class is module-private to callers
      outside ``thermocline.identity``.
    """

    envelope_id: str
    signature_hash: str
    verified_at: datetime
    key_scheme: KeyScheme

    def __init__(
        self,
        *,
        envelope_id: str,
        signature_hash: str,
        verified_at: datetime,
        key_scheme: KeyScheme,
        _token: _ReceiptConstructorToken,
    ) -> None:
        if _token is not _RECEIPT_TOKEN:
            raise TypeError(
                "Receipt is constructible only by IdentityProvider.verify() "
                "returning success. Direct construction is forbidden by design "
                "(D-01) — see "
                ".planning/phases/01-thermocline-py-foundations/01-CONTEXT.md."
            )
        # ``frozen=True`` forbids attribute assignment after __init__; this is
        # the one acceptable use of object.__setattr__ in this codebase. The
        # frozen guarantee is what makes Receipt safe to pass through the audit
        # log without copy-on-write concerns.
        object.__setattr__(self, "envelope_id", envelope_id)
        object.__setattr__(self, "signature_hash", signature_hash)
        object.__setattr__(self, "verified_at", verified_at)
        object.__setattr__(self, "key_scheme", key_scheme)


# ---------------------------------------------------------------------------
# IdentityProvider Protocol (IDENT-01).


@runtime_checkable
class IdentityProvider(Protocol):
    """The locked method signatures every key-scheme adapter must implement.

    Implementations are duck-typed: a class with the right method shapes
    structurally satisfies the Protocol. ``@runtime_checkable`` enables
    ``isinstance(obj, IdentityProvider)`` checks at runtime.
    """

    scheme: ClassVar[KeyScheme]

    def sign(self, *, envelope: dict[str, Any], signer_identity: str) -> Signature:
        ...

    def verify(
        self, *, envelope: dict[str, Any], signature: Signature
    ) -> Receipt | None:
        ...

    def public_key(self, *, identity: str) -> bytes:
        ...

    def generate(self, *, identity: str) -> None:
        ...


# ---------------------------------------------------------------------------
# Verifier — multi-scheme dispatch (IDENT-03).


class Verifier:
    """Multi-scheme verifier. Dispatches on the signature's declared scheme.

    The verifier rejects two threat vectors before ever touching a provider:

    1. **Envelope/signature scheme mismatch** (T-03-06): the envelope declares
       ``key_scheme=brine`` but the signature claims ``scheme=pgp``. Silent
       coercion would let a forger swap signatures across schemes; we raise
       :class:`SchemeError` instead.

    2. **No registered provider for the signature's scheme** (IDENT-03): the
       signature claims a scheme nobody is configured to verify. Rejecting
       early prevents any default-accept failure mode.
    """

    def __init__(self) -> None:
        self._providers: dict[KeyScheme, IdentityProvider] = {}

    def register(self, provider: IdentityProvider) -> None:
        """Register a provider for its declared scheme. Re-register replaces."""
        self._providers[provider.scheme] = provider

    def verify(
        self, *, envelope: dict[str, Any], signature: Signature
    ) -> Receipt | None:
        """Verify ``signature`` against ``envelope`` via the appropriate provider.

        BL-02 closure: ``key_scheme`` lookup is canonical-location-aware via
        :meth:`_declared_scheme` -- routes by ``envelope.get('type')`` to the
        nested ``dispatch_signature`` / ``receipt_signature`` block, with a
        documented top-level fallback for synthetic flat-dict tests and for
        typed envelopes whose nested block is absent or empty.

        Raises
        ------
        SchemeError
            If the envelope's declared ``key_scheme`` does not match the
            signature's actual scheme, or if no provider is registered for
            the signature's scheme.
        """
        declared = self._declared_scheme(envelope)
        if declared != signature.scheme.value:
            raise SchemeError(
                f"declared key scheme {declared!r} does not match signature scheme "
                f"{signature.scheme.value!r}",
                code="UNSUPPORTED_KEY_SCHEME",
            )
        provider = self._providers.get(signature.scheme)
        if provider is None:
            raise SchemeError(
                f"no IdentityProvider registered for scheme {signature.scheme.value!r}",
                code="UNSUPPORTED_KEY_SCHEME",
            )
        return provider.verify(envelope=envelope, signature=signature)

    @staticmethod
    def _declared_scheme(envelope: dict[str, Any]) -> str | None:
        """Read the declared ``key_scheme`` from the canonical nested location.

        Lookup table by envelope ``type`` (BL-02 closure -- exhaustive over
        the five envelope types defined in :mod:`thermocline.envelope`):

        * ``task``, ``job`` -> ``envelope['dispatch_signature']['key_scheme']``
        * ``task_result``, ``job_result`` ->
          ``envelope['receipt_signature']['key_scheme']``
        * ``task_error``, ``job_error`` (the two ``ErrorEnvelope.type``
          discriminator values per ``envelope.py``) -> ``None``. Error
          envelopes are unsigned by spec; the verifier should never be
          called on one. Returning ``None`` surfaces the misuse as
          :class:`SchemeError` (because ``None != signature.scheme.value``).

        Fallback rule: when the envelope has NO ``type`` field, OR the
        canonical nested signature block is absent / empty / has no
        ``key_scheme`` key, the helper falls back to top-level
        ``envelope.get('key_scheme')``. This is the only sanctioned
        deviation from the spec's nested layout -- preserved so existing
        tests whose envelopes carry ``type='task'`` + top-level
        ``key_scheme`` but NO ``dispatch_signature`` block continue to pass
        (e.g., ``test_identity_brine_roundtrip._minimal_envelope``).
        """
        env_type = envelope.get("type")
        if env_type in ("task", "job"):
            block = envelope.get("dispatch_signature")
            if isinstance(block, dict):
                scheme = block.get("key_scheme")
                if scheme is not None:
                    return str(scheme)
            # Nested block is absent / empty / lacks key_scheme -- fall
            # through to the top-level fallback (preserves existing
            # _minimal_envelope tests).
            top = envelope.get("key_scheme")
            return str(top) if top is not None else None
        if env_type in ("task_result", "job_result"):
            block = envelope.get("receipt_signature")
            if isinstance(block, dict):
                scheme = block.get("key_scheme")
                if scheme is not None:
                    return str(scheme)
            top = envelope.get("key_scheme")
            return str(top) if top is not None else None
        if env_type in ("task_error", "job_error"):
            # Error envelopes are unsigned by spec.
            return None
        # No ``type`` field -- synthetic flat-dict test path (tolerated).
        top = envelope.get("key_scheme")
        return str(top) if top is not None else None


# ---------------------------------------------------------------------------
# Brine reference adapter (Ed25519 + python-keyring).
#
# Heavy details (round-trip, tamper detection, IDENT-05 keystore guard) are
# exercised by ``tests/test_identity_brine_roundtrip.py`` and
# ``tests/test_identity_keystore_required.py`` (Task 2 of Plan 01-03).


_KEYSTORE_SERVICE_DEFAULT: Final[str] = "thermocline.brine"

#: Keystore-key prefix for *public* verify keys registered via
#: :meth:`BrineProvider.register_public_key`. Public-key entries live in
#: the SAME keystore service but under this prefix, so they cannot collide
#: with seed entries (seed entries use the bare identity string).
_PUBKEY_PREFIX: Final[str] = "pubkey:"


class BrineProvider:
    """Ed25519 IdentityProvider backed by ``python-keyring``.

    Security properties (forever):

    * Never returns key material from any method (IDENT-02 / Pitfall 9). The
      only exported method that touches a key returns the **public** verify
      key.
    * Refuses to start when the platform secure keystore is unavailable
      (IDENT-05); does NOT fall back to file or env-var key storage. There is
      no fallback path — IDENT-05 is enforced both by the absence of fallback
      code AND by the static lint in
      ``tests/test_identity_keystore_required.py``.
    * Calls ``keyring`` per signature; no in-process key cache (Pitfall 9).
    * Signing input is canonical-JSON via :func:`thermocline.canonical.canonicalize`
      — never ``json.dumps`` (Pitfall 11).

    The constructor probes the keystore at startup. If the keyring backend is
    missing, fail-typed, or null-typed, :class:`KeystoreUnavailableError` is
    raised and the adapter never returns. There is no graceful degradation by
    design.
    """

    scheme: ClassVar[KeyScheme] = KeyScheme.BRINE

    def __init__(self, *, keyring_service: str = _KEYSTORE_SERVICE_DEFAULT) -> None:
        # IDENT-05: probe the keystore at startup and refuse if unavailable.
        # We catch both the explicit NoKeyringError and the more common
        # signal — get_keyring() returns the fail/null backend rather than
        # raising. Either signal triggers KeystoreUnavailableError.
        try:
            backend = keyring.get_keyring()
        except NoKeyringError as exc:
            raise KeystoreUnavailableError(
                f"refusing to start: no keyring backend available ({exc}). "
                "Brine adapter NEVER falls back to file or env-var storage "
                "(IDENT-05).",
                code="KEYSTORE_UNAVAILABLE",
            ) from exc
        # BL-03 closure: isinstance probe against the production fail/null
        # backend classes. Both classes are named ``Keyring`` -- the previous
        # substring heuristic on ``type(backend).__name__`` missed both. Direct
        # class identity is the only correct way.
        if isinstance(backend, (_fail_backend.Keyring, _null_backend.Keyring)):
            raise KeystoreUnavailableError(
                f"refusing to start: keyring backend is "
                f"{type(backend).__module__}.{type(backend).__name__!r} "
                "(no working secure keystore). Brine adapter NEVER falls "
                "back to file or env-var storage (IDENT-05).",
                code="KEYSTORE_UNAVAILABLE",
            )
        self._keyring_service = keyring_service

    def generate(self, *, identity: str) -> None:
        """Generate a new Ed25519 keypair and store the seed in the keystore.

        The 32-byte signing seed is hex-encoded and handed straight to
        ``keyring.set_password``; we drop our reference immediately. Python's
        garbage collector does not zero memory, so the ``del`` is a hygiene
        marker rather than a guarantee — it documents intent and reviewers
        will catch additions that retain references.
        """
        signing_key = nacl.signing.SigningKey.generate()
        keyring.set_password(
            self._keyring_service, identity, signing_key.encode().hex()
        )
        del signing_key

    def public_key(self, *, identity: str) -> bytes:
        """Return the 32-byte Ed25519 verify key for ``identity``.

        Lookup order (BL-01 closure -- load-bearing):

        1. Public-key store -- ``keyring.get_password(self._keyring_service,
           _PUBKEY_PREFIX + identity)``. Populated by
           :meth:`register_public_key`. This is the path a verifier-only role
           takes -- it holds public keys for other nodes without ever holding
           their seeds.
        2. Seed store -- ``keyring.get_password(self._keyring_service,
           identity)``. Populated by :meth:`generate`. The verify key is
           derived from the seed. This is the same-node self-signing path
           (the original behaviour).

        A node that holds BOTH a registered public key AND a seed for the
        same identity returns the registered public key (verify-role takes
        precedence). The lookup-order invariant is exercised by
        ``test_pubkey_store_is_consulted_before_seed`` in
        ``test_identity_cross_role.py``.

        Raises :class:`IdentityError` (code ``IDENTITY_NOT_FOUND``) when both
        are absent.
        """
        pub_hex = keyring.get_password(
            self._keyring_service, _PUBKEY_PREFIX + identity
        )
        if pub_hex is not None:
            try:
                verify_key_bytes = bytes.fromhex(pub_hex)
            except ValueError as exc:
                raise IdentityError(
                    f"corrupted public-key entry for identity {identity!r}: not hex",
                    code="IDENTITY_NOT_FOUND",
                ) from exc
            if len(verify_key_bytes) != 32:
                raise IdentityError(
                    f"corrupted public-key entry for identity {identity!r}: "
                    f"expected 32 bytes, got {len(verify_key_bytes)}",
                    code="IDENTITY_NOT_FOUND",
                )
            return verify_key_bytes

        seed_hex = keyring.get_password(self._keyring_service, identity)
        if seed_hex is None:
            raise IdentityError(
                f"no brine key stored for identity {identity!r}",
                code="IDENTITY_NOT_FOUND",
            )
        signing_key = nacl.signing.SigningKey(bytes.fromhex(seed_hex))
        verify_key_bytes = bytes(signing_key.verify_key)
        del signing_key
        return verify_key_bytes

    def register_public_key(
        self, *, identity: str, verify_key: bytes
    ) -> None:
        """Register a foreign node's Ed25519 verify key under ``identity``.

        BL-01 closure: this is the documented path by which a verifier-only
        role acquires another node's identity material. Public-key entries
        live under a separate namespace (``_PUBKEY_PREFIX + identity``) so
        they do not collide with seed entries.

        Parameters
        ----------
        identity
            Stable identity string for the foreign node -- same value the
            foreign node passes to ``sign(signer_identity=...)``.
        verify_key
            Exactly 32 bytes -- the Ed25519 verify key (NOT the seed).
            Typically obtained out-of-band from the foreign node's
            :meth:`public_key` call.

        Raises
        ------
        IdentityError
            Code ``INVALID_VERIFY_KEY`` if ``verify_key`` is not exactly 32
            bytes.
        """
        if not isinstance(verify_key, (bytes, bytearray)) or len(verify_key) != 32:
            length = (
                len(verify_key)
                if isinstance(verify_key, (bytes, bytearray))
                else "N/A"
            )
            raise IdentityError(
                f"verify_key must be exactly 32 bytes; got "
                f"{type(verify_key).__name__} of length {length}",
                code="INVALID_VERIFY_KEY",
            )
        keyring.set_password(
            self._keyring_service,
            _PUBKEY_PREFIX + identity,
            bytes(verify_key).hex(),
        )

    def sign(
        self, *, envelope: dict[str, Any], signer_identity: str
    ) -> Signature:
        """Sign ``canonicalize(envelope)`` with the brine identity's seed.

        Returns a :class:`Signature`. Never returns key material. Pitfall 11:
        signing input is RFC 8785 canonical JSON, not stdlib ``json``.
        """
        seed_hex = keyring.get_password(self._keyring_service, signer_identity)
        if seed_hex is None:
            raise IdentityError(
                f"no brine key stored for identity {signer_identity!r}",
                code="IDENTITY_NOT_FOUND",
            )
        canonical = canonicalize(envelope)
        signing_key = nacl.signing.SigningKey(bytes.fromhex(seed_hex))
        signed = signing_key.sign(canonical)
        sig_bytes = bytes(signed.signature)  # 64 bytes for Ed25519
        del signing_key
        return Signature(
            scheme=KeyScheme.BRINE,
            bytes_=sig_bytes,
            signer_identity=signer_identity,
        )

    def verify(
        self, *, envelope: dict[str, Any], signature: Signature
    ) -> Receipt | None:
        """Verify a brine Ed25519 signature against ``canonicalize(envelope)``.

        Returns
        -------
        Receipt | None
            A :class:`Receipt` on success; ``None`` on tamper detection (the
            ``BadSignatureError`` is suppressed and the verify-failed path
            returns the no-receipt sentinel — Pitfall 5 / T-03-02).

        Raises
        ------
        SchemeError
            If the signature's declared scheme is not :attr:`KeyScheme.BRINE`.
        IdentityError
            If the signer identity has no key in the keystore.

        Notes
        -----
        ``signature_hash`` is ``blake2b(canonical_bytes + signature.bytes_,
        digest_size=32).hex()``. The recipe is documented here so
        cross-language ports can match it byte-for-byte (T-03-07).
        """
        if signature.scheme is not KeyScheme.BRINE:
            raise SchemeError(
                f"BrineProvider cannot verify signature with scheme "
                f"{signature.scheme.value!r}",
                code="UNSUPPORTED_KEY_SCHEME",
            )
        verify_key_bytes = self.public_key(identity=signature.signer_identity)
        verify_key = nacl.signing.VerifyKey(verify_key_bytes)
        canonical = canonicalize(envelope)
        try:
            verify_key.verify(canonical, signature.bytes_)
        except nacl.exceptions.BadSignatureError:
            return None
        sig_hash = hashlib.blake2b(
            canonical + signature.bytes_, digest_size=32
        ).hexdigest()
        envelope_id = str(envelope.get("envelope_id", ""))
        return Receipt(
            envelope_id=envelope_id,
            signature_hash=sig_hash,
            verified_at=datetime.now(timezone.utc),
            key_scheme=KeyScheme.BRINE,
            _token=_RECEIPT_TOKEN,
        )
