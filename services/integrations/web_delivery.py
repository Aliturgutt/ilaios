"""Provider-neutral Web Factory deployment and rollback receipts.

The local adapter is intentionally side-effect bounded: it proves deployment
identity, content integrity, activation and rollback semantics without claiming a
public production deployment. Public providers can implement the same receipt
contract behind existing ILAIOS approval, credential and budget boundaries.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping


class WebDeploymentError(RuntimeError):
    """Raised when a governed Web deployment cannot be proven."""


@dataclass(frozen=True, slots=True)
class WebDeploymentReceipt:
    contract: str
    provider: str
    deployment_id: str
    source_commit_sha: str
    artifact_sha256: str
    live_url: str
    health: str
    rollback_reference: str | None
    deployed_at: str
    public_production_proven: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": self.contract,
            "provider": self.provider,
            "deployment_id": self.deployment_id,
            "source_commit_sha": self.source_commit_sha,
            "artifact_sha256": self.artifact_sha256,
            "live_url": self.live_url,
            "health": self.health,
            "rollback_reference": self.rollback_reference,
            "deployed_at": self.deployed_at,
            "public_production_proven": self.public_production_proven,
        }


class LocalWebDeploymentAdapter:
    """Content-addressed local production-like Web deployment boundary."""

    provider_id = "ilaios.local-web-deployment.v1"

    def __init__(self, deployment_root: Path) -> None:
        self.root = deployment_root.resolve()
        self.versions = self.root / "versions"
        self.versions.mkdir(parents=True, exist_ok=True)

    def deploy(
        self,
        project_root: Path,
        *,
        source_commit_sha: str,
        expected_artifact_sha256: str | None = None,
        now: datetime | None = None,
    ) -> WebDeploymentReceipt:
        source = project_root.resolve()
        if not source.is_dir():
            raise WebDeploymentError("Web deployment source project is missing")
        if not _valid_sha(source_commit_sha):
            raise WebDeploymentError("Web deployment source commit SHA is malformed")
        artifact_sha = tree_sha256(source)
        if expected_artifact_sha256 and artifact_sha != expected_artifact_sha256:
            raise WebDeploymentError("Web deployment artifact digest mismatch")
        deployment_id = f"web-local-{artifact_sha[:20]}"
        target = self.versions / deployment_id
        if target.exists():
            if tree_sha256(target) != artifact_sha:
                raise WebDeploymentError("existing Web deployment content was tampered")
        else:
            staging = Path(tempfile.mkdtemp(prefix="deploy-", dir=self.root))
            try:
                staged = staging / "project"
                shutil.copytree(source, staged)
                if tree_sha256(staged) != artifact_sha:
                    raise WebDeploymentError("staged Web deployment digest mismatch")
                os.replace(staged, target)
            finally:
                shutil.rmtree(staging, ignore_errors=True)

        current = self._current()
        rollback_reference = None if current is None else str(current["deployment_id"])
        record: dict[str, object] = {
            "deployment_id": deployment_id,
            "artifact_sha256": artifact_sha,
            "source_commit_sha": source_commit_sha,
            "activated_at": _timestamp(now),
            "rollback_reference": rollback_reference,
        }
        self._write_current(record)
        if self._current() != record or tree_sha256(target) != artifact_sha:
            raise WebDeploymentError("Web deployment activation health verification failed")
        return WebDeploymentReceipt(
            contract="web.deployment-receipt.v1",
            provider=self.provider_id,
            deployment_id=deployment_id,
            source_commit_sha=source_commit_sha,
            artifact_sha256=artifact_sha,
            live_url=target.as_uri(),
            health="HEALTHY_LOCAL_PRODUCTION_LIKE",
            rollback_reference=rollback_reference,
            deployed_at=str(record["activated_at"]),
            public_production_proven=False,
        )

    def rollback(
        self,
        deployment_id: str,
        *,
        source_commit_sha: str,
        now: datetime | None = None,
    ) -> WebDeploymentReceipt:
        if not deployment_id.startswith("web-local-"):
            raise WebDeploymentError("invalid Web rollback deployment identifier")
        target = self.versions / deployment_id
        if not target.is_dir():
            raise WebDeploymentError("Web rollback target does not exist")
        artifact_sha = tree_sha256(target)
        if deployment_id != f"web-local-{artifact_sha[:20]}":
            raise WebDeploymentError("Web rollback target identity does not match content")
        previous = self._current()
        previous_id = None if previous is None else str(previous["deployment_id"])
        record: dict[str, object] = {
            "deployment_id": deployment_id,
            "artifact_sha256": artifact_sha,
            "source_commit_sha": source_commit_sha,
            "activated_at": _timestamp(now),
            "rollback_reference": previous_id,
        }
        self._write_current(record)
        if self._current() != record:
            raise WebDeploymentError("Web rollback activation could not be proven")
        return WebDeploymentReceipt(
            contract="web.deployment-receipt.v1",
            provider=self.provider_id,
            deployment_id=deployment_id,
            source_commit_sha=source_commit_sha,
            artifact_sha256=artifact_sha,
            live_url=target.as_uri(),
            health="HEALTHY_LOCAL_ROLLBACK",
            rollback_reference=previous_id,
            deployed_at=str(record["activated_at"]),
            public_production_proven=False,
        )

    def current(self) -> dict[str, object] | None:
        value = self._current()
        return None if value is None else dict(value)

    def _current(self) -> dict[str, object] | None:
        path = self.root / "current.json"
        if not path.is_file():
            return None
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise WebDeploymentError("Web deployment current pointer is malformed")
        return value

    def _write_current(self, record: Mapping[str, object]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        temporary = self.root / "current.json.tmp"
        temporary.write_text(
            json.dumps(dict(record), sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, self.root / "current.json")


def tree_sha256(root: Path) -> str:
    material = bytearray()
    for path in sorted(
        (item for item in root.rglob("*") if item.is_file()),
        key=lambda item: item.relative_to(root).as_posix(),
    ):
        relative = path.relative_to(root).as_posix()
        body = path.read_bytes()
        material.extend(relative.encode("utf-8"))
        material.extend(b"\0")
        material.extend(body)
        material.extend(b"\0")
    return hashlib.sha256(bytes(material)).hexdigest()


def _timestamp(now: datetime | None) -> str:
    value = now or datetime.now(timezone.utc)
    if value.tzinfo is None:
        raise WebDeploymentError("Web deployment timestamp must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat()


def _valid_sha(value: str) -> bool:
    return len(value) == 40 and all(character in "0123456789abcdef" for character in value)


__all__ = [
    "LocalWebDeploymentAdapter",
    "WebDeploymentError",
    "WebDeploymentReceipt",
    "tree_sha256",
]
