"""AST-backed repository intelligence for the canonical ILAIOS code path."""

from __future__ import annotations

import ast
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import tomllib

from src.code_intelligence.models import (
    Certainty,
    DependencyEdge,
    FileKind,
    ImpactAnalysis,
    Language,
    RepositorySnapshot,
    SourceFileRecord,
    SourceLocation,
    SymbolRecord,
    SymbolType,
    TestMapping,
)
from src.code_intelligence.source_file_analyzer import SourceFileAnalyzer

_IGNORED_DIRECTORIES = frozenset(
    {".git", ".mypy_cache", ".pytest_cache", ".ruff_cache", "__pycache__", "build", "dist", "venv"}
)
_MANIFEST_NAMES = frozenset({"pyproject.toml", "package.json", "pubspec.yaml"})
_CONFIG_SUFFIXES = (".yaml", ".yml", ".toml", ".ini", ".cfg", ".json")
_HTTP_METHODS = frozenset({"get", "post", "put", "patch", "delete", "options", "head"})


class RepositoryAnalysisError(ValueError):
    """Repository intelligence input is invalid or unsafe."""


@dataclass(frozen=True, slots=True)
class _PythonFacts:
    symbols: tuple[SymbolRecord, ...]
    imports: tuple[str, ...]
    routes: tuple[str, ...]
    schemas: tuple[str, ...]


