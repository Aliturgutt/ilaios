from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from services.code_intelligence import (
    CodeIntelligenceAdmissionError,
    ILAIOSRepositoryIntelligence,
)


def _git(repository: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ("git", *arguments),
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _repository(tmp_path: Path) -> tuple[Path, str]:
    repository = tmp_path / "repo"
    repository.mkdir()
    _git(repository, "init", "-q")
    (repository / "app.py").write_text(
        "def run() -> str:\n    return 'ok'\n",
        encoding="utf-8",
    )
    _git(repository, "add", "app.py")
    _git(
        repository,
        "-c",
        "user.name=ILAIOS CI",
        "-c",
        "user.email=ci@ilaios.invalid",
        "commit",
        "-q",
        "-m",
        "fixture",
    )
    return repository, _git(repository, "rev-parse", "HEAD")


def test_adapter_binds_evidence_to_exact_repository_revision(tmp_path: Path) -> None:
    repository, revision = _repository(tmp_path)

    evidence = ILAIOSRepositoryIntelligence().inspect(repository, revision)

    assert evidence["schema_version"] == "ilaios-code-intelligence-evidence-v1"
    assert evidence["repository_revision"] == revision
    assert isinstance(evidence["generation_id"], str)
    assert evidence["node_count"] == 2


def test_adapter_rejects_stale_or_wrong_revision(tmp_path: Path) -> None:
    repository, _revision = _repository(tmp_path)

    with pytest.raises(CodeIntelligenceAdmissionError, match="revision"):
        ILAIOSRepositoryIntelligence().inspect(repository, "0" * 40)


def test_adapter_is_read_only_for_repository_worktree(tmp_path: Path) -> None:
    repository, revision = _repository(tmp_path)
    before_status = _git(repository, "status", "--porcelain")
    before_content = (repository / "app.py").read_bytes()

    ILAIOSRepositoryIntelligence().inspect(repository, revision)

    assert _git(repository, "status", "--porcelain") == before_status
    assert (repository / "app.py").read_bytes() == before_content


def test_adapter_rejects_non_sha_revision_before_analysis(tmp_path: Path) -> None:
    repository, _revision = _repository(tmp_path)

    with pytest.raises(CodeIntelligenceAdmissionError, match="base_sha"):
        ILAIOSRepositoryIntelligence().inspect(repository, "not-a-sha")
