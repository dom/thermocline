"""Public API surface for ``thermocline-py``.

Downstream consumers (Photophore, pi-forge, describe-forge, future cross-language
ports) import only from this module. The full lock-in surface is::

    from thermocline import (
        Task, TaskResult, Job, JobResult, ErrorEnvelope, ContentBlock,
        Sensitive, KeyScheme, SUPPORTED_VERSIONS, EnvelopeError,
        canonicalize, CanonicalizationError,
        IdentityProvider, BrineProvider, Verifier, Signature, Receipt,
        IdentityError, SchemeError, KeystoreUnavailableError,
    )

Identity primitives — Protocol, Verifier, brine adapter, Signature/Receipt
value types, plus the typed identity exceptions — are exported alongside
the envelope shapes and canonical JSON helper.
"""
from __future__ import annotations

from .canonical import canonicalize
from .envelope import (
    ContentBlock,
    ErrorEnvelope,
    Job,
    JobResult,
    ResultPolicy,  # Public since v0.3 (renamed from private _ResultPolicy)
    Task,
    TaskResult,
)
from .errors import (
    CanonicalizationError,
    EnvelopeError,
    IdentityError,
    KeystoreUnavailableError,
    SchemeError,
    UnsupportedVersionError,
)
from .identity import (
    BrineProvider,
    IdentityProvider,
    Receipt,
    Signature,
    Verifier,
)
from .schemes import KeyScheme
from .sensitive import Sensitive
from .version import SUPPORTED_VERSIONS, validate_version

__version__ = "0.3.1"

__all__ = [
    # Envelope shapes (Pydantic v2 models from .envelope).
    "Task",
    "TaskResult",
    "Job",
    "JobResult",
    "ErrorEnvelope",
    "ContentBlock",
    # Result policy model (public since v0.3; renamed from private
    # _ResultPolicy — alias retained in envelope.py for one minor cycle).
    "ResultPolicy",
    # Privacy primitive.
    "Sensitive",
    # Key-scheme enum.
    "KeyScheme",
    # Version registry.
    "SUPPORTED_VERSIONS",
    "validate_version",
    # Canonical JSON — the single signing-input path across the suite.
    "canonicalize",
    # Identity primitives.
    "IdentityProvider",
    "BrineProvider",
    "Verifier",
    "Signature",
    "Receipt",
    # Exception hierarchy (codes are part of the public API).
    "EnvelopeError",
    "UnsupportedVersionError",
    "CanonicalizationError",
    "IdentityError",
    "SchemeError",
    "KeystoreUnavailableError",
    # Library version.
    "__version__",
]
