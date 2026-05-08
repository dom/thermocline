"""``Sensitive[T]`` — the redacting wrapper for privacy-sensitive content.

Phase 1 design decision D-03: every privacy-sensitive content field in the
envelope models is typed ``Sensitive[bytes]`` from day 1. The wrapper has:

- A redacting ``__repr__`` and ``__str__`` so accidental ``print`` calls or
  ``logger.info("%s", envelope)`` calls cannot leak the underlying bytes
  (Pitfall 4).
- A ``.reveal()`` accessor — the only path to the wrapped value. Use sites
  that need the raw bytes call this method explicitly, which makes leakage
  visible in code review.
- Pydantic v2 ``__get_pydantic_core_schema__`` integration so Pydantic models
  containing ``Sensitive[bytes]`` fields:
    * accept raw ``bytes``, ``bytearray``, base64 ``str``, or another
      ``Sensitive`` on validation;
    * serialize to a base64 ASCII string in JSON output;
    * round-trip byte-for-byte through ``model_dump_json`` /
      ``model_validate_json``.

The wire format is unchanged from a non-wrapped implementation that base64-
encodes raw bytes. ``Sensitive[T]`` is a Python-language repr concern only.
"""
from __future__ import annotations

import base64
from typing import Any, Generic, TypeVar

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema

T = TypeVar("T")


class Sensitive(Generic[T]):
    """Wrap ``T`` so that ``__repr__``/``__str__`` never reveal the value.

    Notes
    -----
    Equality compares the wrapped values for ergonomic test usage; the wrapper
    itself does not memoize or cache its bytes anywhere outside ``self._value``.

    The Pydantic v2 integration currently specializes on ``bytes`` for the
    ``ContentBlock.content`` use-case (base64 in JSON, raw bytes in Python).
    Other ``T`` types pass through unchanged on the Python side and use
    ``str(value)`` on the JSON side; if a future plan needs another concrete
    serialization, extend ``__get_pydantic_core_schema__``.
    """

    __slots__ = ("_value",)

    def __init__(self, value: T) -> None:
        self._value = value

    def reveal(self) -> T:
        """Return the wrapped value. The only path to the underlying content."""
        return self._value

    def __repr__(self) -> str:
        type_name = type(self._value).__name__
        return f"<Sensitive: {type_name}>"

    def __str__(self) -> str:
        return self.__repr__()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Sensitive):
            return NotImplemented
        # mypy: __eq__ may compare arbitrary inner types, but the return is bool.
        return bool(self._value == other._value)

    def __hash__(self) -> int:
        # Hashable when the inner value is hashable; bytes are.
        return hash(("Sensitive", self._value))

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source: Any,  # noqa: ARG003 — Pydantic API requirement.
        handler: GetCoreSchemaHandler,  # noqa: ARG003
    ) -> core_schema.CoreSchema:
        """Return a Pydantic v2 core schema for ``Sensitive[bytes]``.

        Validation accepts:
          * an existing ``Sensitive`` (passthrough),
          * ``bytes``/``bytearray`` (wrap),
          * a ``str`` (interpret as base64 — the JSON wire format),
          * raises ``TypeError`` otherwise.

        JSON serialization emits ``base64.b64encode(value).decode("ascii")``;
        Python serialization emits the raw bytes (callers that need them call
        ``.reveal()`` instead).
        """

        def _validate(v: Any) -> "Sensitive[bytes]":
            if isinstance(v, Sensitive):
                return v
            if isinstance(v, (bytes, bytearray)):
                return Sensitive(bytes(v))
            if isinstance(v, str):
                # Inbound JSON: base64-decoded into bytes.
                try:
                    decoded = base64.b64decode(v, validate=True)
                except (ValueError, TypeError) as exc:
                    raise ValueError(f"Sensitive expects valid base64 string: {exc}") from exc
                return Sensitive(decoded)
            raise TypeError(
                f"Sensitive expects bytes, bytearray, base64 str, or Sensitive; "
                f"got {type(v).__name__}"
            )

        def _serialize_json(v: "Sensitive[bytes]") -> str:
            inner = v._value
            if not isinstance(inner, (bytes, bytearray)):
                raise TypeError(
                    f"Sensitive JSON serialization requires bytes; got {type(inner).__name__}"
                )
            return base64.b64encode(bytes(inner)).decode("ascii")

        return core_schema.no_info_plain_validator_function(
            _validate,
            serialization=core_schema.plain_serializer_function_ser_schema(
                _serialize_json,
                when_used="json",
                return_schema=core_schema.str_schema(),
            ),
            metadata={
                # Pydantic uses this hint when generating JSON Schema artifacts
                # (build_schemas.py): the wire format for Sensitive[bytes] is a
                # base64 ASCII string.
                "pydantic_js_input_core_schema": core_schema.str_schema(),
            },
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        schema: core_schema.CoreSchema,  # noqa: ARG003
        handler: Any,  # noqa: ARG003
    ) -> dict[str, Any]:
        """Return JSON Schema for Sensitive[bytes] (base64 ASCII string).

        Used by build_schemas.py to render envelope schemas. The wire format
        is byte-for-byte identical to a non-wrapped impl that base64-encodes
        raw bytes — documented in the description.
        """
        return {
            "type": "string",
            "contentEncoding": "base64",
            "description": (
                "Privacy-sensitive bytes serialized as a base64 ASCII string. "
                "Wrapped in a Sensitive[bytes] redaction container at runtime; "
                "downstream code unwraps via .reveal()."
            ),
        }


__all__ = ["Sensitive"]
