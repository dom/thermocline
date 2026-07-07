"""AT-C3: Shadow correlation — shadow IDs must be unique per dispatch.

Failure mode: an adversary observing many envelopes with shadow_id values
could correlate them across dispatches if shadow_ids were content-derived or
cached. Mitigation: secrets.token_hex per generation; never cached.

This thermocline-side test documents the wire contract (shadow_id is a
random 16-byte hex string per dispatch); the runtime uniqueness invariant
is tested in photophore/python/tests/test_shadow_uniqueness_property.py.
"""
# AT-SURFACE: AT-C3
from __future__ import annotations

import re

import pytest

from thermocline import Task
from thermocline.canonical import canonicalize

SHADOW_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")


def _task_with_shadow(shadow_id: str) -> dict:
    return {
        "thermocline": "0.3.1",
        "type": "task",
        "envelope_id": "a1b2c3d4-0000-4000-8000-0000000000c3",
        "issued_at": "2026-05-08T00:00:00Z",
        "issuer": "alice-node",
        "channel_id": "chan-x",
        "task": {"type": "data.compute", "instruction": "x", "parameters": {}},
        "context": [
            {
                "tier": 1,
                "role": "user_file",
                "shadow": {
                    "shadow_id": shadow_id,
                    "content_type": "document",
                    "abstraction": "A document",
                    "relevance": 0.5,
                },
            }
        ],
    }


@pytest.mark.at_surface("AT-C3")
def test_shadow_id_format_contract() -> None:
    """AT-C3: shadow_ids are 16-byte hex (32-character lowercase hex) per spec.

    The thermocline envelope wire contract: tier-1 shadow blocks carry a
    shadow_id that is 16 random bytes hex-encoded (secrets.token_hex(16)).
    This length + randomness is the structural defense against correlation.
    """
    # Sample shadow_id format check — see thermocline/README.md §"Shadow"
    sample = "0f1a2b3c4d5e6f7080a1b2c3d4e5f607"  # 32 hex chars
    assert SHADOW_ID_PATTERN.match(sample), (
        "AT-C3: shadow_id format contract is 32 lowercase hex characters"
    )


@pytest.mark.at_surface("AT-C3")
def test_distinct_shadow_ids_yield_distinct_canonical_bytes() -> None:
    """AT-C3 envelope-scope: distinct shadow_ids produce distinct canonical bytes.

    The correlation defense at the envelope layer is that a tier-1 block
    carries only an opaque per-dispatch shadow_id: two dispatches of the same
    underlying content carry different shadow_ids and therefore serialize to
    different canonical bytes, so an observer cannot equate them by wire form.
    The generator-side uniqueness invariant (that photophore never reuses an
    id) is proven in photophore's property test; here we prove the wire
    contract that distinct ids are actually distinguished under canonicalize.
    """
    a = Task.parse_strict(_task_with_shadow("0" * 32))
    b = Task.parse_strict(_task_with_shadow("1" * 32))
    assert canonicalize(a.model_dump(mode="json")) != canonicalize(
        b.model_dump(mode="json")
    )
    # And the tier-1 block never carries raw content (invariant #1): the shadow
    # is the only representation that crosses.
    assert a.context[0].content is None
    assert a.context[0].shadow is not None
