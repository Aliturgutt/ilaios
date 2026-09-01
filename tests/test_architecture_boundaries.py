"""Architecture fitness checks for monorepo dependency direction."""

from __future__ import annotations

import ast
from pathlib import Path

_FORBIDDEN_IMPORT_ROOTS = {
    "apps": frozenset({"infra"}),
    "services": frozenset({"apps", "infra"}),
    "packages": frozenset({"apps", "services", "infra"}),
    "src": frozenset({"apps", "services", "infra"}),
}


def _python_files(root: str) -> tuple[Path, ...]:
    path = Path(root)
    if not path.exists():
        return ()
    return tuple(sorted(path.rglob("*.py")))


def _import_roots(path: Path) -> frozenset[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", maxsplit=1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", maxsplit=1)[0])
    return frozenset(roots)


def test_monorepo_roots_exist() -> None:
    for root in ("apps", "services", "packages", "infra", "src", "tests"):
        assert Path(root).is_dir(), f"missing logical monorepo root: {root}"


def test_dependency_direction_has_no_forbidden_imports() -> None:
    violations: list[str] = []
    for root, forbidden in _FORBIDDEN_IMPORT_ROOTS.items():
        for path in _python_files(root):
            imported = _import_roots(path)
            invalid = sorted(imported & forbidden)
            if invalid:
                violations.append(f"{path}: {','.join(invalid)}")
    assert not violations, "forbidden monorepo dependencies:\n" + "\n".join(violations)