class RepositoryAnalyzer:
    """Build deterministic snapshots without claiming unsupported semantics."""

    def __init__(self, root: Path, *, max_files: int = 20_000) -> None:
        self._root = root.resolve()
        if not self._root.is_dir() or self._root.is_symlink():
            raise RepositoryAnalysisError("repository root must be a regular directory")
        if max_files < 1:
            raise ValueError("max_files must be positive")
        self._max_files = max_files

    def snapshot(self) -> RepositorySnapshot:
        paths = self._discover()
        module_paths = {
            module: path.relative_to(self._root).as_posix()
            for path in paths
            if path.suffix == ".py"
            for module in [_module_name(path.relative_to(self._root))]
        }
        files: list[SourceFileRecord] = []
        symbols: list[SymbolRecord] = []
        dependencies: list[DependencyEdge] = []
        routes: list[str] = []
        schemas: list[str] = []
        manifests: list[str] = []
        configurations: list[str] = []
        unknowns: list[str] = []
        python_imports: dict[str, tuple[str, ...]] = {}
        all_relative_paths = {path.relative_to(self._root).as_posix() for path in paths}

        for path in paths:
            relative = path.relative_to(self._root).as_posix()
            language = _language(path)
            kind = _file_kind(path, relative)
            module = _module_name(path.relative_to(self._root)) if language is Language.PYTHON else None
            package = relative.split("/", 1)[0] if "/" in relative else None
            generated = _generated(path)
            files.append(
                SourceFileRecord(
                    relative,
                    language,
                    FileKind.GENERATED if generated else kind,
                    module,
                    package,
                    generated,
                    Certainty.INFERRED if generated else Certainty.KNOWN,
                )
            )
            if path.name in _MANIFEST_NAMES:
                manifests.append(relative)
                dependencies.extend(_manifest_dependencies(path, relative))
            elif path.suffix.lower() in _CONFIG_SUFFIXES:
                configurations.append(relative)
            if language is Language.PYTHON:
                facts = _analyze_python(path, relative, module or "")
                symbols.extend(facts.symbols)
                routes.extend(facts.routes)
                schemas.extend(facts.schemas)
                python_imports[relative] = facts.imports
                for imported in facts.imports:
                    target = _resolve_module(imported, module_paths)
                    if target is not None:
                        dependencies.append(
                            DependencyEdge(relative, target, "imports", Certainty.KNOWN)
                        )
            elif language is not None:
                facts = _analyze_structural_text(path, relative, language)
                symbols.extend(facts.symbols)
                routes.extend(facts.routes)
                schemas.extend(facts.schemas)
                for imported in facts.imports:
                    target = _resolve_source_import(relative, imported, all_relative_paths, language)
                    if target is not None:
                        dependencies.append(
                            DependencyEdge(relative, target, "imports", Certainty.INFERRED)
                        )
                unknowns.append(f"semantic certainty limited for {relative}")

        tests = _map_tests(files, python_imports, module_paths)
        return RepositorySnapshot(
            str(self._root),
            _revision(self._root),
            tuple(sorted(files, key=lambda item: item.path)),
            tuple(sorted(symbols, key=lambda item: item.symbol_id)),
            tuple(sorted(set(dependencies), key=lambda item: (item.source, item.target, item.relationship))),
            tests,
            tuple(sorted(set(routes))),
            tuple(sorted(set(schemas))),
            tuple(sorted(manifests)),
            tuple(sorted(configurations)),
            tuple(sorted(unknowns)),
        )

    def impact(
        self, snapshot: RepositorySnapshot, changed_files: tuple[str, ...]
    ) -> ImpactAnalysis:
        known_files = {item.path for item in snapshot.files}
        normalized = tuple(sorted(set(changed_files)))
        unknowns = [f"changed file is absent from snapshot: {path}" for path in normalized if path not in known_files]
        affected = {path for path in normalized if path in known_files}
        reverse: dict[str, set[str]] = {}
        for edge in snapshot.dependencies:
            reverse.setdefault(edge.target, set()).add(edge.source)
        queue = list(affected)
        while queue:
            for dependent in reverse.get(queue.pop(), set()):
                if dependent not in affected:
                    affected.add(dependent)
                    queue.append(dependent)
        changed_symbols = tuple(
            item.symbol_id for item in snapshot.symbols if item.location.path in normalized
        )
        affected_tests = {
            mapping.test_file
            for mapping in snapshot.test_mappings
            if set(mapping.source_files) & affected or mapping.test_file in affected
        }
        affected.update(affected_tests)
        file_records = {item.path: item for item in snapshot.files}
        packages = {
            file_records[path].package
            for path in affected
            if path in file_records and file_records[path].package is not None
        }
        affected_apis = tuple(
            item.name
            for item in snapshot.symbols
            if item.symbol_type is SymbolType.API_ROUTE and item.location.path in affected
        )
        profile = ["unit"]
        if affected_tests:
            profile.append("mapped-tests")
        if affected_apis:
            profile.extend(("api-contract", "integration"))
        if any(path in snapshot.manifests for path in normalized):
            profile.extend(("dependency-audit", "full-suite"))
        confidence = Certainty.UNKNOWN if unknowns else (
            Certainty.INFERRED if any(item.certainty is Certainty.INFERRED for item in snapshot.test_mappings if item.test_file in affected_tests)
            else Certainty.KNOWN
        )
        return ImpactAnalysis(
            normalized,
            tuple(sorted(changed_symbols)),
            tuple(sorted(affected)),
            tuple(sorted(str(item) for item in packages)),
            tuple(sorted(affected_apis)),
            tuple(sorted(affected_tests)),
            tuple(sorted(affected - set(normalized))),
            confidence,
            tuple(sorted(unknowns)),
            tuple(dict.fromkeys(profile)),
        )

    def _discover(self) -> tuple[Path, ...]:
        supported = set(SourceFileAnalyzer.supported_extensions())
        paths = tuple(
            sorted(
                (
                    path
                    for path in self._root.rglob("*")
                    if path.is_file()
                    and not path.is_symlink()
                    and not (_IGNORED_DIRECTORIES & set(path.relative_to(self._root).parts))
                    and (path.suffix.lower() in supported or path.name in _MANIFEST_NAMES or path.suffix.lower() in _CONFIG_SUFFIXES)
                ),
                key=lambda item: item.relative_to(self._root).as_posix(),
            )
        )
        if len(paths) > self._max_files:
            raise RepositoryAnalysisError("repository exceeds file analysis limit")
        return paths


