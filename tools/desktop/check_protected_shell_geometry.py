from __future__ import annotations

import difflib
from pathlib import Path
import re
import sys


PROTECTED_GEOMETRY = re.compile(
    r"\bwidth\s*:|\bheight\s*:|EdgeInsets|SizedBox\(|\bpadding\s*:|\bmargin\s*:"
)


def protected_geometry_changes(baseline: str, candidate: str) -> list[str]:
    diff = difflib.unified_diff(
        baseline.splitlines(),
        candidate.splitlines(),
        fromfile="formatted-baseline",
        tofile="formatted-candidate",
        lineterm="",
    )
    return [
        line
        for line in diff
        if re.match(r"^[+-](?![+-])", line) and PROTECTED_GEOMETRY.search(line)
    ]


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: check_protected_shell_geometry.py BASELINE CANDIDATE")
        return 2
    baseline = Path(sys.argv[1]).read_text(encoding="utf-8-sig")
    candidate = Path(sys.argv[2]).read_text(encoding="utf-8-sig")
    forbidden = protected_geometry_changes(baseline, candidate)
    if forbidden:
        print("Protected shell geometry changed:")
        print("\n".join(forbidden))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
