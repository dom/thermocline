"""Tests for the Pitfall 11 lint (``thermocline.scripts.check_no_json_dumps``).

The lint is wired into the default pytest run via these tests:

* ``test_lint_passes_on_current_tree`` is the live CI gate — every PR that
  introduces ``json.dumps`` (outside the allowlist) under
  ``src/thermocline/`` fails this test.
* ``test_lint_detects_synthetic_violation`` proves the scan function flags
  a realistic violation. Calling ``scan()`` with a fake root keeps the test
  fast and isolated.
* ``test_lint_command_exits_nonzero_on_violation`` exercises the
  ``main()`` entry-point against a fake root to assert the exit code
  (the wire surface CI uses).
"""
from __future__ import annotations

import sys
from pathlib import Path

from thermocline.scripts.check_no_json_dumps import (
    ALLOWLIST,
    ROOT,
    JsonDumpsVisitor,
    main,
    scan,
)

# ---------------------------------------------------------------------------
# Live gate.


def test_lint_passes_on_current_tree() -> None:
    """The committed library tree must contain zero ``json.dumps`` violations."""
    findings = scan(ROOT)
    assert findings == [], (
        f"Pitfall 11 violations found in committed tree: {findings}. "
        f"Use thermocline.canonical.canonicalize for signing input; if this "
        f"call is genuinely a non-signing artifact path (e.g. schema artifact "
        f"emission), add the file to ALLOWLIST in check_no_json_dumps.py."
    )


def test_allowlist_contents_are_stable() -> None:
    """Adding to the allowlist requires touching this test (deliberately).

    The lint allowlist has two entries by construction (build_schemas + the
    lint script itself). Future hardening may grow it; growth must be
    intentional. Bumping this assertion alongside an ALLOWLIST change is the
    gate.
    """
    assert ALLOWLIST == frozenset(
        {"scripts/build_schemas.py", "scripts/check_no_json_dumps.py"}
    )


# ---------------------------------------------------------------------------
# Synthetic-violation tests.


def test_lint_detects_synthetic_violation(tmp_path: Path) -> None:
    """``scan()`` flags a synthetic ``json.dumps`` call under a fake root."""
    violator = tmp_path / "violator.py"
    violator.write_text("import json\nx = json.dumps({'a': 1})\n", encoding="utf-8")
    findings = scan(tmp_path)
    assert any("violator.py" in str(p) for p, _, _ in findings)


def test_lint_detects_json_dump_call(tmp_path: Path) -> None:
    """``json.dump`` (the file-writing variant) is also flagged."""
    violator = tmp_path / "violator2.py"
    violator.write_text(
        "import json\n"
        "with open('x.json', 'w') as f:\n"
        "    json.dump({'a': 1}, f)\n",
        encoding="utf-8",
    )
    findings = scan(tmp_path)
    assert any("violator2.py" in str(p) for p, _, _ in findings)


def test_lint_ignores_substring_in_identifiers(tmp_path: Path) -> None:
    """A function named ``json_dumps_helper`` does not trigger; AST is precise."""
    helper = tmp_path / "helper.py"
    helper.write_text(
        "def json_dumps_helper(x):\n    return repr(x)\n\n"
        "result = json_dumps_helper({'a': 1})\n",
        encoding="utf-8",
    )
    findings = scan(tmp_path)
    assert findings == []


def test_lint_ignores_comment_mentions(tmp_path: Path) -> None:
    """``# json.dumps would not be canonical`` does not trigger."""
    commentary = tmp_path / "commentary.py"
    commentary.write_text(
        "# json.dumps would not be canonical here.\n"
        "x = 1\n",
        encoding="utf-8",
    )
    findings = scan(tmp_path)
    assert findings == []


def test_lint_respects_allowlist_entries(tmp_path: Path) -> None:
    """A violation under the same relative path as an allowlist entry is skipped."""
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "build_schemas.py").write_text(
        "import json\njson.dumps({'a': 1})\n", encoding="utf-8"
    )
    findings = scan(tmp_path)
    assert findings == []


