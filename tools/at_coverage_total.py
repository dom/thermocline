#!/usr/bin/env python3
"""Cross-repo AT-* coverage roll-up (17/17 union).

By DEFAULT this runs only the in-repo ``thermocline`` coverage gate. It does
NOT reach out and execute ``tools/at_coverage.py`` scripts from sibling repos
sitting under ``$HOME/Projects/dom``, because subprocess-executing whatever
happens to be on disk at a fixed home path is a footgun (it runs arbitrary
code from an unpinned location on any machine that has those directories).

The full cross-repo roll-up is opt-in: set ``AT_COVERAGE_TOTAL_CROSS_REPO=1``
(the release coordinator ``scripts/tag-v0.1.0.sh`` does this deliberately when
it has verified sibling checkouts). Even then, each candidate script must be a
regular file under the configured ``THERMOCLINE_SUITE_ROOT`` or it is skipped.
"""
from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path

SUITE_ROOT = Path(
    os.environ.get("THERMOCLINE_SUITE_ROOT", str(Path.home() / "Projects" / "dom"))
)
CROSS_REPO = os.environ.get("AT_COVERAGE_TOTAL_CROSS_REPO", "0") == "1"
EXPECTED_TOTAL = 17
_LOCAL_AT_COVERAGE = Path(__file__).resolve().parent / "at_coverage.py"
SIBLING_REPOS = [
    ("photophore", "tools/at_coverage.py"),
    ("seamount", "tools/at_coverage.py"),
]


def _run(path: Path) -> int:
    return subprocess.run([sys.executable, str(path)], check=False).returncode


def main() -> int:
    # Always run the local thermocline gate (it lives next to this script, a
    # pinned in-repo path, not a fixed home directory).
    if _run(_LOCAL_AT_COVERAGE) != 0:
        print("FAIL: thermocline AT-C coverage incomplete", file=sys.stderr)
        return 1

    if not CROSS_REPO:
        print(
            "ok: thermocline AT-C coverage complete. Cross-repo 17/17 roll-up "
            "skipped (set AT_COVERAGE_TOTAL_CROSS_REPO=1 to include sibling "
            "repos under THERMOCLINE_SUITE_ROOT).",
            file=sys.stderr,
        )
        return 0

    failed: list[str] = []
    for repo, tool in SIBLING_REPOS:
        path = SUITE_ROOT / repo / tool
        if not path.is_file():
            print(f"FAIL: {path} not found (cross-repo mode)", file=sys.stderr)
            return 1
        if _run(path) != 0:
            failed.append(repo)
    if failed:
        print(f"FAIL: AT-* coverage incomplete in: {failed}", file=sys.stderr)
        return 1
    print(
        f"ok: {EXPECTED_TOTAL}/{EXPECTED_TOTAL} AT-* coverage across suite.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
