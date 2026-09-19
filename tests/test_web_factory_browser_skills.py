import json
import sqlite3
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from services.agent_skills_compat import discovery_metadata
from services.runtime.browser_tool_adapter import (
    BROWSER_AGENT_ID,
    BROWSER_AUTOMATION_SKILL_ID,
    BROWSER_CAPABILITY,
    BROWSER_TOOL_NAME,
    BrowserProcessResult,
    BrowserTargetPolicy,
    BrowserToolError,
    BrowserWorkReader,
    GovernedBrowserTool,
    PlaywrightCliAdapter,
    browser_request_payload,
    browser_session_id,
    submit_browser_request,
)
from services.web_factory_skills import (
    WEB_FACTORY_BROWSER_SKILL_IDS,
    validate_web_factory_browser_skills,
    web_factory_browser_skill_plan,
)


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_browser_skill_family_is_canonical_and_portable() -> None:
    validate_web_factory_browser_skills()
    assert WEB_FACTORY_BROWSER_SKILL_IDS == (
        "ilaios-browser",
        "ilaios-browser-automate",
        "ilaios-web-e2e",
        "ilaios-visual-qa",
        "ilaios-production-verification",
    )
    assert tuple(item["skill_id"] for item in web_factory_browser_skill_plan()) == (
        WEB_FACTORY_BROWSER_SKILL_IDS
    )
    root = _root() / "tools" / "web-factory" / "browser-skills"
    for skill_id in WEB_FACTORY_BROWSER_SKILL_IDS:
        metadata = discovery_metadata(root / skill_id)
        assert metadata.name == skill_id
        text = (root / skill_id / "SKILL.md").read_text(encoding="utf-8")
        assert "Status: IMPLEMENTED" in text
        assert "Owner: ILAIOS" in text


def test_browser_provenance_is_cleanroom() -> None:
    provenance = (
        _root() / "tools" / "web-factory" / "browser-skills" / "PROVENANCE.md"
    ).read_text(encoding="utf-8")
    for marker in (
        "FIRST-PARTY ILAIOS IMPLEMENTATION",
        "CODE/TEXT IMPORTED = NONE",
        "PROMPT/SKILL TEXT IMPORTED = NONE",
        "REFERENCE IMPLEMENTATION IMPORTED = NONE",
    ):
        assert marker in provenance


def test_browser_automation_keeps_text_entry_fail_closed() -> None:
    for action in ("type", "fill"):
        with pytest.raises(BrowserToolError, match="outside the governed BrowserQA surface"):
            browser_request_payload(
                "user-1",
                "tenant-1",
                "wf-1",
                BROWSER_AUTOMATION_SKILL_ID,
                action,
                operand="sensitive-text",
                target_url="https://example.com/",
            )


def test_browser_interaction_requires_automation_skill() -> None:
    with pytest.raises(BrowserToolError, match="requires automation skill"):
        browser_request_payload(
            "user-1",
            "tenant-1",
            "wf-1",
            "ilaios-web-e2e",
            "click",
            operand="e1",
            target_url="https://example.com/",
        )


def test_browser_automation_is_submitted_as_high_risk() -> None:
    governance = MagicMock()
    governance.submit.return_value = {"status": "pending_approval"}
    result = submit_browser_request(
        governance,
        "req-1",
        "user-1",
        "tenant-1",
        "wf-1",
        BROWSER_AUTOMATION_SKILL_ID,
        "click",
        operand="e1",
        target_url="https://example.com/",
    )
    assert result == {"status": "pending_approval"}
    assert governance.submit.call_args.kwargs["risk"] == "high"


def test_browser_press_uses_bounded_control_key_allowlist() -> None:
    payload = browser_request_payload(
        "user-1",
        "tenant-1",
        "wf-1",
        BROWSER_AUTOMATION_SKILL_ID,
        "press",
        operand="Tab",
        target_url="https://example.com/",
    )
    assert payload["action"] == "press"
    with pytest.raises(BrowserToolError, match="control-key allowlist"):
        browser_request_payload(
            "user-1",
            "tenant-1",
            "wf-1",
            BROWSER_AUTOMATION_SKILL_ID,
            "press",
            operand="A",
            target_url="https://example.com/",
        )


def test_production_target_requires_https() -> None:
    policy = BrowserTargetPolicy(frozenset({"http://example.com"}))
    with pytest.raises(BrowserToolError, match="HTTPS"):
        policy.authorize("http://example.com/", production=True)


class _FakeEgress:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.calls: list[tuple[str, ...]] = []

    def run(
        self,
        *,
        allowed_origins: tuple[str, ...],
        argv: tuple[str, ...],
        cwd: Path,
        timeout_seconds: int,
    ) -> BrowserProcessResult:
        assert allowed_origins == ("https://example.com",)
        assert timeout_seconds == 60
        self.calls.append(argv)
        for arg in argv:
            if arg.startswith("--filename="):
                (cwd / arg.split("=", 1)[1]).write_text("evidence", encoding="utf-8")
        return BrowserProcessResult(
            0,
            "### Page\n- Page URL: https://example.com/\n",
            "",
            "egress-proof-1",
        )


def test_cli_requires_egress_boundary_and_hashes_artifact(tmp_path: Path) -> None:
    egress = _FakeEgress(tmp_path)
    cli = PlaywrightCliAdapter(egress, tmp_path)
    result = cli.execute(
        ("https://example.com",),
        browser_session_id("u", "t", "w"),
        "snapshot",
        None,
    )
    assert result["boundary_evidence_id"] == "egress-proof-1"
    assert isinstance(result["artifact_sha256"], str)
    assert len(egress.calls) == 1


