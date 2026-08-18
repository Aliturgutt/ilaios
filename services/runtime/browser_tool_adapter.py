"""Governed, fail-closed browser tool adapter for ILAIOS BrowserQA.

The adapter is intentionally read/navigation-only. It is entered through the
canonical ToolGateway and will not launch a browser unless persisted governance
work, admission/budget and an external egress-enforcement boundary all agree.
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

_LOW_RISK = frozenset({"snapshot", "find", "screenshot", "close"})
_MEDIUM_RISK = frozenset({"open", "goto", "reload"})
_SUPPORTED = _LOW_RISK | _MEDIUM_RISK
_PAGE_URL_RE = re.compile(r"(?m)^- Page URL:\s*(\S+)\s*$")
_SESSION_RE = re.compile(r"^ilaios-[0-9a-f]{24}$")


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
        return {
            "tool": BROWSER_TOOL_NAME,
            "action": action,
            "observed_url": observed,
            "artifact_sha256": artifact_sha256,
            "artifact_size": artifact_size,
            "stdout_sha256": hashlib.sha256(result.stdout.encode("utf-8")).hexdigest(),
            "boundary_evidence_id": result.boundary_evidence_id,
        }

    def _command(
        self, session_id: str, action: str, operand: str | None
    ) -> tuple[tuple[str, ...], str | None]:
        _validate_session(session_id)
        _validate_action(action, operand)
        prefix = (self._executable, f"-s={session_id}")
        if action in {"open", "goto"}:
            assert operand is not None
            return ((*prefix, action, operand), None)
        if action == "find":
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
            required_risk = "medium" if action in _MEDIUM_RISK else "low"
            if admission.get("risk") != required_risk:
                raise BrowserToolError("browser persisted risk classification drifted")
            if admission.get("admission_proven") is not True:
                raise BrowserToolError("browser work lacks proven canonical admission")
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
        risk="medium" if action in _MEDIUM_RISK else "low",
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


def _validate_action(action: str, operand: str | None) -> None:
    if action not in _SUPPORTED:
        raise BrowserToolError("browser action is not exposed by read-only v0")
    if action in {"open", "goto"}:
        if operand is None:
            raise BrowserToolError("browser navigation requires URL")
        _validate_http_url(operand)
    elif action == "find":
        if operand is None or not operand.strip() or len(operand) > 512 or operand.startswith("-"):
            raise BrowserToolError("browser find query is invalid")
    elif operand is not None:
        raise BrowserToolError(f"browser action {action} does not accept an operand")


def _payload_text(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise BrowserToolError(f"persisted browser payload lacks {key}")
    return value


def _validate_session(session_id: str) -> None:
    if _SESSION_RE.fullmatch(session_id) is None:
        raise BrowserToolError("browser session is not ILAIOS-scoped")


def _validate_http_url(value: str) -> SplitResult:
    if len(value) > 4096 or any(char in value for char in "\r\n\x00"):
        raise BrowserToolError("browser URL is malformed")
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        parsed.port
    except ValueError as error:
        raise BrowserToolError("browser URL is malformed") from error
    if parsed.scheme.lower() not in {"http", "https"} or not hostname:
        raise BrowserToolError("browser target must use HTTP(S)")
    if parsed.username is not None or parsed.password is not None:
        raise BrowserToolError("credentials are forbidden in browser URLs")
    return parsed


def _canonical_origin(parsed: SplitResult) -> str:
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower()
    port = parsed.port
    default = (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    return f"{scheme}://{host}" + ("" if port is None or default else f":{port}")


def _canonical_url(value: str) -> str:
    parsed = _validate_http_url(value)
    path = parsed.path or "/"
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{_canonical_origin(parsed)}{path}{query}"


def _observed_url(stdout: str) -> str | None:
    match = _PAGE_URL_RE.search(stdout)
    return None if match is None else match.group(1)
