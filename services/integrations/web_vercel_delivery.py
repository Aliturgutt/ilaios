"""Governed Vercel delivery boundary for certified Web Factory source.

The adapter implements the existing ``web.deployment-receipt.v1`` contract. It is
not a routing, policy, approval, credential or budget authority. Callers must prove
those decisions before invoking a public side effect. Production is considered
proven only after Vercel reports READY, ILAIOS provenance metadata round-trips,
the immutable deployment URL is healthy, production traffic is promoted, a
production alias exists, and HTTPS health passes again on that alias.
"""

from __future__ import annotations

import base64
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Mapping, Protocol, cast

import requests

from .web_delivery import (
    WebDeploymentError,
    WebDeploymentReceipt,
    _timestamp,
    _valid_sha,
    tree_sha256,
)


class VercelDeploymentTransport(Protocol):
    """Small injectable transport so provider behavior is deterministic in tests."""

    def api(
        self,
        method: str,
        path: str,
        *,
        token: str,
        team_id: str,
        json_body: Mapping[str, object] | None = None,
    ) -> tuple[int, Mapping[str, object]]: ...

    def probe(self, url: str) -> tuple[int, str]: ...


class RequestsVercelDeploymentTransport:
    """HTTPS transport for the Vercel REST API and public health probes."""

    def __init__(self, *, timeout_seconds: float = 30.0) -> None:
        if timeout_seconds <= 0:
            raise ValueError("Vercel transport timeout must be positive")
        self.timeout_seconds = timeout_seconds

    def api(
        self,
        method: str,
        path: str,
        *,
        token: str,
        team_id: str,
        json_body: Mapping[str, object] | None = None,
    ) -> tuple[int, Mapping[str, object]]:
        if not path.startswith("/"):
            raise WebDeploymentError("Vercel API path must be absolute")
        response = requests.request(
            method,
            f"https://api.vercel.com{path}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            params={"teamId": team_id},
            json=None if json_body is None else dict(json_body),
            timeout=self.timeout_seconds,
        )
        try:
            value = response.json()
        except ValueError:
            value = {}
        if not isinstance(value, dict):
            value = {"payload": value}
        return response.status_code, cast(dict[str, object], value)

    def probe(self, url: str) -> tuple[int, str]:
        response = requests.get(
            url,
            timeout=self.timeout_seconds,
            allow_redirects=True,
        )
        return response.status_code, response.url


