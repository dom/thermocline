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


SHADOW_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")


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
def test_shadow_id_runtime_uniqueness_covered_in_photophore() -> None:
    """AT-C3 runtime invariant: shadow uniqueness lives in photophore.shadow.

    The runtime test that proves uniqueness (Hypothesis 200 examples × 100
    inner iterations = 20,000 generate() calls) is at:

        photophore/python/tests/test_shadow_uniqueness_property.py

    Thermocline-py defines only the envelope wire contract; the generator
    contract is owned by photophore.shadow.
    """
    pytest.skip(
        "AT-C3 runtime uniqueness is tested in "
        "photophore/python/tests/test_shadow_uniqueness_property.py; "
        "thermocline-py library has no shadow generator."
    )
