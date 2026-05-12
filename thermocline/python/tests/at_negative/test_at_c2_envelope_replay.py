"""AT-C2: Envelope replay — replayed envelope_id must be rejected.

Failure mode: an envelope previously processed (audit-logged) MUST be rejected
on second arrival. Mitigation in v0.1: receiver's audit log dedupe on envelope_id.
The dedupe layer itself is a Photophore concern (AT-A1 covers the channel side);
this thermocline-side test asserts the fixture is well-formed and the spec
contract is documented.
"""
# AT-SURFACE: AT-C2
from __future__ import annotations

import json
from pathlib import Path

import pytest

_CONFORMANCE = Path(__file__).resolve().parents[3] / "conformance"


@pytest.mark.at_surface("AT-C2")
def test_envelope_replay_fixture_well_formed() -> None:
    """AT-C2 fixture: replay envelope_pair has identical envelope_id across first/replay.

    The cross-impl conformance contract: any compliant impl reads the fixture,
    dispatches first_dispatch (audit-logged), attempts replay (must reject).
    """
    fixture = _CONFORMANCE / "invalid" / "AT-C1-replayed-envelope.json"
    # Note (Pitfall 3): the existing fixture is filed under AT-C1 because Phase 1
    # naming drift; the JSON content tests AT-C2 (replay). The MANIFEST.yaml
    # encodes the authoritative mapping. We accept this filename mismatch and
    # surface it as a documented Phase 4 known limitation.
    data = json.loads(fixture.read_text())
    assert "envelope_pair" in data, "AT-C2: fixture must carry envelope_pair"
    pair = data["envelope_pair"]
    first = pair["first_dispatch"]
    replay = pair["replay"]
    assert first["envelope_id"] == replay["envelope_id"], (
        "AT-C2: replay must use the same envelope_id as first_dispatch"
    )


@pytest.mark.at_surface("AT-C2")
def test_envelope_replay_dedupe_documented_as_phase2_concern() -> None:
    """AT-C2 dedupe layer: documented for Photophore audit-log dedupe (MAY-clause).

    The thermocline spec defines the surface (replay rejection); the actual
    dedupe implementation lives in Photophore (AT-A1) per the spec division.
    Thermocline-py library code has no per-channel state to dedupe against.
    """
    pytest.skip(
        "AT-C2 dedupe is implemented in photophore.dispatch (see AT-A1 / "
        "test_e2e_at_a1_replay.py). v0.1 spec defers dedupe to the policy "
        "engine; thermocline-py library code has no per-channel state."
    )