def test_lint_ignores_dotted_directories(tmp_path: Path) -> None:
    """Hidden dirs (``.venv``, ``.tox``, ``__pycache__``) do not trigger."""
    for hidden in (".venv", "__pycache__"):
        d = tmp_path / hidden
        d.mkdir()
        (d / "x.py").write_text("import json\njson.dumps({})\n", encoding="utf-8")
    findings = scan(tmp_path)
    assert findings == []


# ---------------------------------------------------------------------------
# Entry-point exit code.


def test_main_returns_zero_on_clean_tree() -> None:
    """``main()`` against the committed library tree exits 0."""
    rc = main([])
    assert rc == 0


def test_main_returns_nonzero_on_violation(
    tmp_path: Path, monkeypatch
) -> None:
    """``main()`` against a violating fake root exits 1.

    Patches the module-level ROOT so the entry point scans the temp tree.
    """
    fake_root = tmp_path
    (fake_root / "violator.py").write_text(
        "import json\njson.dumps({'a': 1})\n", encoding="utf-8"
    )
    monkeypatch.setattr(
        "thermocline.scripts.check_no_json_dumps.ROOT", fake_root
    )
    rc = main([])
    assert rc == 1


# ---------------------------------------------------------------------------
# Visitor-direct test (proves the AST class catches the shape).


def test_visitor_records_json_dumps_call() -> None:
    """The visitor's findings list contains ``(lineno, source)`` for one call."""
    import ast

    src = "import json\nx = json.dumps({'a': 1})\n"
    tree = ast.parse(src)
    visitor = JsonDumpsVisitor()
    visitor.visit(tree)
    assert len(visitor.findings) == 1
    lineno, source = visitor.findings[0]
    assert lineno == 2
    assert "json.dumps" in source


def test_lint_detects_aliased_json_module(tmp_path: Path) -> None:
    """``import json as j`` then ``j.dumps(...)`` is flagged (Finding 12)."""
    violator = tmp_path / "aliased.py"
    violator.write_text("import json as j\nx = j.dumps({'a': 1})\n", encoding="utf-8")
    findings = scan(tmp_path)
    assert any("aliased.py" in str(p) for p, _, _ in findings)


def test_lint_detects_from_json_import_dumps(tmp_path: Path) -> None:
    """``from json import dumps`` then ``dumps(...)`` is flagged (Finding 12)."""
    violator = tmp_path / "fromimport.py"
    violator.write_text("from json import dumps\nx = dumps({'a': 1})\n", encoding="utf-8")
    findings = scan(tmp_path)
    assert any("fromimport.py" in str(p) for p, _, _ in findings)


def test_lint_detects_from_json_import_dump_aliased(tmp_path: Path) -> None:
    """``from json import dumps as d`` then ``d(...)`` is flagged (Finding 12)."""
    violator = tmp_path / "fromalias.py"
    violator.write_text("from json import dumps as d\nx = d({'a': 1})\n", encoding="utf-8")
    findings = scan(tmp_path)
    assert any("fromalias.py" in str(p) for p, _, _ in findings)


def test_lint_detects_orjson_import(tmp_path: Path) -> None:
    """Importing orjson/ujson/simplejson in library code is flagged (Finding 12)."""
    for lib in ("orjson", "ujson", "simplejson"):
        violator = tmp_path / f"uses_{lib}.py"
        violator.write_text(f"import {lib}\n", encoding="utf-8")
    findings = scan(tmp_path)
    flagged = {str(p) for p, _, _ in findings}
    for lib in ("orjson", "ujson", "simplejson"):
        assert any(f"uses_{lib}.py" in f for f in flagged), f"{lib} import not flagged"


def test_lint_detects_from_orjson_import(tmp_path: Path) -> None:
    violator = tmp_path / "from_orjson.py"
    violator.write_text("from orjson import dumps\n", encoding="utf-8")
    findings = scan(tmp_path)
    assert any("from_orjson.py" in str(p) for p, _, _ in findings)


def test_module_runs_via_dash_m() -> None:
    """``python -m thermocline.scripts.check_no_json_dumps`` exits 0 on the live tree."""
    import subprocess

    result = subprocess.run(
        [sys.executable, "-m", "thermocline.scripts.check_no_json_dumps"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"lint exited {result.returncode}; stderr:\n{result.stderr}"
    )
