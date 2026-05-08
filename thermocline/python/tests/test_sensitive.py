"""Tests for the ``Sensitive[T]`` redaction wrapper (D-03 / Pitfall 4).

Covers:
* redacting __repr__/__str__,
* .reveal() returns the original bytes,
* equality across wrappers,
* hashability,
* validation acceptance (bytes, bytearray, base64 str, Sensitive),
* validation rejection (other types, malformed base64),
* JSON round-trip via a small Pydantic model: bytes -> base64 string -> bytes.
"""
from __future__ import annotations

import base64

import pytest
from pydantic import BaseModel, ConfigDict

from thermocline.sensitive import Sensitive


# ---------------------------------------------------------------------------
# Pure-Python wrapper behavior.


def test_repr_redacts_bytes() -> None:
    secret = b"top-secret-payload-bytes-do-not-leak"
    wrapped = Sensitive(secret)
    rendered = repr(wrapped)
    assert rendered == "<Sensitive: bytes>"
    # Belt and suspenders: the secret bytes must not appear in the repr.
    assert "secret" not in rendered
    assert "payload" not in rendered


def test_str_redacts_bytes() -> None:
    wrapped = Sensitive(b"another-secret")
    rendered = str(wrapped)
    assert rendered == "<Sensitive: bytes>"
    assert "secret" not in rendered


def test_reveal_returns_original_bytes() -> None:
    payload = b"\x00\x01\x02 important \xff"
    wrapped = Sensitive(payload)
    assert wrapped.reveal() == payload
    assert wrapped.reveal() is payload  # no copy


def test_equality_compares_wrapped_value() -> None:
    a = Sensitive(b"same")
    b = Sensitive(b"same")
    c = Sensitive(b"different")
    assert a == b
    assert a != c
    # Equality with a non-Sensitive returns NotImplemented, so Python falls
    # back to default behavior (False).
    assert a != b"same"


def test_hashable_when_inner_value_hashable() -> None:
    a = Sensitive(b"hashme")
    b = Sensitive(b"hashme")
    assert hash(a) == hash(b)
    s = {a}
    assert b in s


# ---------------------------------------------------------------------------
# Pydantic v2 integration: validation, serialization, round-trip.


class _SensitiveBlock(BaseModel):
    """Minimal model that types a single ``Sensitive[bytes]`` field."""

    model_config = ConfigDict(extra="forbid")

    content: Sensitive[bytes]


def test_validate_from_bytes_wraps() -> None:
    block = _SensitiveBlock(content=b"hello")  # type: ignore[arg-type]
    assert isinstance(block.content, Sensitive)
    assert block.content.reveal() == b"hello"


def test_validate_from_bytearray_wraps_and_copies() -> None:
    raw = bytearray(b"mutable")
    block = _SensitiveBlock(content=raw)  # type: ignore[arg-type]
    assert block.content.reveal() == b"mutable"
    raw[0] = 0  # mutate source AFTER construction
    # The Sensitive wrapper holds an immutable bytes copy.
    assert block.content.reveal() == b"mutable"


def test_validate_from_base64_string() -> None:
    encoded = base64.b64encode(b"json-incoming").decode("ascii")
    block = _SensitiveBlock.model_validate({"content": encoded})
    assert block.content.reveal() == b"json-incoming"


def test_validate_passes_through_existing_sensitive() -> None:
    inner = Sensitive(b"already-wrapped")
    block = _SensitiveBlock(content=inner)
    # Same object (passthrough), not a re-wrap.
    assert block.content is inner


def test_validate_rejects_unknown_type() -> None:
    with pytest.raises(Exception):  # Pydantic surfaces as ValidationError
        _SensitiveBlock(content=42)  # type: ignore[arg-type]


def test_validate_rejects_invalid_base64() -> None:
    # JSON path with malformed base64.
    with pytest.raises(Exception):  # Pydantic ValidationError wrapping ValueError
        _SensitiveBlock.model_validate({"content": "this is not !! valid base64 ??"})


def test_json_serialize_produces_base64_string() -> None:
    block = _SensitiveBlock(content=b"\x00\x01\x02secret\xff")  # type: ignore[arg-type]
    payload = block.model_dump_json()
    # The JSON wire format wraps the base64 string in a "content" field.
    expected = base64.b64encode(b"\x00\x01\x02secret\xff").decode("ascii")
    assert f'"{expected}"' in payload
    # And the raw secret bytes must NOT appear directly.
    assert "secret" not in payload  # base64 of "secret" is not the literal "secret"


def test_json_round_trip_preserves_bytes() -> None:
    original_bytes = b"\x00\x01\x02 round-trip \xff\xfe"
    block = _SensitiveBlock(content=original_bytes)  # type: ignore[arg-type]
    payload = block.model_dump_json()
    rebuilt = _SensitiveBlock.model_validate_json(payload)
    assert rebuilt.content.reveal() == original_bytes
    assert rebuilt == block


def test_repr_of_model_does_not_leak_bytes() -> None:
    """Pitfall 4: ``repr(model)`` MUST NOT contain the underlying content bytes."""
    secret = b"DO-NOT-LEAK-THIS-VALUE-XYZZY"
    block = _SensitiveBlock(content=secret)  # type: ignore[arg-type]
    rendered = repr(block)
    assert "DO-NOT-LEAK-THIS-VALUE-XYZZY" not in rendered
    assert "<Sensitive: bytes>" in rendered