class _PythonVisitor(ast.NodeVisitor):
    def __init__(self, path: str, module: str) -> None:
        self.path = path
        self.module = module
        self.parents: list[tuple[str, str]] = []
        self.symbols: list[SymbolRecord] = []
        self.imports: set[str] = set()
        self.routes: set[str] = set()
        self.schemas: set[str] = set()

    def visit_Import(self, node: ast.Import) -> None:
        self.imports.update(alias.name for alias in node.names)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.level:
            package = self.module.split(".")[:-1]
            retained = package[: max(0, len(package) - node.level + 1)]
            if node.module:
                retained.extend(node.module.split("."))
                self.imports.add(".".join(retained))
            else:
                self.imports.update(".".join((*retained, alias.name)) for alias in node.names)
        elif node.module:
            self.imports.add(node.module)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        bases = tuple(_expression_name(item) for item in node.bases)
        symbol = self._symbol(node.name, SymbolType.CLASS, node, bases=bases)
        self.symbols.append(symbol)
        if any(base.rsplit(".", 1)[-1] in {"Base", "Model", "DeclarativeBase"} for base in bases):
            schema_name = f"{self.module}.{node.name}"
            self.schemas.add(schema_name)
            self.symbols.append(self._symbol(node.name, SymbolType.SCHEMA, node, certainty=Certainty.INFERRED))
        self.parents.append((node.name, symbol.symbol_id))
        self.generic_visit(node)
        self.parents.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        kind = SymbolType.METHOD if self.parents else SymbolType.FUNCTION
        references = tuple(sorted({_expression_name(item.func) for item in ast.walk(node) if isinstance(item, ast.Call)}))
        self.symbols.append(self._symbol(node.name, kind, node, references=references))
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            name = _expression_name(decorator.func)
            method = name.rsplit(".", 1)[-1].lower()
            if method not in _HTTP_METHODS or not decorator.args:
                continue
            route_arg = decorator.args[0]
            route = route_arg.value if isinstance(route_arg, ast.Constant) and isinstance(route_arg.value, str) else "<dynamic>"
            qualified = f"{method.upper()} {route}"
            self.routes.add(qualified)
            self.symbols.append(self._symbol(qualified, SymbolType.API_ROUTE, node, certainty=Certainty.INFERRED))
        self.generic_visit(node)

    def _symbol(
        self,
        name: str,
        kind: SymbolType,
        node: ast.AST,
        *,
        bases: tuple[str, ...] = (),
        references: tuple[str, ...] = (),
        certainty: Certainty = Certainty.KNOWN,
    ) -> SymbolRecord:
        prefix = ".".join([self.module, *(item[0] for item in self.parents)])
        qualified = f"{prefix}.{name}" if prefix else name
        return SymbolRecord(
            f"{kind.value}:{self.path}:{qualified}", name, qualified, kind,
            SourceLocation(self.path, getattr(node, "lineno", 1), getattr(node, "col_offset", 0)),
            Language.PYTHON, not name.startswith("_"),
            None if not self.parents else self.parents[-1][1], bases, references, certainty,
        )


def _analyze_python(path: Path, relative: str, module: str) -> _PythonFacts:
    content = SourceFileAnalyzer(path.parent).analyze(path).content
    try:
        tree = ast.parse(content, filename=relative)
    except SyntaxError as error:
        raise RepositoryAnalysisError(f"cannot parse Python source {relative}: {error.msg}") from error
    visitor = _PythonVisitor(relative, module)
    visitor.visit(tree)
    module_symbol = SymbolRecord(
        f"module:{relative}:{module}", module, module, SymbolType.MODULE,
        SourceLocation(relative, 1), Language.PYTHON, not module.rsplit(".", 1)[-1].startswith("_"),
    )
    return _PythonFacts((module_symbol, *visitor.symbols), tuple(sorted(visitor.imports)),
                        tuple(sorted(visitor.routes)), tuple(sorted(visitor.schemas)))


