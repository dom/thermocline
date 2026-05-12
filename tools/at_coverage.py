#!/usr/bin/env python3
"""AT-C* coverage gate for thermocline (AT-C1..C6).

Globs thermocline/thermocline/python/tests/at_negative/test_at_c*.py and asserts
all six AT-C surfaces have at least one test file.
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

EXPECTED: frozenset[str] = frozenset({"AT-C1", "AT-C2", "AT-C3", "AT-C4", "AT-C5", "AT-C6"})
PATTERN = re.compile(r"^test_at_c(\d+)_")
ROOT = Path(__file__).resolve().parents[1] / "thermocline" / "python" / "tests" / "at_negative"


def main() -> int:
    if not ROOT.is_dir():
        print(f"FAIL: {ROOT} does not exist", file=sys.stderr)
        return 1
    found: set[str] = set()
    for p in sorted(ROOT.glob("test_at_*.py")):
        m = PATTERN.match(p.name.lower())
        if m:
            found.add(f"AT-C{m.group(1)}")
    missing = EXPECTED - found
    if missing:
        print(f"FAIL: missing AT-C coverage: {sorted(missing)}", file=sys.stderr)
        return 1
    print(f"ok: AT-C coverage complete ({len(found)}/6).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
