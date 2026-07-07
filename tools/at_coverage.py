#!/usr/bin/env python3
"""AT-C* coverage gate for thermocline (AT-C1..C6).

Behavioral gate (0.4.0): instead of trusting filename existence, this AST-parses
the tests under ``thermocline/python/tests/at_negative/`` and requires that every
AT-C surface (AT-C1..AT-C6) has at least one ``@pytest.mark.at_surface("AT-Cn")``
test that is NOT unconditionally skipped. A test that calls ``pytest.skip(...)``
at the top of its body (or carries ``@pytest.mark.skip``) does not count toward
coverage, so a surface cannot be "covered" by a stub that never asserts anything.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

EXPECTED: frozenset[str] = frozenset({"AT-C1", "AT-C2", "AT-C3", "AT-C4", "AT-C5", "AT-C6"})
ROOT = Path(__file__).resolve().parents[1] / "thermocline" / "python" / "tests" / "at_negative"


def _at_surface_name(decorator: ast.expr) -> str | None:
    """Return the surface string from an ``@pytest.mark.at_surface("AT-Cn")``."""
    if not isinstance(decorator, ast.Call):
        return None
    func = decorator.func
    if (
        isinstance(func, ast.Attribute)
        and func.attr == "at_surface"
        and decorator.args
        and isinstance(decorator.args[0], ast.Constant)
        and isinstance(decorator.args[0].value, str)
    ):
        return decorator.args[0].value
    return None


def _is_skip_marker(decorator: ast.expr) -> bool:
    """True for ``@pytest.mark.skip`` / ``@pytest.mark.skipif``."""
    node = decorator.func if isinstance(decorator, ast.Call) else decorator
    return isinstance(node, ast.Attribute) and node.attr in {"skip", "skipif"}


def _body_unconditionally_skips(func: ast.FunctionDef) -> bool:
    """True if the first real statement is a bare ``pytest.skip(...)`` call."""
    for stmt in func.body:
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
            # Leading docstring; keep scanning.
            continue
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            target = stmt.value.func
            if isinstance(target, ast.Attribute) and target.attr == "skip":
                return True
        # First non-docstring, non-skip statement -> not an unconditional skip.
        return False
    return False


def _covered_surfaces() -> set[str]:
    found: set[str] = set()
    for path in sorted(ROOT.glob("test_at_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            surfaces = {
                s for d in node.decorator_list if (s := _at_surface_name(d)) is not None
            }
            if not surfaces:
                continue
            if any(_is_skip_marker(d) for d in node.decorator_list):
                continue
            if _body_unconditionally_skips(node):
                continue
            found.update(surfaces)
    return found


def main() -> int:
    if not ROOT.is_dir():
        print(f"FAIL: {ROOT} does not exist", file=sys.stderr)
        return 1
    found = _covered_surfaces()
    missing = EXPECTED - found
    if missing:
        print(
            f"FAIL: AT-C surfaces without a non-skipped at_surface test: "
            f"{sorted(missing)}",
            file=sys.stderr,
        )
        return 1
    print(
        f"ok: AT-C coverage complete ({len(EXPECTED & found)}/6 surfaces have a "
        "non-skipped behavioral test).",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
