"""Isolated Software Factory producing tested review artifacts only."""

from __future__ import annotations

import difflib
import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


class SoftwareFactoryError(PermissionError):
    """Raised when a proposed self-change exceeds its isolated boundary."""


@dataclass(frozen=True, slots=True)
class ChangeProposal:
    proposal_id: str
    target_path: str
    original_hash: str
    content_hash: str
    patch_path: str
    test_log_path: str
    test_exit_code: int
    production_snapshot_before: str
    production_snapshot_after: str
    requires_human_approval: bool = True
    production_applied: bool = False


class IsolatedSoftwareFactory:
    """Run a fixed test gate with production hidden in a mount namespace."""

    def __init__(
        self,
        production_root: Path,
        workspace_root: Path,
        proposal_root: Path,
        allowed_roots: frozenset[str],
    ) -> None:
        self._production = production_root.resolve()
        self._workspace_root = workspace_root.resolve()
        self._proposal_root = proposal_root.resolve()
        self._allowed_roots = allowed_roots
        if not self._production.is_dir():
            raise SoftwareFactoryError("production root is unavailable")
        if self._production in self._workspace_root.parents:
            raise SoftwareFactoryError("workspace must be outside production")
        if self._production in self._proposal_root.parents:
            raise SoftwareFactoryError("proposal store must be outside production")
        if shutil.which("unshare") is None or shutil.which("mount") is None:
            raise SoftwareFactoryError("mount-namespace isolation is unavailable")

    def propose(self, target_path: str, content: bytes) -> ChangeProposal:
        relative = self._bounded_path(target_path)
        target = self._production / relative
        if not target.is_file() or target.is_symlink():
            raise SoftwareFactoryError("target must be a regular production file")
        before = _snapshot(self._production)
        original = target.read_bytes()
        patch = "".join(
            difflib.unified_diff(
                original.decode("utf-8").splitlines(keepends=True),
                content.decode("utf-8").splitlines(keepends=True),
                fromfile=f"a/{relative.as_posix()}",
                tofile=f"b/{relative.as_posix()}",
            )
        ).encode()
        if not patch:
            raise SoftwareFactoryError("proposal must contain a real patch")
        identity = hashlib.sha256(
            relative.as_posix().encode() + b"\0" + original + b"\0" + content + b"\0" + patch
        ).hexdigest()
        proposal_id = f"change-{identity[:20]}"
        workspace = self._workspace_root / proposal_id
        proposal_dir = self._proposal_root / proposal_id
        if workspace.exists() or proposal_dir.exists():
            raise SoftwareFactoryError("proposal identity already exists")
        self._workspace_root.mkdir(parents=True, exist_ok=True)
        self._proposal_root.mkdir(parents=True, exist_ok=True)
        if any(path.is_symlink() for path in self._production.rglob("*")):
            raise SoftwareFactoryError("production symlinks are outside isolation policy")
        shutil.copytree(self._production, workspace)
        (workspace / relative).write_bytes(content)
        proposal_dir.mkdir()
        patch_path = proposal_dir / "change.patch"
        patch_path.write_bytes(patch)
        test_log_path = proposal_dir / "test.log"
        completed = self._run_isolated_tests(workspace)
        test_log_path.write_text(
            completed.stdout + completed.stderr, encoding="utf-8"
        )
        after = _snapshot(self._production)
        if before != after:
            raise SoftwareFactoryError("production changed during isolated validation")
        proposal = ChangeProposal(
            proposal_id,
            relative.as_posix(),
            hashlib.sha256(original).hexdigest(),
            hashlib.sha256(content).hexdigest(),
            str(patch_path),
            str(test_log_path),
            completed.returncode,
            before,
            after,
        )
        (proposal_dir / "proposal.json").write_text(
            json.dumps(asdict(proposal), sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )
        if completed.returncode != 0:
            raise SoftwareFactoryError("isolated proposal tests failed")
        return proposal

    def approve_for_review(self, proposal_id: str, approver: str) -> Path:
        if not approver or approver != approver.strip():
            raise SoftwareFactoryError("human approver is required")
        proposal_dir = self._proposal_root / proposal_id
        if not (proposal_dir / "proposal.json").is_file():
            raise SoftwareFactoryError("unknown review proposal")
        approval = proposal_dir / "approval.json"
        try:
            with approval.open("x", encoding="utf-8") as stream:
                json.dump(
                    {
                        "approver": approver,
                        "decision": "approved_for_external_review",
                        "decided_at": datetime.now(timezone.utc).isoformat(),
                    },
                    stream,
                    sort_keys=True,
                )
        except FileExistsError as error:
            raise SoftwareFactoryError("review proposal already decided") from error
        return approval

    def apply_to_production(self, proposal: ChangeProposal) -> None:
        del proposal
        raise SoftwareFactoryError("autonomous direct production mutation is forbidden")

    def _bounded_path(self, target_path: str) -> PurePosixPath:
        path = PurePosixPath(target_path)
        if path.is_absolute() or ".." in path.parts or not path.parts:
            raise SoftwareFactoryError("target path escapes isolation")
        if path.parts[0] not in self._allowed_roots:
            raise SoftwareFactoryError("target path is outside the bounded allowlist")
        return path

    def _run_isolated_tests(self, workspace: Path) -> subprocess.CompletedProcess[str]:
        hidden = self._workspace_root / f".{workspace.name}-hidden-production"
        hidden.mkdir()
        script = (
            'production="$1"; hidden="$2"; workspace="$3"; shift 3; '
            'mount --bind "$hidden" "$production"; '
            'mount -o remount,bind,ro "$production"; '
            'cd "$workspace"; exec "$@"'
        )
        return subprocess.run(
            (
                "unshare",
                "--user",
                "--map-root-user",
                "--mount",
                "--net",
                "sh",
                "-c",
                script,
                "ilaios-factory",
                str(self._production),
                str(hidden),
                str(workspace),
                sys.executable,
                "-m",
                "pytest",
                "-q",
            ),
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
            env={
                "ILAIOS_FACTORY_PRODUCTION_PATH": str(self._production),
                "PATH": os.environ.get("PATH", ""),
                "PYTHONPATH": str(workspace),
            },
        )


def _snapshot(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode() + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()
