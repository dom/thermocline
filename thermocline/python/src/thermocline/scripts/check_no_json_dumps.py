"""Pitfall 11 lint: forbid ``json.dumps`` in library code outside the allowlist.

Signing input MUST go through :func:`thermocline.canonical.canonicalize`
(RFC 8785). The Python stdlib ``json`` module emits non-canonical output
(``sort_keys`` defaults to False, separators include whitespace) — signatures
computed over its output do not verify across implementations whose map
iteration order differs. This script walks ``src/thermocline/`` and flags
every Call node whose target is ``json.dumps`` or ``json.dump``.

Allowlist (explicit, append-only):

* ``src/thermocline/scripts/build_schemas.py`` — committed schema artifacts
  use ``json.dumps(..., indent=2, sort_keys=True)`` for human-readable diffs.
  Schemas are NOT signing input; this is dev/CI tooling only.
* ``src/thermocline/scripts/check_no_json_dumps.py`` — this file (the lint
  cannot exempt itself from a substring check; AST-based analysis is precise
  enough to ignore the docstring mentions).

Usage::

    thermocline-check-no-json-dumps               # console script
    python -m thermocline.scripts.check_no_json_dumps

Exits 0 on success, 1 on any violation (with offending file:line printed to
stderr).
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

__all__ = ["scan", "main", "ALLOWLIST", "ROOT", "JsonDumpsVisitor"]


# ``parents[2]`` from ``src/thermocline/scripts/check_no_json_dumps.py``
# resolves to ``src/thermocline/`` — the library root we walk.
ROOT: Path = Path(__file__).resolve().parents[1]

# Allowlist entries are module-relative POSIX paths (matched by
# ``Path.relative_to(ROOT).as_posix()`` to remain stable across platforms).
ALLOWLIST: frozenset[str] = frozenset(
    {
        "scripts/build_schemas.py",
        "scripts/check_no_json_dumps.py",
    }
)


#: Third-party JSON encoders that emit non-canonical output. Importing any of
#: them in library code is a Pitfall 11 violation the same way ``json.dumps``
#: is: signing input MUST funnel through ``thermocline.canonical.canonicalize``.
_FORBIDDEN_JSON_LIBS: frozenset[str] = frozenset({"orjson", "ujson", "simplejson"})


class JsonDumpsVisitor(ast.NodeVisitor):
    """AST visitor that records every ``json.dumps`` / ``json.dump`` call.

    Substring-based checks falsely flag ``# json.dumps`` in comments and
    ``not_json_dumps_helper`` in identifiers. AST analysis matches Call
    nodes whose function is the ``Attribute(Name(id='json'), attr=...)``
    shape, which is precise.
    """

    def __init__(self) -> None:
        self.findings: list[tuple[int, str]] = []

    def visit_Call(self, node: ast.Call) -> None:
        target = node.func
        if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
            if target.value.id == "json" and target.attr in {"dumps", "dump"}:
                self.findings.append((node.lineno, ast.unparse(node)))
        self.generic_visit(node)


def _import_findings(tree: ast.AST) -> list[tuple[int, str]]:
    """Flag lint-bypassing import shapes (Finding 12).

    Catches what a plain ``json.dumps`` attribute match misses:

    * ``import json as j`` followed by ``j.dumps(...)`` (aliased module).
    * ``from json import dumps`` / ``... as d`` followed by a bare
      ``dumps(...)`` / ``d(...)`` call.
    * ``import orjson`` / ``ujson`` / ``simplejson`` (or ``from ... import``):
      non-canonical encoders are forbidden in library code outright.
    """
    findings: list[tuple[int, str]] = []
    json_module_aliases: set[str] = set()  # names bound to stdlib json (asname)
    json_func_names: set[str] = set()  # names bound to json.dumps / json.dump

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top in _FORBIDDEN_JSON_LIBS:
                    findings.append((node.lineno, ast.unparse(node)))
                if alias.name == "json" and alias.asname and alias.asname != "json":
                    json_module_aliases.add(alias.asname)
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if node.module == "json":
                for alias in node.names:
                    if alias.name in {"dumps", "dump"}:
                        json_func_names.add(alias.asname or alias.name)
            elif root in _FORBIDDEN_JSON_LIBS:
                findings.append((node.lineno, ast.unparse(node)))

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and isinstance(func.value, ast.Name)
            and func.value.id in json_module_aliases
            and func.attr in {"dumps", "dump"}
        ):
            findings.append((node.lineno, ast.unparse(node)))
        elif isinstance(func, ast.Name) and func.id in json_func_names:
            findings.append((node.lineno, ast.unparse(node)))
    return findings


def scan(path: Path) -> list[tuple[Path, int, str]]:
    """Walk ``path`` recursively; return ``(relpath, lineno, src)`` for each violation.

    Files matching :data:`ALLOWLIST` (relative to ``path``) are skipped.
    Hidden directories and ``__pycache__`` (any path component starting with
    ``.`` or equal to ``__pycache__``) are skipped to keep the scan
    deterministic across environments.
    """
    findings: list[tuple[Path, int, str]] = []
    for py in sorted(path.rglob("*.py")):
        rel = py.relative_to(path)
        rel_posix = rel.as_posix()
        if rel_posix in ALLOWLIST:
            continue
        if any(part.startswith(".") or part == "__pycache__" for part in rel.parts):
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        except SyntaxError:
            # Malformed source files are surfaced by ruff/mypy; the lint stays
            # focused on its single concern.
            continue
        visitor = JsonDumpsVisitor()
        visitor.visit(tree)
        merged: list[tuple[int, str]] = [*visitor.findings, *_import_findings(tree)]
        seen: set[tuple[int, str]] = set()
        for lineno, src in merged:
            if (lineno, src) in seen:
                continue
            seen.add((lineno, src))
            findings.append((rel, lineno, src))
    return findings


def main(argv: list[str] | None = None) -> int:
    """Entry point for ``thermocline-check-no-json-dumps``.

    Returns 0 on a clean tree, 1 with violations printed to stderr.
    """
    _ = argv  # Reserved for future flags; kept as a stable entry-point signature.
    findings = scan(ROOT)
    if findings:
        print(
            "Pitfall 11 violation: json.dumps used in library code outside allowlist.",
            file=sys.stderr,
        )
        print("", file=sys.stderr)
        for path, lineno, src in findings:
            print(f"  {path}:{lineno}: {src}", file=sys.stderr)
        print("", file=sys.stderr)
        print(
            "Use thermocline.canonical.canonicalize for signing input. "
            "json.dumps emits non-canonical output and cannot be used as a "
            "signing input without breaking signature verification across "
            "implementations.",
            file=sys.stderr,
        )
        return 1
    print("ok: no json.dumps found in library code outside allowlist.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