def _module_name(path: Path) -> str:
    parts = list(path.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _resolve_module(module: str, module_paths: dict[str, str]) -> str | None:
    candidate = module
    while candidate:
        if candidate in module_paths:
            return module_paths[candidate]
        candidate = candidate.rpartition(".")[0]
    return None


def _language(path: Path) -> Language | None:
    extension = path.suffix.lower()
    mapping = {".py": Language.PYTHON, ".ts": Language.TYPESCRIPT, ".tsx": Language.TYPESCRIPT,
               ".js": Language.JAVASCRIPT, ".jsx": Language.JAVASCRIPT, ".dart": Language.DART}
    return mapping.get(extension)


def _file_kind(path: Path, relative: str) -> FileKind:
    if path.name in _MANIFEST_NAMES:
        return FileKind.MANIFEST
    if path.suffix.lower() in _CONFIG_SUFFIXES:
        return FileKind.CONFIGURATION
    parts = path.parts
    if "tests" in parts or path.name.startswith("test_") or relative.endswith("_test.py"):
        return FileKind.TEST
    return FileKind.SOURCE


def _generated(path: Path) -> bool:
    try:
        head = path.read_bytes()[:2048].decode("utf-8", errors="ignore").casefold()
    except OSError:
        return False
    return "generated file" in head or "do not edit" in head or path.name.endswith(("_generated.py", ".g.dart"))


def _expression_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _expression_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return "<dynamic>"


def _map_tests(
    files: list[SourceFileRecord], imports: dict[str, tuple[str, ...]], module_paths: dict[str, str]
) -> tuple[TestMapping, ...]:
    mappings: list[TestMapping] = []
    for file in files:
        if file.kind is not FileKind.TEST:
            continue
        sources = {
            target
            for module in imports.get(file.path, ())
            for target in [_resolve_module(module, module_paths)]
            if target is not None and target != file.path
        }
        certainty = Certainty.KNOWN
        rationale = "resolved Python import"
        if not sources and file.path.endswith(".py"):
            stem = Path(file.path).stem.removeprefix("test_").removesuffix("_test")
            candidates = {item.path for item in files if Path(item.path).stem == stem and item.kind is FileKind.SOURCE}
            sources.update(candidates)
            certainty = Certainty.INFERRED if candidates else Certainty.UNKNOWN
            rationale = "test filename convention" if candidates else "no source relationship resolved"
        mappings.append(TestMapping(file.path, tuple(sorted(sources)), certainty, rationale))
    return tuple(sorted(mappings, key=lambda item: item.test_file))


def _revision(root: Path) -> str:
    result = subprocess.run(("git", "rev-parse", "HEAD"), cwd=root, check=False,
                            capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else "UNKNOWN"


def _analyze_structural_text(path: Path, relative: str, language: Language) -> _PythonFacts:
    """Extract bounded syntax-shaped facts and label every assertion inferred."""
    content = path.read_text(encoding="utf-8-sig")
    imports: set[str] = set()
    symbols: list[SymbolRecord] = []
    routes: set[str] = set()
    schemas: set[str] = set()
    if language is Language.TYPESCRIPT or language is Language.JAVASCRIPT:
        imports.update(
            match.group(1)
            for match in re.finditer(
                r"(?:from\s+|import\s*\(\s*)['\"]([^'\"]+)['\"]", content
            )
        )
        declaration = re.compile(
            r"(?m)^\s*(export\s+)?(?:default\s+)?(?:async\s+)?"
            r"(class|function|const|let|var)\s+([A-Za-z_$][\w$]*)"
            r"(?:\s+extends\s+([A-Za-z_$][\w.$]*))?"
        )
        for match in declaration.finditer(content):
            exported, kind, name, base = match.groups()
            symbol_type = SymbolType.CLASS if kind == "class" else (
                SymbolType.FUNCTION if kind == "function" else SymbolType.VARIABLE
            )
            symbols.append(
                _inferred_symbol(relative, language, name, symbol_type, content, match.start(),
                                 bases=() if base is None else (base,), public=bool(exported))
            )
            if exported:
                symbols.append(
                    _inferred_symbol(relative, language, name, SymbolType.EXPORT, content, match.start())
                )
            if (
                exported
                and name.upper() in {item.upper() for item in _HTTP_METHODS}
                and "/app/" in f"/{relative}"
                and "/route." in relative
            ):
                route = f"{name.upper()} {_next_route(relative)}"
                routes.add(route)
                symbols.append(
                    _inferred_symbol(relative, language, route, SymbolType.API_ROUTE, content, match.start())
                )
    elif language is Language.DART:
        imports.update(
            match.group(1)
            for match in re.finditer(r"(?m)^\s*import\s+['\"]([^'\"]+)['\"]", content)
        )
        declaration = re.compile(
            r"(?m)^\s*(?:abstract\s+)?class\s+([A-Za-z_]\w*)"
            r"(?:\s+extends\s+([A-Za-z_]\w*))?"
            r"|^\s*(?:Future(?:<[^>]+>)?|void|int|double|bool|String|Widget)\s+([A-Za-z_]\w*)\s*\("
        )
        for match in declaration.finditer(content):
            class_name, base, function_name = match.groups()
            name = class_name or function_name
            if name is None:
                continue
            kind = SymbolType.CLASS if class_name else SymbolType.FUNCTION
            symbols.append(
                _inferred_symbol(relative, language, name, kind, content, match.start(),
                                 bases=() if base is None else (base,), public=not name.startswith("_"))
            )
    return _PythonFacts(tuple(symbols), tuple(sorted(imports)), tuple(sorted(routes)), tuple(sorted(schemas)))


def _inferred_symbol(
    relative: str,
    language: Language,
    name: str,
    kind: SymbolType,
    content: str,
    offset: int,
    *,
    bases: tuple[str, ...] = (),
    public: bool = True,
) -> SymbolRecord:
    line = content.count("\n", 0, offset) + 1
    column = offset - content.rfind("\n", 0, offset) - 1
    qualified = f"{relative}:{name}"
    return SymbolRecord(
        f"{kind.value}:{qualified}", name, qualified, kind,
        SourceLocation(relative, line, column), language, public,
        bases=bases, certainty=Certainty.INFERRED,
    )


def _resolve_source_import(
    source: str, imported: str, paths: set[str], language: Language
) -> str | None:
    if imported.startswith("."):
        base = Path(source).parent.joinpath(imported).as_posix()
        candidates = [
            base,
            *(base + suffix for suffix in (".ts", ".tsx", ".js", ".jsx", ".dart")),
            *(base + "/index" + suffix for suffix in (".ts", ".tsx", ".js", ".jsx")),
        ]
        return next((candidate for candidate in candidates if candidate in paths), None)
    if language is Language.DART and imported.startswith("package:"):
        package_path = imported.partition("/")[2]
        candidate = f"apps/desktop/lib/{package_path}"
        return candidate if candidate in paths else None
    return None


def _next_route(relative: str) -> str:
    route = relative.split("/app/", 1)[1].rsplit("/route.", 1)[0]
    return "/" + "/".join(part for part in route.split("/") if not part.startswith("(") and not part.endswith(")"))


def _manifest_dependencies(path: Path, relative: str) -> tuple[DependencyEdge, ...]:
    dependencies: list[DependencyEdge] = []
    if path.name == "pyproject.toml":
        document = tomllib.loads(path.read_text(encoding="utf-8-sig"))
        project = document.get("project", {})
        if isinstance(project, dict):
            declared = project.get("dependencies", [])
            if isinstance(declared, list):
                for item in declared:
                    if isinstance(item, str):
                        name = re.split(r"[<>=!~;\[]", item, maxsplit=1)[0].strip()
                        if name:
                            dependencies.append(
                                DependencyEdge(relative, f"package:{name}", "declares_dependency", Certainty.KNOWN)
                            )
    elif path.name == "package.json":
        document = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(document, dict):
            for package_section in ("dependencies", "devDependencies", "peerDependencies"):
                declared = document.get(package_section, {})
                if isinstance(declared, dict):
                    dependencies.extend(
                        DependencyEdge(relative, f"package:{name}", "declares_dependency", Certainty.KNOWN)
                        for name in declared
                    )
    elif path.name == "pubspec.yaml":
        manifest_section: str | None = None
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if line in {"dependencies:", "dev_dependencies:"}:
                manifest_section = line[:-1]
                continue
            if manifest_section is not None and line and not line.startswith(" "):
                manifest_section = None
            match = re.match(r"^  ([A-Za-z_]\w*):", line) if manifest_section else None
            if match and match.group(1) not in {"flutter"}:
                dependencies.append(
                    DependencyEdge(relative, f"package:{match.group(1)}", "declares_dependency", Certainty.INFERRED)
                )
    return tuple(dependencies)
