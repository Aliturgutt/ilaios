"""Fail-closed diagnostics for local operational-drill subprocess failures."""

import subprocess
import sys

import pytest

from services import operational_drills


@pytest.mark.parametrize(
    ("code", "expected_type"),
    [
        ("raise RuntimeError('private-marker-123')", "RuntimeError"),
        ("import missing_ilaios_test_dependency_123", "ModuleNotFoundError"),
        ("import sys; sys.exit(3)", "UNKNOWN"),
    ],
)
def test_runtime_start_error_reports_only_exception_type(
    tmp_path, monkeypatch, code, expected_type
):
    original_popen = subprocess.Popen

    def failing_runtime(*args, **kwargs):
        return original_popen([sys.executable, "-c", code], **kwargs)

    monkeypatch.setattr(operational_drills.subprocess, "Popen", failing_runtime)
    runtime = operational_drills._RuntimeProcess(
        tmp_path, tmp_path / "state", tmp_path / "ready.json"
    )

    with pytest.raises(operational_drills.DrillExecutionError) as exc_info:
        runtime.start()

    message = str(exc_info.value)
    assert "runtime exited before readiness" in message
    assert f"error_type={expected_type}" in message
    assert "private-marker-123" not in message
    assert runtime._stderr_capture is None
