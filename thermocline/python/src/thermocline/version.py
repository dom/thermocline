"""Thermocline version registry and validation helper.

`SUPPORTED_VERSIONS` is the authoritative list of envelope versions this
library accepts. Unknown declared versions are rejected with
:class:`UnsupportedVersionError` (THERMO-07).
"""
from __future__ import annotations

from .errors import UnsupportedVersionError

# Currently-accepted Thermocline envelope versions.
#
# v0.3.0 is the existing pi-forge baseline; v0.3.1 is this library's target
# version (the cirdan -> thermocline JSON field rename, shipped at
# thermocline@5c0d87c).
SUPPORTED_VERSIONS: frozenset[str] = frozenset({"0.3.0", "0.3.1"})


def validate_version(declared: str) -> None:
    """Raise :class:`UnsupportedVersionError` if ``declared`` is not supported.

    Parameters
    ----------
    declared
        The version string carried in the envelope's ``thermocline`` field.

    Raises
    ------
    UnsupportedVersionError
        If ``declared`` is not in :data:`SUPPORTED_VERSIONS`.
    """
    if declared not in SUPPORTED_VERSIONS:
        supported = ", ".join(sorted(SUPPORTED_VERSIONS))
        raise UnsupportedVersionError(
            f"Unsupported Thermocline version: {declared!r}. Supported: {supported}",
        )


__all__ = ["SUPPORTED_VERSIONS", "validate_version"]
