"""Cross-platform security and transaction tests for the canonical factory."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

import services.software_factory as software_factory_module
from services.software_factory import (
    Change,
    ChangeOperation,
    ChangeSet,
    ExecutionPolicy,
    FactoryJob,
    FactoryJobState,
    RepositoryRef,
    SoftwareFactory,
    SoftwareFactoryError,
    SoftwareFactoryRequest,
    ValidationPlan,
)


def _engine_submit(
    factory: SoftwareFactory, request: SoftwareFactoryRequest
) -> FactoryJob:
    """Exercise the internal engine after the SF-4 boundary in foundation tests."""
    return factory.submit(request, authority=software_factory_module._GOVERNED_FACTORY_AUTHORITY)


def _repository(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "repository"
    (root / "src").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "src" / "old.py").write_text("old = True\n", encoding="utf-8")
    (root / "src" / "modify.py").write_text("value = 1\n", encoding="utf-8")
    subprocess.run(("git", "init", "-q"), cwd=root, check=True)
    subprocess.run(("git", "config", "user.email", "factory@example.invalid"), cwd=root, check=True)
    subprocess.run(("git", "config", "user.name", "Factory Test"), cwd=root, check=True)
    subprocess.run(("git", "add", "."), cwd=root, check=True)
    subprocess.run(("git", "commit", "-qm", "base"), cwd=root, check=True)
    sha = subprocess.run(
        ("git", "rev-parse", "HEAD"), cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()
    return root, sha


def _policy() -> ExecutionPolicy:
    return ExecutionPolicy(frozenset({"src", "tests"}))


def test_atomic_multifile_changeset_is_review_only_and_idempotent(tmp_path: Path) -> None:
    repository, sha = _repository(tmp_path)
    original_hash = hashlib.sha256((repository / "src/modify.py").read_bytes()).hexdigest()
    request = SoftwareFactoryRequest(
        "request-1",
        RepositoryRef(repository.resolve(), sha),
        _policy(),
        ChangeSet(
            (
                Change(ChangeOperation.CREATE, "tests/test_new.py", b"def test_new():\n    assert True\n"),
                Change(ChangeOperation.MODIFY, "src/modify.py", b"value = 2\n", expected_sha256=original_hash),
                Change(ChangeOperation.RENAME, "src/old.py", destination="src/renamed.py"),
                Change(ChangeOperation.DELETE, "tests/test_new.py"),
            )
        ),
    )
    factory = SoftwareFactory(tmp_path / "workspaces", tmp_path / "proposals")

    job = _engine_submit(factory, request)
    assert job.state is FactoryJobState.PROPOSED
    assert job.workspace is not None
    assert (job.workspace.path / "src/modify.py").read_text() == "value = 2\n"
    assert (job.workspace.path / "src/renamed.py").is_file()
    assert not (job.workspace.path / "src/old.py").exists()
    assert (repository / "src/modify.py").read_text() == "value = 1\n"
    assert _engine_submit(factory, request) == job
    assert factory.proposal(job.job_id).production_applied is False
    with pytest.raises(SoftwareFactoryError, match="forbidden"):
        factory.promote(job.job_id)


def test_changeset_failure_is_atomic_and_paths_are_bounded(tmp_path: Path) -> None:
    repository, sha = _repository(tmp_path)
    factory = SoftwareFactory(tmp_path / "workspaces", tmp_path / "proposals")
    request = SoftwareFactoryRequest(
        "request-atomic",
        RepositoryRef(repository.resolve(), sha),
        _policy(),
        ChangeSet(
            (
                Change(ChangeOperation.MODIFY, "src/modify.py", b"value = 2\n"),
                Change(ChangeOperation.CREATE, "../escape.py", b"escaped = True\n"),
            )
        ),
    )
    with pytest.raises(SoftwareFactoryError, match="escapes"):
        _engine_submit(factory, request)
    workspace = tmp_path / "workspaces" / next(iter(factory._jobs))  # transaction state inspection
    assert (workspace / "src/modify.py").read_text() == "value = 1\n"
    assert not (tmp_path / "escape.py").exists()


def test_secure_mode_fails_closed_without_command_sandbox(tmp_path: Path) -> None:
    repository, sha = _repository(tmp_path)
    factory = SoftwareFactory(tmp_path / "workspaces", tmp_path / "proposals")
    request = SoftwareFactoryRequest(
        "request-secure",
        RepositoryRef(repository.resolve(), sha),
        _policy(),
        ChangeSet((Change(ChangeOperation.CREATE, "src/new.py", b"value = 1\n"),)),
        ValidationPlan((("python", "-c", "print('unsafe')"),)),
    )
    with pytest.raises(SoftwareFactoryError, match="sandbox cannot enforce"):
        _engine_submit(factory, request)


def test_nonsecure_command_execution_still_requires_explicit_network_and_secrets(
    tmp_path: Path,
) -> None:
    repository, sha = _repository(tmp_path)
    policy = ExecutionPolicy(frozenset({"src"}), secure_mode=False)
    request = SoftwareFactoryRequest(
        "request-no-policy-bypass",
        RepositoryRef(repository.resolve(), sha),
        policy,
        ChangeSet((Change(ChangeOperation.CREATE, "src/new.py", b"value = 1\n"),)),
        ValidationPlan((("python", "-c", "print('must not run')"),)),
    )
    with pytest.raises(SoftwareFactoryError, match="sandbox cannot enforce"):
        _engine_submit(SoftwareFactory(tmp_path / "workspaces", tmp_path / "proposals"), request)


def test_base_sha_and_request_identity_are_enforced(tmp_path: Path) -> None:
    repository, sha = _repository(tmp_path)
    factory = SoftwareFactory(tmp_path / "workspaces", tmp_path / "proposals")
    change = ChangeSet((Change(ChangeOperation.CREATE, "src/new.py", b"value = 1\n"),))
    _engine_submit(factory, SoftwareFactoryRequest("same", RepositoryRef(repository.resolve(), sha), _policy(), change))
    conflicting = ChangeSet((Change(ChangeOperation.CREATE, "src/other.py", b"value = 2\n"),))
    with pytest.raises(SoftwareFactoryError, match="conflicts"):
        _engine_submit(factory, SoftwareFactoryRequest("same", RepositoryRef(repository.resolve(), sha), _policy(), conflicting))
    with pytest.raises(SoftwareFactoryError, match="base SHA"):
        _engine_submit(
            SoftwareFactory(tmp_path / "workspaces-2", tmp_path / "proposals-2"),
            SoftwareFactoryRequest("stale", RepositoryRef(repository.resolve(), "0" * 40), _policy(), change),
        )
