#!/usr/bin/env python3
"""Cross-repo AT-* coverage roll-up (17/17 union).

Reads THERMOCLINE_SUITE_ROOT (default $HOME/Projects/dom). Subprocess-invokes each
repo's tools/at_coverage.py. Exits 0 only when all three pass.
"""
from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path

SUITE_ROOT = Path(os.environ.get("THERMOCLINE_SUITE_ROOT", str(Path.home() / "Projects" / "dom")))
EXPECTED_TOTAL = 17
REPOS = [
    ("thermocline", "tools/at_coverage.py"),
    ("photophore", "tools/at_coverage.py"),
    ("seamount", "tools/at_coverage.py"),
]


def main() -> int:
    failed: list[str] = []
    for repo, tool in REPOS:
        path = SUITE_ROOT / repo / tool
        if not path.is_file():
            print(f"FAIL: {path} not found", file=sys.stderr)
            return 1
        r = subprocess.run([sys.executable, str(path)], check=False)
        if r.returncode != 0:
            failed.append(repo)
    if failed:
        print(f"FAIL: AT-* coverage incomplete in: {failed}", file=sys.stderr)
        return 1
    print(f"ok: {EXPECTED_TOTAL}/{EXPECTED_TOTAL} AT-* coverage across suite.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
