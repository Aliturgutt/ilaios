"""Accepted Web artifact publishing through the existing Vercel boundary."""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path

import pytest

from services.control_plane import ControlPlane, ControlPlaneConfig
from services.governance import GovernedRuntimeGateway
from services.integrations.web_delivery import tree_sha256
from services.integrations.web_product_runtime import (
    DurableWebProductRuntime,
    WebProductRuntimeError,
)
from services.integrations.web_vercel_delivery import VercelWebDeploymentAdapter
from services.runtime import DurableGrantPolicy, GovernedRuntime


class _Transport:
    def __init__(self, responses: list[tuple[int, Mapping[str, object]]]) -> None:
        self._responses = deque(responses)

    def api(
        self,
        method: str,
        path: str,
        *,
        token: str,
        team_id: str,
        json_body: Mapping[str, object] | None = None,
    ) -> tuple[int, Mapping[str, object]]:
        assert token == "test-token"
        assert team_id == "team-test"
        assert self._responses
        return self._responses.popleft()

    def probe(self, url: str) -> tuple[int, str]:
        return 200, url


def _ready(deployment_id: str, source_sha: str, artifact_sha: str) -> dict[str, object]:
    return {
        "id": deployment_id,
        "readyState": "READY",
        "url": "immutable-preview.vercel.app",
        "meta": {
            "ilaiosSourceCommitSha": source_sha,
            "ilaiosArtifactSha256": artifact_sha,
            "ilaiosDeploymentContract": "web.deployment-receipt.v1",
        },
    }


def _runtime(tmp_path: Path, transport: _Transport) -> DurableWebProductRuntime:
    control = ControlPlane(ControlPlaneConfig(tmp_path / "state.sqlite3", "token"))
    grants = DurableGrantPolicy(tmp_path / "state.sqlite3")
    governance = GovernedRuntimeGateway(
        tmp_path / "governance.sqlite3", GovernedRuntime(tmp_path / "state.sqlite3"), hard_cap_minor=10
    )
    adapter = VercelWebDeploymentAdapter(
        team_id="team-test",
        project_id="project-test",
        project_name="generated-site",
        production_alias="customer.example",
        credential_provider=lambda: "test-token",
        transport=transport,
        poll_interval_seconds=0,
        sleeper=lambda _seconds: None,
    )
    return DurableWebProductRuntime(
        tmp_path / "web.sqlite3", control, grants, governance, tmp_path / "artifacts", adapter
    )


def _accepted(runtime: DurableWebProductRuntime, root: Path, *, request_id: str = "web-1") -> tuple[str, str]:
    root.mkdir()
    (root / "package.json").write_text('{"scripts":{"build":"next build"}}', encoding="utf-8")
    (root / "app.tsx").write_text("export default function App(){return null}", encoding="utf-8")
    source_sha = "a" * 40
    digest = tree_sha256(root)
    runtime._governance.submit(
        request_id, "user-1", "web-agent", "web-factory-finished-product-v1", "web", {}, (), risk="medium"
    )
    manifest = {
        "accepted": True,
        "identity_proven": True,
        "source_commit_bound": True,
        "source_commit_sha": source_sha,
        "source_project_path": str(root),
        "source_project_digest": digest,
    }
    with runtime._connect() as connection:
        connection.execute(
            "INSERT INTO web_product_requests VALUES (?, 'g', 'j', 'p', 'user-1', 'tenant-1', '{}', 'accepted', ?)",
            (request_id, __import__("json").dumps(manifest)),
        )
    return source_sha, digest


def test_preview_publish_history_and_rollback_use_one_accepted_artifact(tmp_path: Path) -> None:
    source_sha = "a" * 40
    transport = _Transport(
        [
            (201, {"id": "dpl_preview"}),
            (200, _ready("dpl_preview", source_sha, "")),
        ]
    )
    runtime = _runtime(tmp_path, transport)
    _, digest = _accepted(runtime, tmp_path / "site")
    transport._responses = deque(
        [
            (201, {"id": "dpl_preview"}),
            (200, _ready("dpl_preview", source_sha, digest)),
            (201, {"id": "dpl_live"}),
            (200, _ready("dpl_live", source_sha, digest)),
            (202, {}),
            (200, {"aliases": [{"alias": "customer.example"}]}),
            (201, {}),
            (200, _ready("dpl_live", source_sha, digest)),
            (200, {"aliases": [{"alias": "customer.example"}]}),
        ]
    )
    now = datetime(2026, 9, 4, tzinfo=timezone.utc)

    preview = runtime.preview("web-1", requester_id="user-1", tenant_id="tenant-1", now=now)
    publish_request = runtime.request_publish(
        "web-1", requester_id="user-1", tenant_id="tenant-1", now=now
    )
    assert publish_request["status"] == "pending_approval"
    decision = runtime.decide_publish(
        "web-1",
        requester_id="user-1",
        tenant_id="tenant-1",
        approver_id="independent-approver",
        decision="approved",
    )
    assert decision["status"] == "approved"
    published = runtime.publish("web-1", requester_id="user-1", tenant_id="tenant-1", now=now)
    rollback = runtime.rollback("web-1", "dpl_live", requester_id="user-1", tenant_id="tenant-1", now=now)

    assert preview["public_production_proven"] is False
    assert published["live_url"] == "https://customer.example"
    assert rollback["health"] == "HEALTHY_PUBLIC_ROLLBACK"
    assert [item["deployment_id"] for item in runtime.deployment_history("web-1", requester_id="user-1", tenant_id="tenant-1")] == ["dpl_preview", "dpl_live", "dpl_live"]


def test_cross_tenant_publish_is_denied_before_provider_access(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path, _Transport([]))
    _accepted(runtime, tmp_path / "site")

    with pytest.raises(WebProductRuntimeError, match="cross-tenant"):
        runtime.publish("web-1", requester_id="user-1", tenant_id="tenant-2", now=datetime.now(timezone.utc))


def test_publish_requires_independent_approval_before_provider_access(tmp_path: Path) -> None:
    transport = _Transport([])
    runtime = _runtime(tmp_path, transport)
    _accepted(runtime, tmp_path / "site")
    now = datetime(2026, 9, 4, tzinfo=timezone.utc)

    runtime.request_publish("web-1", requester_id="user-1", tenant_id="tenant-1", now=now)
    with pytest.raises(WebProductRuntimeError, match="approval is not proven"):
        runtime.publish("web-1", requester_id="user-1", tenant_id="tenant-1", now=now)
