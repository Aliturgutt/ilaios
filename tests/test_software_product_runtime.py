"""Finished-product Software Factory runtime tests."""

from __future__ import annotations

import hashlib
import io
import zipfile
from pathlib import Path
from typing import cast

import pytest

from services.integrations.software_product_runtime import (
    FinishedSoftwareBuilder,
    SoftwareProductSecurityError,
    SoftwareProductValidationError,
)


def test_finished_software_builder_produces_deterministic_usable_zip(tmp_path: Path) -> None:
    builder = FinishedSoftwareBuilder(tmp_path / "runs")
    result = builder.build(
        "software-build-1",
        "Build me a simple production-quality task management application",
    )

    artifact = result.pop("artifact_bytes")
    assert isinstance(artifact, bytes)
    build_result = cast(dict[str, object], result["build_result"])
    security_result = cast(dict[str, object], result["security_result"])
    test_result = cast(dict[str, object], result["test_result"])
    runtime_result = cast(dict[str, object], result["runtime_result"])
    dependency_evidence = cast(dict[str, object], result["dependency_evidence"])
    assert hashlib.sha256(artifact).hexdigest() == build_result["artifact_sha256"]
    assert security_result["passed"] is True
    assert test_result["passed"] is True
    assert runtime_result["passed"] is True
    assert runtime_result["browser_javascript_execution_proven"] is False
    assert dependency_evidence["third_party"] == []
    assert result["repair_history"] == []

    with zipfile.ZipFile(io.BytesIO(artifact), "r") as archive:
        assert sorted(archive.namelist()) == [
            "README.txt",
            "app.js",
            "index.html",
            "styles.css",
        ]
        assert b"Task Manager" in archive.read("index.html")
        assert b"localStorage" in archive.read("app.js")


def test_builder_repairs_one_bounded_validation_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    builder = FinishedSoftwareBuilder(tmp_path / "runs")
    original = builder._structural_test  # noqa: SLF001
    calls = 0

    def fail_once(project: Path) -> dict[str, object]:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise SoftwareProductValidationError("injected repairable failure")
        return original(project)

    monkeypatch.setattr(builder, "_structural_test", fail_once)
    result = builder.build(
        "software-build-repair",
        "Build a task manager software application",
    )

    build_result = cast(dict[str, object], result["build_result"])
    history = cast(list[dict[str, object]], result["repair_history"])
    assert build_result["passed"] is True
    assert len(history) == 1
    assert history[0]["attempt"] == 1
    assert history[0]["repaired"] is True


def test_generated_security_failure_is_not_repaired_or_delivered(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    builder = FinishedSoftwareBuilder(tmp_path / "runs")
    original = builder._write_project  # noqa: SLF001

    def unsafe(project: Path, objective: str, attempt: int) -> None:
        original(project, objective, attempt)
        with (project / "app.js").open("a", encoding="utf-8") as stream:
            stream.write("\nfetch('https://example.invalid');\n")

    monkeypatch.setattr(builder, "_write_project", unsafe)
    with pytest.raises(SoftwareProductSecurityError, match="network egress"):
        builder.build(
            "software-build-security",
            "Build a task management application",
        )
