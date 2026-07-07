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
    "UnsignedAck",
    "IdentityProvider",
    "Verifier",
    "BrineProvider",
]

#: Versioned tag for the ``Receipt.signature_hash`` recipe (ADR-0004). The
#: recipe is ``blake2b(canonical_bytes + signature_bytes, digest_size=32)``;
#: the tag lets cross-language ports and future migrations dispatch on an
#: explicit algorithm identifier rather than an implicit default.
SIGNATURE_HASH_ALGO: Final[str] = "blake2b-256-v1"


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
    #: Identity whose public key verified the signature. Bound to the
    #: envelope's declared ``node_id`` on the verify path (AT-C4): a Receipt
    #: can only exist for the identity the envelope claimed as signer.
    verified_identity: str
    #: Versioned tag for the ``signature_hash`` recipe so cross-language ports
    #: and future hash migrations dispatch on an explicit algorithm identifier
    #: rather than an implicit default (ADR-0004 versioned-hash discipline).
    signature_hash_algo: str

    def __init__(
        self,
        *,
        envelope_id: str,
        signature_hash: str,
        verified_at: datetime,
        key_scheme: KeyScheme,
        verified_identity: str,
        _token: _ReceiptConstructorToken,
        signature_hash_algo: str = "blake2b-256-v1",
    ) -> None:
        if _token is not _RECEIPT_TOKEN:
            raise TypeError(
                "Receipt is constructible only by IdentityProvider.verify() "
                "returning success. Direct construction is forbidden by design: "
                "a Receipt represents a verified envelope, and constructing one "
                "without going through verify() would let unverified envelopes "
                "appear as if they had passed the privacy fence."
            )
        # ``frozen=True`` forbids attribute assignment after __init__; this is
        # the one acceptable use of object.__setattr__ in this codebase. The
        # frozen guarantee is what makes Receipt safe to pass through the audit
        # log without copy-on-write concerns.
        object.__setattr__(self, "envelope_id", envelope_id)
        object.__setattr__(self, "signature_hash", signature_hash)
        object.__setattr__(self, "verified_at", verified_at)
        object.__setattr__(self, "key_scheme", key_scheme)
        object.__setattr__(self, "verified_identity", verified_identity)
        object.__setattr__(self, "signature_hash_algo", signature_hash_algo)


# ---------------------------------------------------------------------------
# UnsignedAck — the defined return of the ``none`` key scheme.


