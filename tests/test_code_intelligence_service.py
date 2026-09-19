from __future__ import annotations

import subprocess
from collections.abc import Mapping
from pathlib import Path

import pytest

from services.code_intelligence import (
    CodeIntelligenceAdmissionError,
    ILAIOSRepositoryIntelligence,
)
from services.software_factory_skills import (
    SkillExecutionRequest,
    SkillExecutor,
    SkillRegistry,
    default_skills_root,
)


class _UnusedRuntime:
    def validate(self, adapter_id: str, repository: Path) -> Mapping[str, object]:
        raise AssertionError(
            f"runtime adapter must not be called: {adapter_id} {repository}"
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
    (repository / ".gitignore").write_text("ignored.py\n", encoding="utf-8")
    _git(repository, "add", "app.py", ".gitignore")
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


def _commit_all(repository: Path, message: str) -> str:
    _git(repository, "add", "-A")
    _git(
        repository,
        "-c",
        "user.name=ILAIOS CI",
        "-c",
        "user.email=ci@ilaios.invalid",
        "commit",
        "-q",
        "-m",
        message,
    )
    return _git(repository, "rev-parse", "HEAD")


def test_adapter_binds_evidence_to_exact_repository_revision(tmp_path: Path) -> None:
    repository, revision = _repository(tmp_path)

    evidence = ILAIOSRepositoryIntelligence().inspect(repository, revision)

    assert evidence["schema_version"] == "ilaios-code-intelligence-evidence-v1"
    assert evidence["repository_revision"] == revision
    assert isinstance(evidence["generation_id"], str)
    assert evidence["node_count"] == 3


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


def test_adapter_rejects_dirty_tracked_worktree(tmp_path: Path) -> None:
    repository, revision = _repository(tmp_path)
    (repository / "app.py").write_text(
        "def run() -> str:\n    return 'changed'\n",
        encoding="utf-8",
    )

    with pytest.raises(CodeIntelligenceAdmissionError, match="worktree must be clean"):
        ILAIOSRepositoryIntelligence().inspect(repository, revision)


def test_adapter_rejects_untracked_supported_source(tmp_path: Path) -> None:
    repository, revision = _repository(tmp_path)
    (repository / "extra.py").write_text("value = 1\n", encoding="utf-8")

    with pytest.raises(CodeIntelligenceAdmissionError, match="worktree must be clean"):
        ILAIOSRepositoryIntelligence().inspect(repository, revision)


def test_adapter_rejects_ignored_supported_source(tmp_path: Path) -> None:
    repository, revision = _repository(tmp_path)
    (repository / "ignored.py").write_text("value = 1\n", encoding="utf-8")
    assert _git(repository, "status", "--porcelain") == ""

    with pytest.raises(
        CodeIntelligenceAdmissionError,
        match="not tracked by requested revision",
    ):
        ILAIOSRepositoryIntelligence().inspect(repository, revision)


def test_adapter_preserves_tracked_paths_with_leading_whitespace(tmp_path: Path) -> None:
    repository, _revision = _repository(tmp_path)
    (repository / " config.json").write_text("{}\n", encoding="utf-8")
    revision = _commit_all(repository, "whitespace path")

    evidence = ILAIOSRepositoryIntelligence().inspect(repository, revision)

    assert evidence["repository_revision"] == revision


def test_adapter_rejects_symbolic_link_repository_root(tmp_path: Path) -> None:
    repository, revision = _repository(tmp_path)
    link = tmp_path / "repo-link"
    try:
        link.symlink_to(repository, target_is_directory=True)
    except OSError:
        pytest.skip("symbolic links are unavailable on this platform")

    with pytest.raises(CodeIntelligenceAdmissionError, match="symbolic link"):
        ILAIOSRepositoryIntelligence().inspect(link, revision)


def test_adapter_fails_closed_when_git_verification_times_out(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, revision = _repository(tmp_path)

    def _timeout(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(cmd=("git",), timeout=10.0)

    monkeypatch.setattr("services.code_intelligence.subprocess.run", _timeout)

    with pytest.raises(CodeIntelligenceAdmissionError, match="Git verification failed"):
        ILAIOSRepositoryIntelligence().inspect(repository, revision)


def test_sf7_repository_intelligence_skill_uses_first_party_adapter(
    tmp_path: Path,
) -> None:
    repository, revision = _repository(tmp_path)
    project_root = Path(__file__).resolve().parents[1]
    executor = SkillExecutor(
        SkillRegistry(default_skills_root(project_root)),
        ILAIOSRepositoryIntelligence(),
        _UnusedRuntime(),
    )

    result = executor.execute(
        SkillExecutionRequest(
            skill_id="sf-repository-intelligence",
            repository=repository,
            base_sha=revision,
            actor_id="actor-1",
            tenant_id="tenant-1",
            policy_allowed=True,
            payload={"intent": "inspect repository", "changed_paths": []},
            requested_capabilities=frozenset({"repository_intelligence"}),
        )
    )

    assert result.status == "READY"
    assert result.repository_evidence["repository_revision"] == revision
    assert (
        result.repository_evidence["graph_schema_version"]
        == "ilaios-code-intelligence-graph-v1"
    )
