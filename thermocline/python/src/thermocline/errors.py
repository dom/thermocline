"""Typed exception hierarchy for ``thermocline-py``.

Error ``code`` strings are part of the public API and are matched on by forge
handlers, conformance fixtures, and downstream callers. Codes are stable across
releases unless an explicit ADR retires one.
"""
from __future__ import annotations


class EnvelopeError(Exception):
    """Base class for all errors raised by the thermocline library.

    Subclasses set a default ``code`` matching the spec's error vocabulary; the
    code is also exposed as an instance attribute so error-handlers can match
    on a stable string rather than the exception class.
    """

    #: Default code for this exception class. Subclasses override.
    default_code: str = "ENVELOPE_ERROR"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code: str = code if code is not None else self.default_code

    def __repr__(self) -> str:
        return f"{type(self).__name__}(code={self.code!r}, message={self.message!r})"


class UnsupportedVersionError(EnvelopeError):
    """Envelope declared a version not in :data:`thermocline.version.SUPPORTED_VERSIONS`.

    Code: ``UNSUPPORTED_VERSION``. THERMO-07.
    """

    default_code = "UNSUPPORTED_VERSION"


class CanonicalizationError(EnvelopeError):
    """RFC 8785 canonicalization failed (Plan 02 surface).

    Code: ``CANONICALIZATION_FAILED``.
    """

    default_code = "CANONICALIZATION_FAILED"


class IdentityError(EnvelopeError):
    """Identity-provider operation failed (Plan 03 surface).

    Code: ``IDENTITY_ERROR``.
    """

    default_code = "IDENTITY_ERROR"


class SchemeError(IdentityError):
    """A signing or verification request used an unsupported key scheme.

    Code: ``UNSUPPORTED_KEY_SCHEME``. Plan 03 / IDENT-03.
    """

    default_code = "UNSUPPORTED_KEY_SCHEME"


class KeystoreUnavailableError(IdentityError):
    """Platform keystore is not reachable; identity adapter must refuse to start.

    Code: ``KEYSTORE_UNAVAILABLE``. Plan 03 / IDENT-05.
    """

    default_code = "KEYSTORE_UNAVAILABLE"


__all__ = [
    "EnvelopeError",
    "UnsupportedVersionError",
    "CanonicalizationError",
    "IdentityError",
    "SchemeError",
    "KeystoreUnavailableError",
]
