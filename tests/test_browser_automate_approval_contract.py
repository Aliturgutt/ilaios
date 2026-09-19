from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from services.runtime.browser_tool_adapter import (
    BROWSER_AGENT_ID,
    BROWSER_AUTOMATION_SKILL_ID,
    BROWSER_CAPABILITY,
    BrowserProcessResult,
    BrowserTargetPolicy,
    BrowserToolError,
    BrowserWorkReader,
    GovernedBrowserTool,
    PlaywrightCliAdapter,
    browser_request_payload,
)


class _NeverRunEgress:
    def run(
        self,
        *,
        allowed_origins: tuple[str, ...],
        argv: tuple[str, ...],
        cwd: Path,
        timeout_seconds: int,
    ) -> BrowserProcessResult:
        raise AssertionError("browser egress must not run without independent approval")


def _persist_click(path: Path) -> dict[str, object]:
    payload = browser_request_payload(
        "user-1",
        "tenant-1",
        "workflow-1",
        BROWSER_AUTOMATION_SKILL_ID,
        "click",
        operand="e1",
        target_url="https://example.com/",
    )
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE governed_work (request_id TEXT PRIMARY KEY, requester_id TEXT NOT NULL, "
            "agent_id TEXT NOT NULL, skill_id TEXT NOT NULL, capability TEXT NOT NULL, "
            "payload_json TEXT NOT NULL, secret_ids_json TEXT NOT NULL, status TEXT NOT NULL, "
            "result_json TEXT)"
        )
        connection.execute(
            "INSERT INTO governed_work VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "req-1",
                "user-1",
                BROWSER_AGENT_ID,
                BROWSER_AUTOMATION_SKILL_ID,
                BROWSER_CAPABILITY,
                json.dumps(payload, sort_keys=True, separators=(",", ":")),
                "[]",
                "pending",
                None,
            ),
        )
    return payload


def _tool(tmp_path: Path, governance: MagicMock) -> GovernedBrowserTool:
    database = tmp_path / "governance.db"
    governance._database_path = database
    _persist_click(database)
    return GovernedBrowserTool(
        governance,
        BrowserWorkReader(governance, database),
        BrowserTargetPolicy(frozenset({"https://example.com"})),
        PlaywrightCliAdapter(_NeverRunEgress(), tmp_path / "evidence"),
        MagicMock(),
    )


def _execute_click(tool: GovernedBrowserTool) -> None:
    payload = browser_request_payload(
        "user-1",
        "tenant-1",
        "workflow-1",
        BROWSER_AUTOMATION_SKILL_ID,
        "click",
        operand="e1",
        target_url="https://example.com/",
    )
    tool.execute(
        "req-1",
        str(payload["session_id"]),
        "click",
        "e1",
        "https://example.com/",
    )


def test_high_risk_interaction_rejects_missing_independent_approval(
    tmp_path: Path,
) -> None:
    governance = MagicMock()
    governance.admission_snapshot.return_value = {
        "risk": "high",
        "admission_proven": True,
        "human_approval_required": True,
        "approval_proven": False,
    }
    tool = _tool(tmp_path, governance)
    with pytest.raises(BrowserToolError, match="lacks independent approval"):
        _execute_click(tool)
    governance.authorize_billable.assert_not_called()


def test_high_risk_interaction_rejects_snapshot_that_drops_approval_requirement(
    tmp_path: Path,
) -> None:
    governance = MagicMock()
    governance.admission_snapshot.return_value = {
        "risk": "high",
        "admission_proven": True,
        "human_approval_required": False,
        "approval_proven": True,
    }
    tool = _tool(tmp_path, governance)
    with pytest.raises(BrowserToolError, match="must require human approval"):
        _execute_click(tool)
    governance.authorize_billable.assert_not_called()
