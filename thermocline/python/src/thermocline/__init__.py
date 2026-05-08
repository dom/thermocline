"""Public API surface for ``thermocline-py``.

Downstream consumers (Photophore, pi-forge, describe-forge, future cross-language
ports) import only from this module. The full lock-in surface is::

    from thermocline import (
        Task, TaskResult, Job, JobResult, ErrorEnvelope, ContentBlock,
        Sensitive, KeyScheme, SUPPORTED_VERSIONS, EnvelopeError,
    )

(Plan 02 will add ``canonicalize``; Plan 03 will add ``IdentityProvider``,
``Receipt``, ``Signature``, and the brine adapter.)
"""
from __future__ import annotations

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

# Envelope models (Pydantic v2) live in .envelope. Task 2 of plan 01 adds
# the module and the names below; until then, downstream callers that expect
# Task / TaskResult / Job / JobResult / ErrorEnvelope / ContentBlock from
# `thermocline` get an ImportError. The package is otherwise fully usable.
_envelope_names: list[str]
try:
    from .envelope import (  # type: ignore[import-not-found,unused-ignore]
        ContentBlock,
        ErrorEnvelope,
        Job,
        JobResult,
        Task,
        TaskResult,
    )

    _envelope_names = [
        "Task",
        "TaskResult",
        "Job",
        "JobResult",
        "ErrorEnvelope",
        "ContentBlock",
    ]
except ImportError:
    _envelope_names = []

__all__ = [
    *_envelope_names,
    # Privacy primitive.
    "Sensitive",
    # Key-scheme enum.
    "KeyScheme",
    # Version registry.
    "SUPPORTED_VERSIONS",
    "validate_version",
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