@dataclass(frozen=True, slots=True)
class UnsignedAck:
    """Explicit acknowledgement that an envelope carried ``key_scheme=none``.

    ``none`` is a spec-valid scheme (honest about the absence of a signature)
    but it is NOT a verified :class:`Receipt`: nothing was cryptographically
    checked. The verify helpers return this distinct type only when the caller
    explicitly opts into the unsigned path (``allow_unsigned=True``); otherwise
    they raise :class:`SchemeError` (code ``UNSIGNED_SCHEME_REJECTED``).

    A downstream forge that requires integrity (Seamount) refuses ``none`` by
    leaving ``allow_unsigned`` at its default ``False`` and treating any
    ``UnsignedAck`` it constructs itself as non-authoritative. The spec forbids
    ``none`` on channels with a trust ceiling above tier-0.
    """

    envelope_id: str
    reason: str = "key_scheme=none: envelope is unsigned (no integrity guarantee)"


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

    def rotate(self, *, identity: str) -> None:
        """Replace the signing key, archiving the old verify key (key.rotate).

        Envelopes signed before rotation MUST remain verifiable against the
        archived key (README §"Constraints"). See :meth:`BrineProvider.rotate`.
        """
        ...

    def revoke(self, *, identity: str, key_version: int | None = None) -> None:
        """Mark a key revoked so verifiers reject its signatures (key.revoke).

        ``key_version`` selects an archived version; ``None`` revokes the
        current key. See :meth:`BrineProvider.revoke`.
        """
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

        ``key_scheme`` lookup is canonical-location-aware via
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

        Lookup table by envelope ``type`` (exhaustive over the five envelope
        types defined in :mod:`thermocline.envelope`):

        * ``task``, ``job`` -> ``envelope['dispatch_signature']['key_scheme']``
        * ``task_result``, ``job_result`` ->
          ``envelope['receipt_signature']['key_scheme']``
        * ``task_error``, ``job_error`` (the two ``ErrorEnvelope.type``
          discriminator values per ``envelope.py``) -> ``None``. Error
          envelopes are unsigned by spec; the verifier should never be
          called on one. Returning ``None`` surfaces the misuse as
          :class:`SchemeError` (because ``None != signature.scheme.value``).

        Fallback rule (restricted in 0.4.0): the top-level
        ``envelope.get('key_scheme')`` fallback applies ONLY to envelopes with
        NO ``type`` field (synthetic flat-dict test inputs). A *typed* envelope
        (``task`` / ``job`` / ``task_result`` / ``job_result``) whose nested
        signature block is absent, empty, or missing ``key_scheme`` is malformed
        for verification and raises :class:`SchemeError`. The prior behavior
        tolerated a non-spec top-level ``key_scheme`` on typed envelopes "so
        tests pass"; that loophole let a signer place the scheme at a location
        the wire format never defines. It is closed.
        """
        env_type = envelope.get("type")
        if env_type in ("task", "job", "task_result", "job_result"):
            block_key = (
                "dispatch_signature"
                if env_type in ("task", "job")
                else "receipt_signature"
            )
            block = envelope.get(block_key)
            if isinstance(block, dict):
                scheme = block.get("key_scheme")
                if scheme is not None:
                    return str(scheme)
            raise SchemeError(
                f"typed envelope {env_type!r} has no declared key_scheme in its "
                f"{block_key!r} block; a non-spec top-level key_scheme is not "
                "accepted (scheme must live in the nested signature block)",
                code="UNSUPPORTED_KEY_SCHEME",
            )
        if env_type in ("task_error", "job_error"):
            # Error envelopes are unsigned by spec.
            return None
        # No ``type`` field -- synthetic flat-dict test path (tolerated).
        top = envelope.get("key_scheme")
        return str(top) if top is not None else None

    @staticmethod
    def _declared_node_id(envelope: dict[str, Any]) -> str | None:
        """Return the ``node_id`` declared in the canonical signature block.

        Mirrors :meth:`_declared_scheme`'s block routing. Returns ``None`` when
        the envelope has no typed signature block (synthetic flat-dict inputs),
        so the node-id binding check is skipped for those.
        """
        env_type = envelope.get("type")
        block_key: str | None
        if env_type in ("task", "job"):
            block_key = "dispatch_signature"
        elif env_type in ("task_result", "job_result"):
            block_key = "receipt_signature"
        else:
            block_key = None
        if block_key is not None:
            block = envelope.get(block_key)
            if isinstance(block, dict):
                node_id = block.get("node_id")
                if node_id is not None:
                    return str(node_id)
        return None


# ---------------------------------------------------------------------------
# Brine reference adapter (Ed25519 + python-keyring).
#
# Heavy details (round-trip, tamper detection, IDENT-05 keystore guard) are
# exercised by ``tests/test_identity_brine_roundtrip.py`` and
# ``tests/test_identity_keystore_required.py``.


_KEYSTORE_SERVICE_DEFAULT: Final[str] = "thermocline.brine"

#: Keystore-key prefix for *public* verify keys registered via
#: :meth:`BrineProvider.register_public_key`. Public-key entries live in
#: the SAME keystore service but under this prefix, so they cannot collide
#: with seed entries (seed entries use the bare identity string).
_PUBKEY_PREFIX: Final[str] = "pubkey:"

#: Prefix for an archived verify key produced by :meth:`BrineProvider.rotate`.
#: Full key is ``archive:<identity>:<version>`` -> hex verify key. Archived
#: keys remain verifiable so envelopes signed before a rotation still verify
#: (README §"Constraints": a rotated key remains valid for verification).
_ARCHIVE_PREFIX: Final[str] = "archive:"

#: Prefix for the archive-version counter: ``archivecount:<identity>`` -> int.
_ARCHIVE_COUNT_PREFIX: Final[str] = "archivecount:"

#: Prefix for revocation flags. ``revoked:<identity>`` revokes the current key;
#: ``revoked:<identity>:<version>`` revokes a specific archived version.
_REVOKED_PREFIX: Final[str] = "revoked:"


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
        # isinstance probe against the production fail/null backend classes.
        # Both classes are named ``Keyring`` -- a substring heuristic on
        # ``type(backend).__name__`` misses both. Direct class identity is
        # the only correct way.
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

        Refuses to clobber an existing seed: re-generating an identity is a
        deliberate, audited operation -- use :meth:`rotate` instead. Calling
        ``generate`` on an identity that already has a seed raises
        ``IdentityError(code='IDENTITY_ALREADY_EXISTS')``. This closes a
        foreseeable data-loss path: re-running a setup script no longer
        destroys the prior signing identity.

        The 32-byte signing seed is hex-encoded and handed straight to
        ``keyring.set_password``; we drop our reference immediately. Python's
        garbage collector does not zero memory, so the ``del`` is a hygiene
        marker rather than a guarantee -- it documents intent and reviewers
        will catch additions that retain references.

        Raises
        ------
        IdentityError
            Code ``IDENTITY_ALREADY_EXISTS`` if a seed already exists at
            ``(self._keyring_service, identity)``.
        """
        existing = keyring.get_password(self._keyring_service, identity)
        if existing is not None:
            raise IdentityError(
                f"identity {identity!r} already has a seed; "
                "use rotate() to replace it deliberately",
                code="IDENTITY_ALREADY_EXISTS",
            )
        signing_key = nacl.signing.SigningKey.generate()
        keyring.set_password(
            self._keyring_service, identity, signing_key.encode().hex()
        )
        del signing_key

    def rotate(self, *, identity: str) -> None:
        """Replace the seed for ``identity`` with a freshly-generated one.

        This is the ONLY documented path that overwrites an existing seed.
        ``generate`` refuses to clobber by design; use ``rotate`` for
        deliberate replacement.

        Post-condition: the seed stored at ``(self._keyring_service,
        identity)`` is different from the seed that was there before this
        call. Any :meth:`register_public_key` entry for the same identity is
        independent (it lives under a different keystore key, namespaced by
        ``_PUBKEY_PREFIX``) and is NOT touched by this call -- the
        seed-vs-public-key orthogonality is the lookup-order invariant
        exercised in ``test_identity_cross_role.py``.

        Raises
        ------
        IdentityError
            Code ``IDENTITY_NOT_FOUND`` if no seed exists for ``identity`` to
            rotate. (Use :meth:`generate` first.)
        """
        existing = keyring.get_password(self._keyring_service, identity)
        if existing is None:
            raise IdentityError(
                f"cannot rotate identity {identity!r}: no seed exists "
                "(use generate() first)",
                code="IDENTITY_NOT_FOUND",
            )
        # Archive the OLD verify key under a versioned entry so envelopes signed
        # before this rotation remain verifiable (README §"Constraints": "A
        # rotated key remains valid for verification of previously signed
        # envelopes"). We archive the public verify key only, never the seed.
        old_signing_key = nacl.signing.SigningKey(bytes.fromhex(existing))
        old_verify_hex = bytes(old_signing_key.verify_key).hex()
        del old_signing_key
        version = self._archive_count(identity)
        keyring.set_password(
            self._keyring_service,
            f"{_ARCHIVE_PREFIX}{identity}:{version}",
            old_verify_hex,
        )
        keyring.set_password(
            self._keyring_service,
            f"{_ARCHIVE_COUNT_PREFIX}{identity}",
            str(version + 1),
        )
        new_signing_key = nacl.signing.SigningKey.generate()
        keyring.set_password(
            self._keyring_service, identity, new_signing_key.encode().hex()
        )
        del new_signing_key

    def revoke(self, *, identity: str, key_version: int | None = None) -> None:
        """Mark a key revoked so :meth:`verify` rejects its signatures.

        ``key_version=None`` (default) revokes the identity's CURRENT signing
        key. Passing an integer revokes a specific archived verify-key version
        (as produced by :meth:`rotate`). Revocation is idempotent and additive;
        there is no un-revoke path by design (revocation is a one-way trust
        decision, README §"Required Capabilities" key.revoke).

        Raises
        ------
        IdentityError
            Code ``IDENTITY_NOT_FOUND`` if revoking the current key of an
            identity that has no seed and no registered public key.
        """
        if key_version is None:
            has_seed = (
                keyring.get_password(self._keyring_service, identity) is not None
            )
            has_pub = (
                keyring.get_password(
                    self._keyring_service, _PUBKEY_PREFIX + identity
                )
                is not None
            )
            if not has_seed and not has_pub:
                raise IdentityError(
                    f"cannot revoke identity {identity!r}: no key material exists",
                    code="IDENTITY_NOT_FOUND",
                )
            keyring.set_password(
                self._keyring_service, f"{_REVOKED_PREFIX}{identity}", "1"
            )
        else:
            keyring.set_password(
                self._keyring_service,
                f"{_REVOKED_PREFIX}{identity}:{key_version}",
                "1",
            )

    def _archive_count(self, identity: str) -> int:
        raw = keyring.get_password(
            self._keyring_service, f"{_ARCHIVE_COUNT_PREFIX}{identity}"
        )
        return int(raw) if raw is not None else 0

    def _is_revoked(self, identity: str, key_version: int | None = None) -> bool:
        key = (
            f"{_REVOKED_PREFIX}{identity}"
            if key_version is None
            else f"{_REVOKED_PREFIX}{identity}:{key_version}"
        )
        return keyring.get_password(self._keyring_service, key) is not None

    def _archived_verify_keys(self, identity: str) -> list[tuple[int, bytes]]:
        """Return non-revoked archived ``(version, verify_key_bytes)`` pairs."""
        out: list[tuple[int, bytes]] = []
        for version in range(self._archive_count(identity)):
            if self._is_revoked(identity, version):
                continue
            hex_key = keyring.get_password(
                self._keyring_service, f"{_ARCHIVE_PREFIX}{identity}:{version}"
            )
            if hex_key is None:
                continue
            try:
                key_bytes = bytes.fromhex(hex_key)
            except ValueError:
                continue
            if len(key_bytes) == 32:
                out.append((version, key_bytes))
        return out

    def public_key(self, *, identity: str) -> bytes:
        """Return the 32-byte Ed25519 verify key for ``identity``.

        Lookup order (load-bearing):

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
        are absent, or (code ``KEY_REVOKED``) when the current key has been
        revoked via :meth:`revoke`.
        """
        if self._is_revoked(identity):
            raise IdentityError(
                f"current key for identity {identity!r} is revoked",
                code="KEY_REVOKED",
            )
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

        This is the documented path by which a verifier-only role acquires
        another node's identity material. Public-key entries live under a
        separate namespace (``_PUBKEY_PREFIX + identity``) so they do not
        collide with seed entries.

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
        # AT-C4 / README §"AT-C4": bind verification to the envelope's declared
        # node_id. A signature that verifies under one identity's key but
        # claims a different node_id in the envelope is an impersonation
        # attempt; refuse to produce a Receipt.
        identity = signature.signer_identity
        declared_node_id = Verifier._declared_node_id(envelope)
        if declared_node_id is not None and declared_node_id != identity:
            return None
        canonical = canonicalize(envelope)

        # Candidate verify keys, in precedence order: the current key (unless
        # revoked), then each non-revoked archived key from prior rotations.
        # Archived keys let envelopes signed before a rotation still verify
        # (README §"Constraints"); revoked keys are excluded (key.revoke).
        candidates: list[bytes] = []
        if not self._is_revoked(identity):
            candidates.append(self.public_key(identity=identity))
        candidates.extend(key for _, key in self._archived_verify_keys(identity))

        for verify_key_bytes in candidates:
            try:
                nacl.signing.VerifyKey(verify_key_bytes).verify(
                    canonical, signature.bytes_
                )
            except nacl.exceptions.BadSignatureError:
                continue
            sig_hash = hashlib.blake2b(
                canonical + signature.bytes_, digest_size=32
            ).hexdigest()
            return Receipt(
                envelope_id=str(envelope.get("envelope_id", "")),
                signature_hash=sig_hash,
                verified_at=datetime.now(timezone.utc),
                key_scheme=KeyScheme.BRINE,
                verified_identity=identity,
                signature_hash_algo=SIGNATURE_HASH_ALGO,
                _token=_RECEIPT_TOKEN,
            )
        return None
