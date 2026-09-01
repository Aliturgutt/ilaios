"""Realistic SF-5 repository intelligence and impact-analysis tests."""

from __future__ import annotations

import subprocess
from pathlib import Path

from services.software_factory import (
    Change,
    ChangeOperation,
    ChangeSet,
    ExecutionPolicy,
    RepositoryRef,
    SoftwareFactory,
    SoftwareFactoryRequest,
)
from src.code_intelligence import Certainty, FileKind, RepositoryAnalyzer, SymbolType


def _fixture(root: Path) -> None:
    (root / "src").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "web").mkdir()
    (root / "desktop").mkdir()
    (root / "src" / "__init__.py").write_text("", encoding="utf-8")
    (root / "src" / "models.py").write_text(
        "class Base:\n    pass\n\nclass Account(Base):\n    account_id: str\n",
        encoding="utf-8",
    )
    (root / "src" / "service.py").write_text(
        "from .models import Account\n\n"
        "def load_account():\n    return Account()\n\n"
        "class AccountService:\n"
        "    def fetch(self):\n        return load_account()\n\n"
        "@router.get('/accounts/{account_id}')\n"
        "def get_account(account_id: str):\n    return load_account()\n",
        encoding="utf-8",
    )
    (root / "tests" / "test_service.py").write_text(
        "from src.service import load_account\n\n"
        "def test_load_account():\n    assert load_account() is not None\n",
        encoding="utf-8",
    )
    (root / "src" / "client_generated.py").write_text(
        "# Generated file. Do not edit.\nVALUE = 1\n", encoding="utf-8"
    )
    (root / "web" / "client.ts").write_text(
        "export function loadAccount() { return fetch('/accounts/1'); }\n"
        "export class AccountClient extends BaseClient {}\n",
        encoding="utf-8",
    )
    (root / "desktop" / "account.dart").write_text(
        "import './client.dart';\nclass AccountView extends Widget {}\nvoid loadAccount() {}\n",
        encoding="utf-8",
    )
    (root / "pyproject.toml").write_text(
        "[project]\nname='fixture'\ndependencies=['requests>=2']\n", encoding="utf-8"
    )
    (root / "web" / "package.json").write_text(
        '{"dependencies":{"react":"^19"}}\n', encoding="utf-8"
    )
    (root / "config.yaml").write_text("enabled: true\n", encoding="utf-8")


def _git_repository(root: Path) -> str:
    subprocess.run(("git", "init", "-q"), cwd=root, check=True)
    subprocess.run(("git", "config", "user.email", "intelligence@example.invalid"), cwd=root, check=True)
    subprocess.run(("git", "config", "user.name", "Intelligence Test"), cwd=root, check=True)
    subprocess.run(("git", "add", "."), cwd=root, check=True)
    subprocess.run(("git", "commit", "-qm", "fixture"), cwd=root, check=True)
    return subprocess.run(("git", "rev-parse", "HEAD"), cwd=root, check=True,
                          capture_output=True, text=True).stdout.strip()


def test_snapshot_uses_ast_and_represents_semantic_unknowns(tmp_path: Path) -> None:
    _fixture(tmp_path)
    snapshot = RepositoryAnalyzer(tmp_path).snapshot()

    assert {item.path for item in snapshot.files} >= {
        "src/models.py", "src/service.py", "tests/test_service.py", "web/client.ts",
        "desktop/account.dart",
    }
    classes = {item.qualified_name: item for item in snapshot.symbols if item.symbol_type is SymbolType.CLASS}
    assert classes["src.models.Account"].bases == ("Base",)
    methods = {item.qualified_name: item for item in snapshot.symbols if item.symbol_type is SymbolType.METHOD}
    assert methods["src.service.AccountService.fetch"].parent_symbol_id is not None
    assert "load_account" in methods["src.service.AccountService.fetch"].references
    assert "GET /accounts/{account_id}" in snapshot.api_routes
    assert "src.models.Account" in snapshot.schema_entities
    assert any(edge.source == "src/service.py" and edge.target == "src/models.py" for edge in snapshot.dependencies)
    assert any(
        edge.source == "pyproject.toml" and edge.target == "package:requests"
        for edge in snapshot.dependencies
    )
    assert any(
        edge.source == "web/package.json" and edge.target == "package:react"
        for edge in snapshot.dependencies
    )
    mapping = next(item for item in snapshot.test_mappings if item.test_file == "tests/test_service.py")
    assert mapping.source_files == ("src/service.py",) and mapping.certainty is Certainty.KNOWN
    generated = next(item for item in snapshot.files if item.path == "src/client_generated.py")
    assert generated.kind is FileKind.GENERATED and generated.certainty is Certainty.INFERRED
    ts_class = next(item for item in snapshot.symbols if item.name == "AccountClient")
    assert ts_class.bases == ("BaseClient",) and ts_class.certainty is Certainty.INFERRED
    dart_class = next(item for item in snapshot.symbols if item.name == "AccountView")
    assert dart_class.bases == ("Widget",) and dart_class.certainty is Certainty.INFERRED
    assert "semantic certainty limited for web/client.ts" in snapshot.unknowns


def test_impact_propagates_reverse_dependencies_tests_apis_and_profiles(tmp_path: Path) -> None:
    _fixture(tmp_path)
    analyzer = RepositoryAnalyzer(tmp_path)
    snapshot = analyzer.snapshot()
    impact = analyzer.impact(snapshot, ("src/models.py",))

    assert impact.changed_files == ("src/models.py",)
    assert {"src/models.py", "src/service.py", "tests/test_service.py"} <= set(impact.affected_files)
    assert impact.affected_tests == ("tests/test_service.py",)
    assert "GET /accounts/{account_id}" in impact.affected_apis
    assert {"unit", "mapped-tests", "api-contract", "integration"} <= set(
        impact.recommended_validation_profile
    )
    assert impact.confidence is Certainty.KNOWN

    unknown = analyzer.impact(snapshot, ("missing/new.py",))
    assert unknown.confidence is Certainty.UNKNOWN
    assert unknown.unknowns == ("changed file is absent from snapshot: missing/new.py",)


def test_software_factory_binds_repository_impact_to_base_sha(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    _fixture(repository)
    sha = _git_repository(repository)
    request = SoftwareFactoryRequest(
        "impact-request",
        RepositoryRef(repository.resolve(), sha),
        ExecutionPolicy(frozenset({"src"})),
        ChangeSet((Change(ChangeOperation.MODIFY, "src/models.py", b"class Account:\n    pass\n"),)),
    )
    snapshot, impact = SoftwareFactory(
        tmp_path / "workspaces", tmp_path / "proposals"
    ).repository_impact(request)

    assert snapshot.revision == sha
    assert impact.changed_files == ("src/models.py",)
    assert "tests/test_service.py" in impact.affected_tests
