"""Governed, fail-closed browser tool adapter for ILAIOS BrowserQA.

The adapter is entered through the canonical ToolGateway and will not launch a
browser unless persisted governance work, admission/budget, required independent
approval, and an external egress-enforcement boundary all agree. Read/navigation
remains low/medium risk; the narrow automation surface is high-risk and approval
bound per request rather than granted as standing agent authority.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, cast
from urllib.parse import SplitResult, urlsplit

from services.governance.runtime import GovernedRuntimeGateway
from services.web_factory_skills import WEB_FACTORY_BROWSER_SKILL_IDS
from src.core.audit_engine import AuditEngine
from src.core.tool_gateway import ToolGateway

BROWSER_TOOL_NAME = "browser.playwright-cli"
BROWSER_AGENT_ID = "ilaios.agent.web.browser-qa.v1"
BROWSER_CAPABILITY = "web.verify"
BROWSER_AUTOMATION_SKILL_ID = "ilaios-browser-automate"

_LOW_RISK = frozenset({"snapshot", "find", "screenshot", "close"})
_MEDIUM_RISK = frozenset({"open", "goto", "reload"})
_HIGH_RISK = frozenset({"click", "press"})
_SUPPORTED = _LOW_RISK | _MEDIUM_RISK | _HIGH_RISK
_PAGE_URL_RE = re.compile(r"(?m)^- Page URL:\s*(\S+)\s*$")
_SESSION_RE = re.compile(r"^ilaios-[0-9a-f]{24}$")
_SAFE_PRESS_KEYS = frozenset(
    {
        "Enter",
        "Tab",
        "Shift+Tab",
        "Escape",
        "ArrowUp",
        "ArrowDown",
        "ArrowLeft",
        "ArrowRight",
        "Home",
        "End",
        "PageUp",
        "PageDown",
    }
)


class BrowserToolError(RuntimeError):
    """Browser request violated a fail-closed ILAIOS boundary."""


@dataclass(frozen=True, slots=True)
class BrowserProcessResult:
    returncode: int
    stdout: str
    stderr: str
    boundary_evidence_id: str


class BrowserEgressBoundary(Protocol):
    """Security boundary external to Playwright CLI itself.

    Implementations must enforce allowed network egress for the spawned browser,
    including redirects/subresources, and return durable boundary evidence.
    """

    def run(
        self,
        *,
        allowed_origins: tuple[str, ...],
        argv: tuple[str, ...],
        cwd: Path,
        timeout_seconds: int,
    ) -> BrowserProcessResult: ...


@dataclass(frozen=True, slots=True)
class PersistedBrowserWork:
    requester_id: str
    agent_id: str
    skill_id: str
    capability: str
    payload: dict[str, Any]
    status: str


class BrowserWorkReader:
    """Read-only binding to the canonical governance database."""

    def __init__(self, governance: GovernedRuntimeGateway, database_path: Path) -> None:
        expected = getattr(governance, "_database_path", None)
        if not isinstance(expected, Path) or expected.resolve() != database_path.resolve():
            raise BrowserToolError("browser governance database identity mismatch")
        self._database_path = database_path.resolve()

    def read(self, request_id: str) -> PersistedBrowserWork:
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(self._database_path)
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                "SELECT requester_id, agent_id, skill_id, capability, payload_json, status "
                "FROM governed_work WHERE request_id = ?",
                (request_id,),
            ).fetchone()
        except sqlite3.Error as error:
            raise BrowserToolError("browser governance evidence is unavailable") from error
        finally:
            if connection is not None:
                connection.close()
        if row is None:
            raise BrowserToolError("browser work request is not persisted")
        try:
            payload = json.loads(str(row["payload_json"]))
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            raise BrowserToolError("browser work payload is malformed") from error
        if not isinstance(payload, dict):
            raise BrowserToolError("browser work payload is malformed")
        return PersistedBrowserWork(
            str(row["requester_id"]),
            str(row["agent_id"]),
            str(row["skill_id"]),
            str(row["capability"]),
            cast(dict[str, Any], payload),
            str(row["status"]),
        )


class BrowserTargetPolicy:
    def __init__(self, allowed_origins: frozenset[str]) -> None:
        if not allowed_origins:
            raise BrowserToolError("browser requires explicit allowed origins")
        self.origins = tuple(
            sorted({_canonical_origin(_validate_http_url(item)) for item in allowed_origins})
        )

    def authorize(self, url: str | None, *, production: bool = False) -> None:
        if url is None:
            return
        parsed = _validate_http_url(url)
        if _canonical_origin(parsed) not in self.origins:
            raise BrowserToolError("browser target origin is not allowed")
        if production and parsed.scheme.lower() != "https":
            raise BrowserToolError("production browser verification requires HTTPS")

    def assert_observed(self, url: str) -> None:
        parsed = _validate_http_url(url)
        if _canonical_origin(parsed) not in self.origins:
            raise BrowserToolError("browser observed a URL outside allowed origins")


class PlaywrightCliAdapter:
    """Replaceable CLI mapping; process launch is delegated to the egress boundary."""

    def __init__(
        self,
        egress: BrowserEgressBoundary,
        evidence_root: Path,
        *,
        executable: str = "playwright-cli",
        timeout_seconds: int = 60,
    ) -> None:
        if not executable or any(char in executable for char in "\r\n\x00"):
            raise BrowserToolError("invalid browser executable")
        if timeout_seconds < 1 or timeout_seconds > 300:
            raise BrowserToolError("browser timeout must be within 1..300 seconds")
        self._egress = egress
        self._root = evidence_root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        self._executable = executable
        self._timeout = timeout_seconds

    def execute(
        self,
        allowed_origins: tuple[str, ...],
        session_id: str,
        action: str,
        operand: str | None,
    ) -> dict[str, object]:
        argv, artifact = self._command(session_id, action, operand)
        result = self._egress.run(
            allowed_origins=allowed_origins,
            argv=argv,
            cwd=self._root,
            timeout_seconds=self._timeout,
        )
        if not result.boundary_evidence_id.strip():
            raise BrowserToolError("browser egress boundary returned no evidence")
        if result.returncode != 0:
            raise BrowserToolError(f"browser CLI failed with exit code {result.returncode}")
        observed = _observed_url(result.stdout)
        artifact_sha256: str | None = None
        artifact_size: int | None = None
        if artifact is not None:
            path = self._root / artifact
            if not path.is_file():
                raise BrowserToolError("browser evidence artifact was not created")
            data = path.read_bytes()
            artifact_sha256 = hashlib.sha256(data).hexdigest()
            artifact_size = len(data)

        observation_boundary_evidence_id: str | None = None
        observation_artifact_sha256: str | None = None
        observation_artifact_size: int | None = None
        if action != "close" and observed is None:
            (
                observed,
                observation_boundary_evidence_id,
                observation_artifact_sha256,
                observation_artifact_size,
            ) = self._attest_session_url(allowed_origins, session_id)

        return {
            "tool": BROWSER_TOOL_NAME,
            "action": action,
            "observed_url": observed,
            "artifact_sha256": artifact_sha256,
            "artifact_size": artifact_size,
            "stdout_sha256": hashlib.sha256(result.stdout.encode("utf-8")).hexdigest(),
            "boundary_evidence_id": result.boundary_evidence_id,
            "observation_boundary_evidence_id": observation_boundary_evidence_id,
            "observation_artifact_sha256": observation_artifact_sha256,
            "observation_artifact_size": observation_artifact_size,
        }

    def _attest_session_url(
        self,
        allowed_origins: tuple[str, ...],
        session_id: str,
    ) -> tuple[str, str, str, int]:
        """Observe the same named session without weakening URL verification."""
        artifact = f"url-attestation-{uuid.uuid4().hex}.yaml"
        result = self._egress.run(
            allowed_origins=allowed_origins,
            argv=(
                self._executable,
                f"-s={session_id}",
                "snapshot",
                f"--filename={artifact}",
            ),
            cwd=self._root,
            timeout_seconds=self._timeout,
        )
        if not result.boundary_evidence_id.strip():
            raise BrowserToolError("browser URL attestation lacks egress evidence")
        if result.returncode != 0:
            raise BrowserToolError(
                f"browser URL attestation failed with exit code {result.returncode}"
            )
        observed = _observed_url(result.stdout)
        if observed is None:
            raise BrowserToolError("browser URL attestation returned no Page URL")
        path = self._root / artifact
        if not path.is_file():
            raise BrowserToolError("browser URL attestation artifact was not created")
        data = path.read_bytes()
        if not data:
            raise BrowserToolError("browser URL attestation artifact is empty")
        return (
            observed,
            result.boundary_evidence_id,
            hashlib.sha256(data).hexdigest(),
            len(data),
        )

    def _command(
        self, session_id: str, action: str, operand: str | None
    ) -> tuple[tuple[str, ...], str | None]:
        _validate_session(session_id)
        _validate_action(action, operand)
        prefix = (self._executable, f"-s={session_id}")
        if action in {"open", "goto", "find", "click", "press"}:
            assert operand is not None
            return ((*prefix, action, operand), None)
        if action in {"snapshot", "screenshot"}:
            extension = "yaml" if action == "snapshot" else "png"
            artifact = f"{action}-{uuid.uuid4().hex}.{extension}"
            return ((*prefix, action, f"--filename={artifact}"), artifact)
        return ((*prefix, action), None)


class GovernedBrowserTool:
    """ToolGateway handler that crosses canonical governance before browser launch."""

    def __init__(
        self,
        governance: GovernedRuntimeGateway,
        reader: BrowserWorkReader,
        targets: BrowserTargetPolicy,
        cli: PlaywrightCliAdapter,
        audit: AuditEngine,
    ) -> None:
        self._governance = governance
        self._reader = reader
        self._targets = targets
        self._cli = cli
        self._audit = audit

    def execute(
        self,
        request_id: str,
        session_id: str,
        action: str,
        operand: str | None,
        target_url: str | None,
    ) -> dict[str, object]:
        reserved = False
        amount = 0
        try:
            work = self._reader.read(request_id)
            _validate_persisted_binding(work, session_id, action, operand, target_url)
            production = work.skill_id == "ilaios-production-verification"
            self._targets.authorize(target_url, production=production)
            admission = self._governance.admission_snapshot(request_id)
            required_risk = _risk_for_action(action)
            if admission.get("risk") != required_risk:
                raise BrowserToolError("browser persisted risk classification drifted")
            if admission.get("admission_proven") is not True:
                raise BrowserToolError("browser work lacks proven canonical admission")
            if action in _HIGH_RISK:
                if work.skill_id != BROWSER_AUTOMATION_SKILL_ID:
                    raise BrowserToolError("browser interaction requires automation skill")
                if admission.get("human_approval_required") is not True:
                    raise BrowserToolError("browser interaction must require human approval")
                if admission.get("approval_proven") is not True:
                    raise BrowserToolError("browser interaction lacks independent approval")
            amount = self._governance.authorize_billable(request_id)
            reserved = True
            result = self._cli.execute(
                self._targets.origins, session_id, action, operand
            )
            observed = result.get("observed_url")
            if action != "close":
                if not isinstance(observed, str) or not observed:
                    raise BrowserToolError("browser output lacks observed Page URL evidence")
                self._targets.assert_observed(observed)
            safe_result = cast(dict[str, object], dict(result))
            self._governance.reconcile_billable(
                request_id, actual_minor=amount, status="executed", result=safe_result
            )
            self._audit.record(
                "browser-tool",
                action,
                "success",
                {"request_id": request_id, "skill_id": work.skill_id},
            )
            return {**safe_result, "request_id": request_id, "reserved_minor": amount}
        except Exception:
            if reserved:
                self._governance.reconcile_billable(
                    request_id, actual_minor=0, status="failed"
                )
            self._audit.record(
                "browser-tool",
                action,
                "failure" if reserved else "denied",
                {"request_id": request_id},
            )
            raise


def submit_browser_request(
    governance: GovernedRuntimeGateway,
    request_id: str,
    requester_id: str,
    tenant_id: str,
    workflow_id: str,
    skill_id: str,
    action: str,
    *,
    operand: str | None = None,
    target_url: str | None = None,
) -> dict[str, object]:
    payload = browser_request_payload(
        requester_id,
        tenant_id,
        workflow_id,
        skill_id,
        action,
        operand=operand,
        target_url=target_url,
    )
    return governance.submit(
        request_id,
        requester_id,
        BROWSER_AGENT_ID,
        skill_id,
        BROWSER_CAPABILITY,
        payload,
        (),
        risk=_risk_for_action(action),
    )


def browser_request_payload(
    requester_id: str,
    tenant_id: str,
    workflow_id: str,
    skill_id: str,
    action: str,
    *,
    operand: str | None = None,
    target_url: str | None = None,
) -> dict[str, Any]:
    if not all(item.strip() for item in (requester_id, tenant_id, workflow_id)):
        raise BrowserToolError("browser requester, tenant and workflow are required")
    if skill_id not in WEB_FACTORY_BROWSER_SKILL_IDS:
        raise BrowserToolError("unknown canonical browser skill")
    _validate_action(action, operand)
    if action in _HIGH_RISK and skill_id != BROWSER_AUTOMATION_SKILL_ID:
        raise BrowserToolError("browser interaction requires automation skill")
    if skill_id == BROWSER_AUTOMATION_SKILL_ID and action not in _HIGH_RISK:
        raise BrowserToolError("browser automation skill is limited to high-risk interaction")
    if action in {"open", "goto"}:
        if target_url is None or operand is None:
            raise BrowserToolError("browser navigation requires a governed target URL")
        if _canonical_url(target_url) != _canonical_url(operand):
            raise BrowserToolError("browser navigation operand diverges from target")
    elif action != "close" and target_url is None:
        raise BrowserToolError("browser action requires expected current URL")
    if target_url is not None:
        _validate_http_url(target_url)
    return {
        "schema_version": 1,
        "tenant_id": tenant_id,
        "workflow_id": workflow_id,
        "session_id": browser_session_id(requester_id, tenant_id, workflow_id),
        "action": action,
        "operand": operand,
        "target_url": target_url,
    }


def build_browser_tool_gateway(
    gateway: ToolGateway,
    governance: GovernedRuntimeGateway,
    governance_database_path: Path,
    allowed_origins: frozenset[str],
    egress: BrowserEgressBoundary,
    audit: AuditEngine,
    evidence_root: Path,
    *,
    executable: str = "playwright-cli",
    timeout_seconds: int = 60,
) -> ToolGateway:
    reader = BrowserWorkReader(governance, governance_database_path)
    targets = BrowserTargetPolicy(allowed_origins)
    cli = PlaywrightCliAdapter(
        egress, evidence_root, executable=executable, timeout_seconds=timeout_seconds
    )
    gateway.register_handler(
        BROWSER_TOOL_NAME,
        GovernedBrowserTool(governance, reader, targets, cli, audit).execute,
    )
    return gateway


def browser_session_id(requester_id: str, tenant_id: str, workflow_id: str) -> str:
    digest = hashlib.sha256(
        f"{requester_id}\0{tenant_id}\0{workflow_id}".encode("utf-8")
    ).hexdigest()[:24]
    return f"ilaios-{digest}"


def _validate_persisted_binding(
    work: PersistedBrowserWork,
    session_id: str,
    action: str,
    operand: str | None,
    target_url: str | None,
) -> None:
    if work.status != "pending":
        raise BrowserToolError("browser work is not pending")
    if work.agent_id != BROWSER_AGENT_ID or work.capability != BROWSER_CAPABILITY:
        raise BrowserToolError("browser work exceeds canonical BrowserQA authority")
    if work.skill_id not in WEB_FACTORY_BROWSER_SKILL_IDS:
        raise BrowserToolError("persisted browser skill is not canonical")
    expected = browser_request_payload(
        work.requester_id,
        _payload_text(work.payload, "tenant_id"),
        _payload_text(work.payload, "workflow_id"),
        work.skill_id,
        action,
        operand=operand,
        target_url=target_url,
    )
    if json.dumps(expected, sort_keys=True, separators=(",", ":")) != json.dumps(
        work.payload, sort_keys=True, separators=(",", ":")
    ):
        raise BrowserToolError("browser action diverges from persisted governed work")
    if expected["session_id"] != session_id:
        raise BrowserToolError("browser session identity diverges from governed work")


def _risk_for_action(action: str) -> str:
    if action in _HIGH_RISK:
        return "high"
    if action in _MEDIUM_RISK:
        return "medium"
    return "low"


def _validate_action(action: str, operand: str | None) -> None:
    if action not in _SUPPORTED:
        raise BrowserToolError("browser action is outside the governed BrowserQA surface")
    if action in {"open", "goto", "find", "click", "press"} and (
        operand is None or not operand.strip()
    ):
        raise BrowserToolError("browser action requires a non-empty operand")
    if action not in {"open", "goto", "find", "click", "press"} and operand is not None:
        raise BrowserToolError("browser action does not accept an operand")
    if operand is not None and (
        len(operand) > 512 or any(char in operand for char in "\r\n\x00")
    ):
        raise BrowserToolError("browser action operand is malformed")
    if action == "press" and operand not in _SAFE_PRESS_KEYS:
        raise BrowserToolError("browser press key is outside the bounded control-key allowlist")


def _validate_session(session_id: str) -> None:
    if _SESSION_RE.fullmatch(session_id) is None:
        raise BrowserToolError("browser session identifier is invalid")


def _observed_url(stdout: str) -> str | None:
    match = _PAGE_URL_RE.search(stdout)
    if match is None:
        return None
    return match.group(1)


def _validate_http_url(value: str) -> SplitResult:
    if not isinstance(value, str) or not value.strip():
        raise BrowserToolError("browser URL is required")
    if len(value) > 2048 or any(char in value for char in "\r\n\x00"):
        raise BrowserToolError("browser URL is malformed")
    parsed = urlsplit(value.strip())
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise BrowserToolError("browser URL must be absolute HTTP(S)")
    if parsed.username is not None or parsed.password is not None:
        raise BrowserToolError("browser URL may not contain credentials")
    return parsed


def _canonical_origin(parsed: SplitResult) -> str:
    scheme = parsed.scheme.lower()
    host = parsed.hostname.lower() if parsed.hostname else ""
    port = parsed.port
    if port is None or (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
        return f"{scheme}://{host}"
    return f"{scheme}://{host}:{port}"


def _canonical_url(value: str) -> str:
    parsed = _validate_http_url(value)
    path = parsed.path or "/"
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{_canonical_origin(parsed)}{path}{query}"


def _payload_text(payload: dict[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise BrowserToolError(f"browser payload field is invalid: {field}")
    return value
