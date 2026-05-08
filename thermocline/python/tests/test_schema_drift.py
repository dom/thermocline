"""Schema drift tests (D-02 acceptance).

Three tests:

1. ``test_schemas_match_models``: Running ``build_schemas --check`` against
   the committed schemas exits 0 (no drift between Pydantic models and the
   on-disk artifacts).

2. ``test_drift_simulation_signal``: Backup-modify-restore. Inject a
   synthetic property into ``task.schema.json``, run ``--check``, assert it
   exits non-zero with a diff message naming the changed file. Restore the
   original on tearDown so the suite leaves the working tree clean.

3. ``test_committed_schemas_are_valid_draft_2020_12``: Each on-disk schema
   self-validates as a Draft 2020-12 schema.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest

# tests/test_schema_drift.py -> parents[2] = thermocline/python -> ../schema = thermocline/schema
REPO_SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schema"
BUILD_CMD = [sys.executable, "-m", "thermocline.scripts.build_schemas"]
SCHEMA_NAMES = ("task", "task_result", "job", "job_result", "error")


def test_schemas_match_models() -> None:
    """Committed schemas must match the live Pydantic models."""
    result = subprocess.run([*BUILD_CMD, "--check"], capture_output=True, text=True)
    assert result.returncode == 0, (
        f"committed schemas drifted from models. stderr:\n{result.stderr}"
    )


def test_drift_simulation_signal(tmp_path: Path) -> None:  # noqa: ARG001 — pytest fixture
    """D-02 acceptance: corrupting a schema must trigger a non-zero exit + named-file diff."""
    target = REPO_SCHEMA_DIR / "task.schema.json"
    backup = target.read_text()
    try:
        # Corrupt: inject a synthetic property the live model does not emit.
        corrupted = json.loads(backup)
        # Walk to the model's properties block (the top-level $defs / $ref structure
        # nests under the inner Task definition; injecting at the top level still
        # produces a textual diff).
        corrupted.setdefault("properties", {})["__synthetic_drift_field__"] = {
            "type": "string",
        }
        target.write_text(json.dumps(corrupted, indent=2, sort_keys=True) + "\n")

        result = subprocess.run([*BUILD_CMD, "--check"], capture_output=True, text=True)
        assert result.returncode != 0, "drift simulation did not trigger non-zero exit"
        # Diff must name the corrupted file in stderr.
        assert "task.schema.json" in result.stderr, (
            f"drift output did not name the offending file. stderr:\n{result.stderr}"
        )
    finally:
        target.write_text(backup)
        # Sanity: restore worked, --check is back to clean.
        result = subprocess.run([*BUILD_CMD, "--check"], capture_output=True, text=True)
        assert result.returncode == 0, "failed to restore committed task.schema.json"


@pytest.mark.parametrize("name", SCHEMA_NAMES)
def test_committed_schemas_are_valid_draft_2020_12(name: str) -> None:
    """Each on-disk schema is a valid Draft 2020-12 JSON Schema document."""
    target = REPO_SCHEMA_DIR / f"{name}.schema.json"
    schema = json.loads(target.read_text())
    # check_schema raises if the document is not a valid schema.
    jsonschema.Draft202012Validator.check_schema(schema)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"] == f"https://thermocline.spec/schema/v0.3.1/{name}.schema.json"
