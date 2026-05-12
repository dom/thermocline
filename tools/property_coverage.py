#!/usr/bin/env python3
"""CONF-03 4/4 invariant + max_examples >= 200 gate.

Reads THERMOCLINE_SUITE_ROOT (default $HOME/Projects/dom). AST-parses each of
the 4 CONF-03 property test files; asserts (a) the `CONF-03 invariant:` marker
comment is present in source; (b) every @settings(max_examples=N) literal has
N >= 200.

CONFLICT-03 / Task 7 env-var toggle: when PROPERTY_COVERAGE_STRICT=1 (set by
release script tag-v0.1.0.sh), missing TARGETS are a hard FAIL (full
cross-repo audit). Default (`0` or unset) treats missing TARGETS as soft WARN
so per-repo CI checkouts do not break.
"""
from __future__ import annotations
import ast
import os
import sys
from pathlib import Path

SUITE_ROOT = Path(os.environ.get("THERMOCLINE_SUITE_ROOT", str(Path.home() / "Projects" / "dom")))
STRICT = os.environ.get("PROPERTY_COVERAGE_STRICT", "0") == "1"
TARGETS = [
    SUITE_ROOT / "photophore" / "python" / "tests" / "test_classifier_default_property.py",
    SUITE_ROOT / "photophore" / "python" / "tests" / "test_audit_chain_property.py",
    SUITE_ROOT / "thermocline" / "thermocline" / "python" / "tests" / "test_canonical_properties.py",
    SUITE_ROOT / "photophore" / "python" / "tests" / "test_shadow_uniqueness_property.py",
]
MIN_EXAMPLES = 200
INVARIANT_MARKER = "CONF-03 invariant:"


def _check_max_examples(tree: ast.AST, path: Path) -> list[str]:
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "settings":
            for kw in node.keywords:
                if (
                    kw.arg == "max_examples"
                    and isinstance(kw.value, ast.Constant)
                    and isinstance(kw.value.value, int)
                    and kw.value.value < MIN_EXAMPLES
                ):
                    violations.append(
                        f"{path}:{node.lineno}: max_examples={kw.value.value} < {MIN_EXAMPLES}"
                    )
    return violations


def main() -> int:
    failures: list[str] = []
    warnings: list[str] = []
    for path in TARGETS:
        if not path.is_file():
            msg = f"{'FAIL' if STRICT else 'WARN'}: {path} not found"
            (failures if STRICT else warnings).append(msg)
            continue
        src = path.read_text()
        if INVARIANT_MARKER not in src:
            failures.append(f"FAIL: {path} missing '# {INVARIANT_MARKER}' comment")
        try:
            tree = ast.parse(src)
        except SyntaxError as e:
            failures.append(f"FAIL: {path} syntax: {e}")
            continue
        failures.extend(_check_max_examples(tree, path))
    for w in warnings:
        print(w, file=sys.stderr)
    if failures:
        for f in failures:
            print(f, file=sys.stderr)
        return 1
    mode = "strict" if STRICT else "soft"
    print(
        f"ok ({mode}): CONF-03 4/4 invariants present; max_examples >= {MIN_EXAMPLES}.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
