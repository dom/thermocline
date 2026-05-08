"""Public API surface for ``thermocline-py``.

Downstream consumers (Photophore, pi-forge, describe-forge, future cross-language
ports) import only from this module. The full lock-in surface is::

    from thermocline import (
        Task, TaskResult, Job, JobResult, ErrorEnvelope, ContentBlock,
        Sensitive, KeyScheme, SUPPORTED_VERSIONS, EnvelopeError,
        canonicalize,
    )

(Plan 03 will add ``IdentityProvider``, ``Receipt``, ``Signature``, and the
brine adapter.)
"""
from __future__ import annotations

from .canonical import canonicalize
from .envelope import (
    ContentBlock,
    ErrorEnvelope,
    Job,
    JobResult,
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
    # Privacy primitive.
    "Sensitive",
    # Key-scheme enum.
    "KeyScheme",
    # Version registry.
    "SUPPORTED_VERSIONS",
    "validate_version",
    # Canonical JSON (Plan 02 — the single signing-input path).
    "canonicalize",
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
