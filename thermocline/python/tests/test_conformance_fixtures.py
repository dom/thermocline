"""Conformance fixture harness — Phase 1 slice (D-04 / THERMO-06).

This harness validates the conformance corpus that any v0.3.1-compliant
implementation can run against:

* The three-level manifest (top-level + valid/MANIFEST.yaml + invalid/MANIFEST.yaml)
  is well-formed and references real files.
* Each valid (request, response) pair parses through ``Task.parse_strict`` /
  ``TaskResult.parse_strict`` AND validates against the JSON Schema artifacts
  under ``thermocline/schema/``.
* The ``invalid/`` directory covers all six Thermocline AT-C surfaces (AT-C1..AT-C6).
* Each invalid fixture is well-formed JSON (parseable) so future phases can
  load it without a syntax-checking step.
* For surfaces wired in Phase 1 (AT-C5 / AT-C6), the actual error code raised
  by ``Task.parse_strict`` matches the manifest's ``expect_error_code``.

Surfaces tagged ``phase: 2+`` in the manifest are committed for Photophore /
Seamount tests to wire against — Phase 1 validates them structurally only.

The Phase 4 conformance harness (Plan 04-04) will extend this to walk every
manifest entry and produce a unified pass/fail report; the manifest schema is
designed to support that extension without restructuring.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
import pytest
import yaml
from pydantic import ValidationError

from thermocline.envelope import Task, TaskResult
from thermocline.errors import UnsupportedVersionError

# ---------------------------------------------------------------------------
# Path resolution. Tests live at thermocline/python/tests/, so two parents up
# is thermocline/, which contains conformance/ and schema/.

_TESTS_DIR = Path(__file__).resolve().parent
_THERMOCLINE_DIR = _TESTS_DIR.parents[1]
CONFORMANCE_DIR = _THERMOCLINE_DIR / "conformance"
SCHEMA_DIR = _THERMOCLINE_DIR / "schema"

EXPECTED_AT_C_SURFACES = {"AT-C1", "AT-C2", "AT-C3", "AT-C4", "AT-C5", "AT-C6"}


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text())


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


# ---------------------------------------------------------------------------
# Top-level manifest.


def test_top_level_manifest_well_formed() -> None:
    manifest = _load_yaml(CONFORMANCE_DIR / "MANIFEST.yaml")
    assert manifest["schema_version"] == "0.3.1"
    assert "phases_covered" in manifest
    # Phase 1 must declare it covers the AT-C envelope-side surfaces.
    phases = manifest["phases_covered"]
    phase1 = next(p for p in phases if p["phase"] == 1)
    assert EXPECTED_AT_C_SURFACES.issubset(set(phase1["surfaces"]))


# ---------------------------------------------------------------------------
# Valid pairs — each request/response parses + validates against JSON Schema.


def test_valid_manifest_well_formed() -> None:
    manifest = _load_yaml(CONFORMANCE_DIR / "valid" / "MANIFEST.yaml")
    assert "pairs" in manifest
    assert len(manifest["pairs"]) >= 1
    for entry in manifest["pairs"]:
        for required in ("id", "request", "response"):
            assert required in entry, f"valid manifest entry missing {required!r}: {entry}"


def test_valid_pairs_parse_and_validate_against_schema() -> None:
    manifest = _load_yaml(CONFORMANCE_DIR / "valid" / "MANIFEST.yaml")
    task_schema = _load_json(SCHEMA_DIR / "task.schema.json")
    task_result_schema = _load_json(SCHEMA_DIR / "task_result.schema.json")
    task_validator = jsonschema.Draft202012Validator(task_schema)
    task_result_validator = jsonschema.Draft202012Validator(task_result_schema)

    for pair in manifest["pairs"]:
        req_path = CONFORMANCE_DIR / "valid" / pair["request"]
        resp_path = CONFORMANCE_DIR / "valid" / pair["response"]
        assert req_path.exists(), f"valid request fixture missing: {req_path}"
        assert resp_path.exists(), f"valid response fixture missing: {resp_path}"

        req = _load_json(req_path)
        resp = _load_json(resp_path)

        # Pydantic v2 strict parse — must succeed.
        Task.parse_strict(req)
        TaskResult.parse_strict(resp)

        # JSON Schema validation — must succeed.
        task_validator.validate(req)
        task_result_validator.validate(resp)


# ---------------------------------------------------------------------------
# Invalid manifest — surface coverage + structural well-formedness.


def test_invalid_manifest_covers_all_at_c_surfaces() -> None:
    manifest = _load_yaml(CONFORMANCE_DIR / "invalid" / "MANIFEST.yaml")
    surfaces = {entry["surface"] for entry in manifest["fixtures"]}
    missing = EXPECTED_AT_C_SURFACES - surfaces
    assert not missing, f"invalid manifest is missing AT-C surfaces: {missing}"


def test_invalid_manifest_has_six_surface_entries() -> None:
    """Tight upper bound — exactly six AT-C entries in Phase 1, no fewer, no extras yet."""
    manifest = _load_yaml(CONFORMANCE_DIR / "invalid" / "MANIFEST.yaml")
    at_c_entries = [e for e in manifest["fixtures"] if e["surface"].startswith("AT-C")]
    assert len(at_c_entries) == 6, (
        f"expected exactly 6 AT-C entries in Phase 1; found {len(at_c_entries)}"
    )


def test_invalid_manifest_entries_have_required_fields() -> None:
    manifest = _load_yaml(CONFORMANCE_DIR / "invalid" / "MANIFEST.yaml")
    for entry in manifest["fixtures"]:
        for required in ("fixture", "surface", "description", "expect_error_code"):
            assert required in entry, (
                f"invalid manifest entry for {entry.get('surface', '?')} missing {required!r}"
            )


def test_invalid_fixtures_referenced_by_manifest_exist_and_parse() -> None:
    manifest = _load_yaml(CONFORMANCE_DIR / "invalid" / "MANIFEST.yaml")
    for entry in manifest["fixtures"]:
        path = CONFORMANCE_DIR / "invalid" / entry["fixture"]
        assert path.exists(), f"manifest references missing fixture: {path}"
        # Must be parseable as JSON (well-formed). Phase 1 does NOT require
        # every fixture to also pass Pydantic — surfaces tagged phase>=2 are
        # exercised by future phases, and several are deliberately
        # *non*-envelope-shaped fixture documents.
        _load_json(path)


def test_invalid_fixture_count_covers_all_at_c_surfaces() -> None:
    """Filesystem-side check: at least one AT-C JSON fixture per surface AT-C1..AT-C6.

    Phase 4 added AT-C5-result-policy-modified.json as the canonical AT-C5
    fixture and retained the misnamed AT-C5-unsupported-version.json for
    backward compatibility (it actually tests THERMO-07, not AT-C5 — see
    Plan 04-01 SUMMARY). Total count may grow over time as Phase 4+
    fixtures land alongside the originals; the load-bearing assertion is
    "every AT-C<n> surface has at least one fixture."
    """
    import re
    files = sorted((CONFORMANCE_DIR / "invalid").glob("AT-C*.json"))
    surfaces_found: set[str] = set()
    for f in files:
        m = re.match(r"^AT-(C\d)-", f.name)
        if m:
            surfaces_found.add(f"AT-{m.group(1)}")
    expected = {"AT-C1", "AT-C2", "AT-C3", "AT-C4", "AT-C5", "AT-C6"}
    assert surfaces_found >= expected, (
        f"AT-C surface coverage incomplete: missing {expected - surfaces_found}; "
        f"found files: {[f.name for f in files]}"
    )


# ---------------------------------------------------------------------------
# Phase-1-wired surfaces: the manifest's expect_error_code must match what the
# Phase 1 implementation actually raises. Phase 2+ surfaces are wired in their
# respective phases.


@pytest.mark.parametrize(
    "surface,expected_code",
    [
        ("AT-C5", "UNSUPPORTED_VERSION"),
        ("AT-C6", "EXTRA_FIELD_FORBIDDEN"),
    ],
)
def test_phase1_wired_invalid_fixtures_raise_expected_errors(
    surface: str, expected_code: str
) -> None:
    """Manifest expect_error_code MUST match the actual Phase 1 error path.

    AT-C5: ``Task.parse_strict`` raises :class:`UnsupportedVersionError` with
    ``code="UNSUPPORTED_VERSION"`` for any thermocline value not in
    SUPPORTED_VERSIONS.

    AT-C6: ``Task.parse_strict`` raises Pydantic ``ValidationError`` whose
    error type is ``extra_forbidden``. The manifest's
    ``expect_error_code="EXTRA_FIELD_FORBIDDEN"`` is the public name we expose
    for that surface (the harness translates Pydantic's internal type name).
    """
    manifest = _load_yaml(CONFORMANCE_DIR / "invalid" / "MANIFEST.yaml")
    entry = next(e for e in manifest["fixtures"] if e["surface"] == surface)
    assert entry["expect_error_code"] == expected_code, (
        f"manifest expect_error_code drifted from test expectation for {surface}: "
        f"manifest says {entry['expect_error_code']!r}, test expects {expected_code!r}"
    )

    fixture = _load_json(CONFORMANCE_DIR / "invalid" / entry["fixture"])

    if surface == "AT-C5":
        with pytest.raises(UnsupportedVersionError) as excinfo:
            Task.parse_strict(fixture)
        assert excinfo.value.code == "UNSUPPORTED_VERSION"
        # The offending version must appear somewhere in the diagnostic.
        assert "0.0.1" in str(excinfo.value)

    elif surface == "AT-C6":
        with pytest.raises(ValidationError) as excinfo:
            Task.parse_strict(fixture)
        # Pydantic v2 reports extra-field rejection with type 'extra_forbidden'.
        # We assert on the structured error stream rather than message text so
        # this stays stable across Pydantic micro-versions.
        types = {err.get("type") for err in excinfo.value.errors()}
        assert "extra_forbidden" in types, (
            f"expected at least one 'extra_forbidden' error; got types={types}"
        )


def test_phase1_unwired_surfaces_are_phase_tagged() -> None:
    """Surfaces not wired in Phase 1 must carry ``phase: 2`` (or later).

    This is the discipline that lets future phases find their work — every
    structurally-only fixture in Phase 1 has a ``phase`` field pointing at the
    phase that will wire it.
    """
    manifest = _load_yaml(CONFORMANCE_DIR / "invalid" / "MANIFEST.yaml")
    phase1_wired = {"AT-C4", "AT-C5", "AT-C6"}  # AT-C4 is wired in test_identity_dispatch
    for entry in manifest["fixtures"]:
        surface = entry["surface"]
        if surface in phase1_wired:
            continue
        assert entry.get("phase", 1) >= 2, (
            f"surface {surface} is not Phase-1-wired and must declare ``phase: 2`` "
            f"(or later) in the manifest; got {entry.get('phase')!r}"
        )