def _create_work_db(
    path: Path,
    payload: dict[str, Any],
    *,
    skill_id: str = "ilaios-visual-qa",
) -> None:
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
                skill_id,
                BROWSER_CAPABILITY,
                json.dumps(payload, sort_keys=True, separators=(",", ":")),
                "[]",
                "pending",
                None,
            ),
        )


def test_governed_tool_binds_persisted_work_before_cli(tmp_path: Path) -> None:
    payload = browser_request_payload(
        "user-1",
        "tenant-1",
        "wf-1",
        "ilaios-visual-qa",
        "snapshot",
        target_url="https://example.com/",
    )
    db = tmp_path / "governance.db"
    _create_work_db(db, payload)
    governance = MagicMock()
    governance._database_path = db
    governance.admission_snapshot.return_value = {
        "risk": "low",
        "admission_proven": True,
    }
    governance.authorize_billable.return_value = 10
    reader = BrowserWorkReader(governance, db)
    targets = BrowserTargetPolicy(frozenset({"https://example.com"}))
    cli = PlaywrightCliAdapter(_FakeEgress(tmp_path), tmp_path / "evidence")
    audit = MagicMock()
    tool = GovernedBrowserTool(governance, reader, targets, cli, audit)
    result = tool.execute(
        "req-1",
        str(payload["session_id"]),
        "snapshot",
        None,
        "https://example.com/",
    )
    assert result["reserved_minor"] == 10
    governance.authorize_billable.assert_called_once_with("req-1")
    governance.reconcile_billable.assert_called_once()
    audit.record.assert_called_once()


def test_approved_browser_click_crosses_canonical_tool_boundary(tmp_path: Path) -> None:
    payload = browser_request_payload(
        "user-1",
        "tenant-1",
        "wf-1",
        BROWSER_AUTOMATION_SKILL_ID,
        "click",
        operand="e1",
        target_url="https://example.com/",
    )
    db = tmp_path / "governance.db"
    _create_work_db(db, payload, skill_id=BROWSER_AUTOMATION_SKILL_ID)
    governance = MagicMock()
    governance._database_path = db
    governance.admission_snapshot.return_value = {
        "risk": "high",
        "admission_proven": True,
        "human_approval_required": True,
        "approval_proven": True,
    }
    governance.authorize_billable.return_value = 10
    egress = _FakeEgress(tmp_path)
    tool = GovernedBrowserTool(
        governance,
        BrowserWorkReader(governance, db),
        BrowserTargetPolicy(frozenset({"https://example.com"})),
        PlaywrightCliAdapter(egress, tmp_path / "evidence"),
        MagicMock(),
    )
    result = tool.execute(
        "req-1",
        str(payload["session_id"]),
        "click",
        "e1",
        "https://example.com/",
    )
    assert result["action"] == "click"
    assert egress.calls[0][-2:] == ("click", "e1")
    governance.authorize_billable.assert_called_once_with("req-1")


def test_browser_click_without_approval_is_denied_before_budget(tmp_path: Path) -> None:
    payload = browser_request_payload(
        "user-1",
        "tenant-1",
        "wf-1",
        BROWSER_AUTOMATION_SKILL_ID,
        "click",
        operand="e1",
        target_url="https://example.com/",
    )
    db = tmp_path / "governance.db"
    _create_work_db(db, payload, skill_id=BROWSER_AUTOMATION_SKILL_ID)
    governance = MagicMock()
    governance._database_path = db
    governance.admission_snapshot.return_value = {
        "risk": "high",
        "admission_proven": False,
        "human_approval_required": True,
        "approval_proven": False,
    }
    tool = GovernedBrowserTool(
        governance,
        BrowserWorkReader(governance, db),
        BrowserTargetPolicy(frozenset({"https://example.com"})),
        PlaywrightCliAdapter(_FakeEgress(tmp_path), tmp_path / "evidence"),
        MagicMock(),
    )
    with pytest.raises(BrowserToolError, match="proven canonical admission"):
        tool.execute(
            "req-1",
            str(payload["session_id"]),
            "click",
            "e1",
            "https://example.com/",
        )
    governance.authorize_billable.assert_not_called()


def test_spoofed_session_is_denied_before_budget_reservation(tmp_path: Path) -> None:
    payload = browser_request_payload(
        "user-1",
        "tenant-1",
        "wf-1",
        "ilaios-visual-qa",
        "snapshot",
        target_url="https://example.com/",
    )
    db = tmp_path / "governance.db"
    _create_work_db(db, payload)
    governance = MagicMock()
    governance._database_path = db
    tool = GovernedBrowserTool(
        governance,
        BrowserWorkReader(governance, db),
        BrowserTargetPolicy(frozenset({"https://example.com"})),
        PlaywrightCliAdapter(_FakeEgress(tmp_path), tmp_path / "evidence"),
        MagicMock(),
    )
    with pytest.raises(BrowserToolError, match="session identity"):
        tool.execute(
            "req-1",
            "ilaios-000000000000000000000000",
            "snapshot",
            None,
            "https://example.com/",
        )
    governance.authorize_billable.assert_not_called()


def test_browser_tool_name_is_stable() -> None:
    assert BROWSER_TOOL_NAME == "browser.playwright-cli"
