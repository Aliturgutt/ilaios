"""Runtime wiring tests for autonomous execution orphan recovery."""

from __future__ import annotations

from datetime import datetime
from typing import cast

import pytest

from services.desktop_identity_server import DesktopIdentityHTTPServer
from services.execution_coordinator import ExecutionCoordinator


class _RecoveryCoordinator:
    def __init__(self) -> None:
        self.calls: list[tuple[str, datetime]] = []

    def recover_stale(
        self, *, token: str, now: datetime
    ) -> tuple[dict[str, str], ...]:
        self.calls.append((token, now))
        return ({"request_id": "exec-orphan", "status": "INTERRUPTED"},)


def test_server_lifecycle_periodically_reconciles_orphaned_executions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = [100.0]
    monkeypatch.setattr(
        "services.desktop_identity_server.time.monotonic", lambda: clock[0]
    )
    recovery = _RecoveryCoordinator()
    server = DesktopIdentityHTTPServer(
        ("127.0.0.1", 0),
        bearer_token="desktop-token",
        identity=None,
        coordinator=cast(ExecutionCoordinator, recovery),
    )
    try:
        server.service_actions()
        server.service_actions()
        assert len(recovery.calls) == 1
        token, recovery_time = recovery.calls[0]
        assert token == "desktop-token"
        assert recovery_time.tzinfo is not None

        clock[0] = 159.9
        server.service_actions()
        assert len(recovery.calls) == 1

        clock[0] = 160.0
        server.service_actions()
        assert len(recovery.calls) == 2
    finally:
        server.server_close()


def test_recovery_failure_is_observable_and_does_not_break_server_loop(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class _FailingRecoveryCoordinator:
        def recover_stale(
            self, *, token: str, now: datetime
        ) -> tuple[dict[str, str], ...]:
            raise RuntimeError("simulated recovery failure")

    monkeypatch.setattr(
        "services.desktop_identity_server.time.monotonic", lambda: 200.0
    )
    server = DesktopIdentityHTTPServer(
        ("127.0.0.1", 0),
        bearer_token="desktop-token",
        identity=None,
        coordinator=cast(ExecutionCoordinator, _FailingRecoveryCoordinator()),
    )
    try:
        server.service_actions()
        output = capsys.readouterr().out
        assert '"event": "execution_recovery_sweep_failed"' in output
        assert '"error_type": "RuntimeError"' in output
    finally:
        server.server_close()