class VercelWebDeploymentAdapter:
    """Fail-closed Vercel production deploy, promote, health and rollback adapter."""

    provider_id = "vercel.web-deployment.v1"
    deployment_contract = "web.deployment-receipt.v1"

    def __init__(
        self,
        *,
        team_id: str,
        project_id: str,
        project_name: str,
        credential_provider: Callable[[], str],
        transport: VercelDeploymentTransport | None = None,
        max_poll_attempts: int = 30,
        poll_interval_seconds: float = 2.0,
        max_inline_bytes: int = 8 * 1024 * 1024,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if not team_id.strip():
            raise ValueError("Vercel team identifier is required")
        if not project_id.strip() or "/" in project_id:
            raise ValueError("Vercel project identifier is invalid")
        if not project_name.strip():
            raise ValueError("Vercel project name is required")
        if max_poll_attempts < 1:
            raise ValueError("Vercel poll attempt budget must be positive")
        if poll_interval_seconds < 0:
            raise ValueError("Vercel poll interval cannot be negative")
        if max_inline_bytes < 1:
            raise ValueError("Vercel inline byte budget must be positive")
        self.team_id = team_id.strip()
        self.project_id = project_id.strip()
        self.project_name = project_name.strip()
        self._credential_provider = credential_provider
        self._transport = transport or RequestsVercelDeploymentTransport()
        self._max_poll_attempts = max_poll_attempts
        self._poll_interval_seconds = poll_interval_seconds
        self._max_inline_bytes = max_inline_bytes
        self._sleeper = sleeper

    def deploy(
        self,
        project_root: Path,
        *,
        source_commit_sha: str,
        expected_artifact_sha256: str | None = None,
        rollback_reference: str | None = None,
        authorization_proven: bool,
        budget_proven: bool,
        now: datetime | None = None,
    ) -> WebDeploymentReceipt:
        self._assert_public_side_effect_authorized(
            authorization_proven=authorization_proven,
            budget_proven=budget_proven,
        )
        source = project_root.resolve()
        if not source.is_dir():
            raise WebDeploymentError("Vercel Web deployment source project is missing")
        if not _valid_sha(source_commit_sha):
            raise WebDeploymentError("Vercel Web source commit SHA is malformed")
        artifact_sha = tree_sha256(source)
        if expected_artifact_sha256 and artifact_sha != expected_artifact_sha256:
            raise WebDeploymentError("Vercel Web deployment artifact digest mismatch")
        files = self._inline_project_files(source)
        token = self._credential()
        create_body: dict[str, object] = {
            "name": self.project_name,
            "project": self.project_id,
            "files": files,
            "gitMetadata": {
                "commitRef": "ilaios-generated",
                "commitSha": source_commit_sha,
                "dirty": False,
                "ci": True,
                "ciType": "ilaios",
            },
            "meta": self._provenance(source_commit_sha, artifact_sha),
            "projectSettings": {
                "framework": "nextjs",
                "buildCommand": "npm run build",
                "installCommand": "npm install",
            },
            "target": "production",
        }
        status, created = self._transport.api(
            "POST",
            "/v13/deployments",
            token=token,
            team_id=self.team_id,
            json_body=create_body,
        )
        if status not in {200, 201, 202}:
            raise WebDeploymentError(
                f"Vercel deployment creation failed with HTTP {status}"
            )
        deployment_id = _required_string(created, "id", "Vercel deployment id")
        ready = self._await_ready(deployment_id, token=token)
        self._assert_provider_provenance(
            ready,
            source_commit_sha=source_commit_sha,
            artifact_sha256=artifact_sha,
        )
        preview_url = self._deployment_url(ready)
        self._assert_healthy_https(preview_url)
        self._promote(deployment_id, token=token)
        live_url = self._production_alias(deployment_id, token=token)
        self._assert_healthy_https(live_url)
        return WebDeploymentReceipt(
            contract=self.deployment_contract,
            provider=self.provider_id,
            deployment_id=deployment_id,
            source_commit_sha=source_commit_sha,
            artifact_sha256=artifact_sha,
            live_url=live_url,
            health="HEALTHY_PUBLIC_PRODUCTION",
            rollback_reference=rollback_reference,
            deployed_at=_timestamp(now),
            public_production_proven=True,
        )

    def rollback(
        self,
        deployment_id: str,
        *,
        source_commit_sha: str,
        expected_artifact_sha256: str,
        replaced_deployment_id: str | None = None,
        authorization_proven: bool,
        budget_proven: bool,
        now: datetime | None = None,
    ) -> WebDeploymentReceipt:
        self._assert_public_side_effect_authorized(
            authorization_proven=authorization_proven,
            budget_proven=budget_proven,
        )
        if not deployment_id.startswith("dpl_"):
            raise WebDeploymentError("Vercel rollback deployment id is malformed")
        if not _valid_sha(source_commit_sha):
            raise WebDeploymentError("Vercel rollback source commit SHA is malformed")
        if len(expected_artifact_sha256) != 64 or any(
            character not in "0123456789abcdef"
            for character in expected_artifact_sha256
        ):
            raise WebDeploymentError("Vercel rollback artifact digest is malformed")
        token = self._credential()
        status, _ = self._transport.api(
            "POST",
            f"/v1/projects/{self.project_id}/rollback/{deployment_id}",
            token=token,
            team_id=self.team_id,
            json_body={"description": "ILAIOS governed Web Factory rollback"},
        )
        if status not in {200, 201, 202, 204}:
            raise WebDeploymentError(
                f"Vercel rollback request failed with HTTP {status}"
            )
        ready = self._await_ready(deployment_id, token=token)
        self._assert_provider_provenance(
            ready,
            source_commit_sha=source_commit_sha,
            artifact_sha256=expected_artifact_sha256,
        )
        preview_url = self._deployment_url(ready)
        self._assert_healthy_https(preview_url)
        live_url = self._production_alias(deployment_id, token=token)
        self._assert_healthy_https(live_url)
        return WebDeploymentReceipt(
            contract=self.deployment_contract,
            provider=self.provider_id,
            deployment_id=deployment_id,
            source_commit_sha=source_commit_sha,
            artifact_sha256=expected_artifact_sha256,
            live_url=live_url,
            health="HEALTHY_PUBLIC_ROLLBACK",
            rollback_reference=replaced_deployment_id,
            deployed_at=_timestamp(now),
            public_production_proven=True,
        )

    def _assert_public_side_effect_authorized(
        self,
        *,
        authorization_proven: bool,
        budget_proven: bool,
    ) -> None:
        if authorization_proven is not True:
            raise WebDeploymentError("public Web deployment authorization is not proven")
        if budget_proven is not True:
            raise WebDeploymentError("public Web deployment budget is not proven")

    def _credential(self) -> str:
        token = self._credential_provider().strip()
        if not token:
            raise WebDeploymentError("Vercel credential is unavailable")
        return token

    def _inline_project_files(self, source: Path) -> list[dict[str, object]]:
        ignored_parts = {".git", ".next", "node_modules"}
        files: list[dict[str, object]] = []
        total = 0
        for path in sorted(
            (item for item in source.rglob("*") if item.is_file()),
            key=lambda item: item.relative_to(source).as_posix(),
        ):
            relative = path.relative_to(source)
            if any(part in ignored_parts for part in relative.parts):
                continue
            if path.name == ".env" or (
                path.name.startswith(".env.") and path.name != ".env.example"
            ):
                raise WebDeploymentError(
                    "Vercel Web deployment source contains an environment secret file"
                )
            body = path.read_bytes()
            total += len(body)
            if total > self._max_inline_bytes:
                raise WebDeploymentError(
                    "Vercel inline deployment exceeds bounded upload budget"
                )
            files.append(
                {
                    "file": relative.as_posix(),
                    "data": base64.b64encode(body).decode("ascii"),
                    "encoding": "base64",
                }
            )
        if not files:
            raise WebDeploymentError("Vercel Web deployment contains no source files")
        if not any(item["file"] == "package.json" for item in files):
            raise WebDeploymentError("Vercel Web deployment package.json is missing")
        return files

    def _await_ready(
        self,
        deployment_id: str,
        *,
        token: str,
    ) -> Mapping[str, object]:
        for attempt in range(self._max_poll_attempts):
            status, value = self._transport.api(
                "GET",
                f"/v13/deployments/{deployment_id}",
                token=token,
                team_id=self.team_id,
            )
            if status != 200:
                raise WebDeploymentError(
                    f"Vercel deployment reconciliation failed with HTTP {status}"
                )
            ready_state = str(value.get("readyState", value.get("status", "")))
            if ready_state == "READY":
                if value.get("id") != deployment_id:
                    raise WebDeploymentError("Vercel deployment identity changed")
                return value
            if ready_state in {"ERROR", "CANCELED", "CANCELLED"}:
                raise WebDeploymentError(
                    f"Vercel deployment reached terminal state {ready_state}"
                )
            if attempt + 1 < self._max_poll_attempts:
                self._sleeper(self._poll_interval_seconds)
        raise WebDeploymentError("Vercel deployment readiness budget was exhausted")

    def _assert_provider_provenance(
        self,
        deployment: Mapping[str, object],
        *,
        source_commit_sha: str,
        artifact_sha256: str,
    ) -> None:
        metadata = deployment.get("meta")
        if not isinstance(metadata, dict):
            raise WebDeploymentError("Vercel deployment provenance metadata is missing")
        if metadata.get("ilaiosSourceCommitSha") != source_commit_sha:
            raise WebDeploymentError("Vercel deployment source SHA provenance mismatch")
        if metadata.get("ilaiosArtifactSha256") != artifact_sha256:
            raise WebDeploymentError("Vercel deployment artifact provenance mismatch")
        if metadata.get("ilaiosDeploymentContract") != self.deployment_contract:
            raise WebDeploymentError("Vercel deployment contract provenance mismatch")

    def _deployment_url(self, deployment: Mapping[str, object]) -> str:
        value = deployment.get("url")
        if not isinstance(value, str) or not value.strip():
            raise WebDeploymentError("Vercel immutable deployment URL is missing")
        return _https_url(value)

    def _promote(self, deployment_id: str, *, token: str) -> None:
        status, _ = self._transport.api(
            "POST",
            f"/v10/projects/{self.project_id}/promote/{deployment_id}",
            token=token,
            team_id=self.team_id,
        )
        if status not in {200, 201, 202, 204}:
            raise WebDeploymentError(
                f"Vercel production promotion failed with HTTP {status}"
            )

    def _production_alias(self, deployment_id: str, *, token: str) -> str:
        status, value = self._transport.api(
            "GET",
            f"/v2/deployments/{deployment_id}/aliases",
            token=token,
            team_id=self.team_id,
        )
        if status != 200:
            raise WebDeploymentError(
                f"Vercel production alias lookup failed with HTTP {status}"
            )
        aliases = value.get("aliases")
        if not isinstance(aliases, list) or not aliases:
            raise WebDeploymentError("Vercel production alias is not proven")
        for item in aliases:
            alias: object | None
            if isinstance(item, str):
                alias = item
            elif isinstance(item, dict):
                alias = item.get("alias")
            else:
                alias = None
            if isinstance(alias, str) and alias.strip():
                return _https_url(alias)
        raise WebDeploymentError("Vercel production alias is malformed")

    def _assert_healthy_https(self, live_url: str) -> None:
        if not live_url.startswith("https://"):
            raise WebDeploymentError("Vercel production URL is not HTTPS")
        status, final_url = self._transport.probe(live_url)
        if status < 200 or status >= 400:
            raise WebDeploymentError(
                f"Vercel production health probe failed with HTTP {status}"
            )
        if not final_url.startswith("https://"):
            raise WebDeploymentError("Vercel production health redirected away from HTTPS")

    def _provenance(
        self,
        source_commit_sha: str,
        artifact_sha256: str,
    ) -> dict[str, str]:
        return {
            "ilaiosSourceCommitSha": source_commit_sha,
            "ilaiosArtifactSha256": artifact_sha256,
            "ilaiosDeploymentContract": self.deployment_contract,
        }


def _required_string(
    value: Mapping[str, object],
    key: str,
    description: str,
) -> str:
    candidate = value.get(key)
    if not isinstance(candidate, str) or not candidate.strip():
        raise WebDeploymentError(f"{description} is missing")
    return candidate.strip()


def _https_url(value: str) -> str:
    normalized = value.strip().rstrip("/")
    if normalized.startswith("https://"):
        return normalized
    if "://" in normalized:
        raise WebDeploymentError("Vercel production alias uses a non-HTTPS scheme")
    return f"https://{normalized}"


__all__ = [
    "RequestsVercelDeploymentTransport",
    "VercelDeploymentTransport",
    "VercelWebDeploymentAdapter",
]
