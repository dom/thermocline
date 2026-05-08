"""RFC 8785 canonical JSON — the only path for signing input across the suite.

Phase 1 design decision and Pitfall 11: Python's stdlib ``json`` module emits
non-canonical output (``sort_keys`` defaults to False, separators include
whitespace). A signature computed over ``json``-stdlib output does not verify
across implementations whose map iteration order differs. Every signing or
verifying path in the Thermocline suite (Plan 03 brine adapter, Phase 2 audit
chain, Phase 3 dispatch coordinator, future cross-language ports) MUST funnel
through ``thermocline.canonical.canonicalize``.

The implementation delegates to the third-party ``rfc8785`` package, which
implements RFC 8785 / JCS exactly: object keys are sorted lexicographically
by code point, numbers are stringified per ECMA-262 §7.1.12.1 (integer-valued
floats normalize to integer form), arrays preserve order, and no whitespace
appears anywhere in the output. The single ``canonicalize`` function is the
only place in the library that calls ``rfc8785.dumps``.
"""
from __future__ import annotations

from typing import Any

import rfc8785

from .errors import CanonicalizationError

__all__ = ["canonicalize", "CanonicalizationError"]


# JsonScalar / JsonValue document the shape ``model.model_dump(mode="json")``
# produces. They are intentionally permissive (``Any`` parameter) at the
# function boundary so callers can pass arbitrary Pydantic dump output without
# casts; ``rfc8785`` performs the actual JSON-shape check at the boundary and
# raises on non-serializable inputs (sets, datetimes, raw bytes, custom
# objects). Library code that hand-builds payloads should use the typed
# aliases below.
JsonScalar = str | int | float | bool | None
JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]


def canonicalize(payload: Any) -> bytes:
    """Return RFC 8785 canonical-JSON bytes for ``payload``.

    Parameters
    ----------
    payload
        A value produced by Pydantic ``model.model_dump(mode="json")`` —
        recursively ``dict[str, JsonValue]``, ``list[JsonValue]``, ``str``,
        ``int``, ``float``, ``bool``, or ``None``. The ``mode="json"``
        discipline ensures :class:`thermocline.Sensitive[bytes]` content has
        already been base64-encoded to ``str`` before reaching this function.

    Returns
    -------
    bytes
        Canonical-JSON bytes per RFC 8785. The same logical payload always
        produces the same bytes regardless of source-language map ordering.
        Object keys are sorted; arrays preserve order; integers and integer-
        valued floats both serialize as integer form (ECMA-262); booleans and
        ``null`` are lowercase; no whitespace appears anywhere.

    Raises
    ------
    CanonicalizationError
        On inputs containing non-JSON-serializable types (sets, datetimes,
        custom objects, raw ``bytes``) or any internal ``rfc8785`` failure.
        The error is raised early so signing paths cannot silently fall back
        to non-canonical encoders. The original exception is chained via
        ``__cause__``.
    """
    try:
        return rfc8785.dumps(payload)
    except (TypeError, ValueError) as exc:
        # ``rfc8785.CanonicalizationError`` is a ``ValueError`` subclass; this
        # branch covers it and any other shape mismatch the package surfaces
        # (FloatDomainError on NaN/Inf, IntegerDomainError on overflow). All
        # are wrapped under the typed thermocline error so callers match on
        # one stable code (``CANONICALIZATION_FAILED``).
        raise CanonicalizationError(
            f"payload is not canonical-JSON-serializable: {exc}"
        ) from exc
