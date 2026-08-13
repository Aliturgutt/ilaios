"""Isolated Software Factory producing tested review artifacts only."""

from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Any, Protocol, cast

from services.cloud import TenantBoundary
from services.governance.gates import SecurityFinanceGate, WorkRequest
from services.identity import AccessRequest, AuthorizationEngine, Principal
from services.runtime.grants import ExecutionGrant, GrantPolicy
from src.code_intelligence.models import ImpactAnalysis, RepositorySnapshot
from src.code_intelligence.repository_analyzer import RepositoryAnalyzer
from src.core.audit_engine import AuditEngine
from src.core.evidence_chain import EvidenceChain, EvidenceRecord


class SoftwareFactoryError(PermissionError):
    """Raised when a proposed self-change exceeds its isolated boundary."""


class ChangeOperation(str, Enum):
    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"
    RENAME = "rename"


class FactoryJobState(str, Enum):
    PENDING = "pending"
    PREPARED = "prepared"
    CHANGED = "changed"
    VALIDATED = "validated"
    FAILED = "failed"
    PROPOSED = "proposed"


@dataclass(frozen=True, slots=True)
class RepositoryRef:
    root: Path
    base_sha: str

    def __post_init__(self) -> None:
        if not self.root.is_absolute() or re.fullmatch(r"[0-9a-f]{40}", self.base_sha) is None:
            raise ValueError("repository root must be absolute and base_sha must be lowercase SHA-1")


@dataclass(frozen=True, slots=True)
class ExecutionPolicy:
    allowed_roots: frozenset[str]
    network_allowed: bool = False
    secrets_allowed: bool = False
    secure_mode: bool = True
    max_files: int = 100
    max_bytes: int = 10_000_000
    timeout_seconds: int = 120

    def __post_init__(self) -> None:
        if not self.allowed_roots or self.max_files < 1 or self.max_bytes < 1:
            raise ValueError("execution policy requires bounded roots and positive limits")
        if self.secure_mode and (self.network_allowed or self.secrets_allowed):
            raise ValueError("secure mode defaults deny network and secrets")


@dataclass(frozen=True, slots=True)
class Workspace:
    workspace_id: str
    path: Path
    repository: RepositoryRef


@dataclass(frozen=True, slots=True)
class Change:
    operation: ChangeOperation
    path: str
    content: bytes | None = None
    destination: str | None = None
    expected_sha256: str | None = None


@dataclass(frozen=True, slots=True)
class ChangeSet:
    changes: tuple[Change, ...]

    def __post_init__(self) -> None:
        if not self.changes:
            raise ValueError("a change set cannot be empty")


@dataclass(frozen=True, slots=True)
class ValidationPlan:
    commands: tuple[tuple[str, ...], ...] = ()


@dataclass(frozen=True, slots=True)
class ValidationResult:
    passed: bool
    checks: tuple[str, ...]
    errors: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class EvidenceBundle:
    evidence_id: str
    repository_sha: str
    changeset_sha256: str
    workspace_sha256: str
    validation: ValidationResult
    created_at: str


@dataclass(frozen=True, slots=True)
class PromotionProposal:
    proposal_id: str
    job_id: str
    evidence: EvidenceBundle
    requires_human_approval: bool = True
    production_applied: bool = False


@dataclass(frozen=True, slots=True)
class SoftwareFactoryRequest:
    request_id: str
    repository: RepositoryRef
    policy: ExecutionPolicy
    changeset: ChangeSet
    validation_plan: ValidationPlan = field(default_factory=ValidationPlan)

    def __post_init__(self) -> None:
        if not self.request_id or self.request_id != self.request_id.strip():
            raise ValueError("request_id must be non-blank and trimmed")


@dataclass(frozen=True, slots=True)
class FactoryJob:
    job_id: str
    request_id: str
    state: FactoryJobState
    workspace: Workspace | None = None
    evidence: EvidenceBundle | None = None
    error: str | None = None


class FactoryPolicyEvaluator(Protocol):
    """Integration port for the canonical policy-governance capability."""

    def permits(self, principal: Principal, request: SoftwareFactoryRequest) -> bool: ...


@dataclass(frozen=True, slots=True)
class FactoryGovernanceContext:
    principal: Principal
    access_request: AccessRequest
    execution_grant: ExecutionGrant
    tenant_region: str
    risk: str
    now: datetime


class _FactoryAuthority:
    """Unexported, identity-based capability issued only by the governed gateway."""


_GOVERNED_FACTORY_AUTHORITY = _FactoryAuthority()


class SoftwareFactory:
    """Canonical review-only multi-file Software Factory orchestration path."""

    def __init__(self, workspace_root: Path, proposal_root: Path) -> None:
        self._workspace_root = workspace_root.resolve()
        self._proposal_root = proposal_root.resolve()
        if self._workspace_root == self._proposal_root:
            raise SoftwareFactoryError("workspace and proposal stores must be separated")
        self._jobs: dict[str, FactoryJob] = {}
        self._requests: dict[str, str] = {}
        self._lock = threading.RLock()

    def submit(
        self,
        request: SoftwareFactoryRequest,
        *,
        authority: object | None = None,
    ) -> FactoryJob:
        if authority is not _GOVERNED_FACTORY_AUTHORITY:
            raise SoftwareFactoryError("direct factory execution bypass is forbidden")
        fingerprint = _request_fingerprint(request)
        with self._lock:
            previous = self._requests.get(request.request_id)
            if previous is not None:
                if previous != fingerprint:
                    raise SoftwareFactoryError("request_id conflicts with different content")
                existing = self._jobs[f"factory-{fingerprint[:20]}"]
                if existing.state not in {FactoryJobState.PROPOSED, FactoryJobState.FAILED}:
                    raise SoftwareFactoryError("request is already executing")
                return existing
            job_id = f"factory-{fingerprint[:20]}"
            job = FactoryJob(job_id, request.request_id, FactoryJobState.PENDING)
            self._requests[request.request_id] = fingerprint
            self._jobs[job_id] = job
        try:
            workspace = self._prepare_workspace(job_id, request)
            job = replace(job, state=FactoryJobState.PREPARED, workspace=workspace)
            self._jobs[job_id] = job
            self._apply_changeset(workspace.path, request.changeset, request.policy)
            job = replace(job, state=FactoryJobState.CHANGED)
            self._jobs[job_id] = job
            validation = self._validate(workspace.path, request.validation_plan, request.policy)
            if not validation.passed:
                raise SoftwareFactoryError("validation failed: " + "; ".join(validation.errors))
            evidence = _make_evidence(request, workspace.path, validation)
            job = replace(job, state=FactoryJobState.VALIDATED, evidence=evidence)
            self._jobs[job_id] = job
            self._write_proposal(job)
            job = replace(job, state=FactoryJobState.PROPOSED)
            self._jobs[job_id] = job
            return job
        except Exception as error:
            self._jobs[job_id] = replace(job, state=FactoryJobState.FAILED, error=str(error))
            raise

    def proposal(self, job_id: str) -> PromotionProposal:
        job = self._jobs.get(job_id)
        if job is None or job.state is not FactoryJobState.PROPOSED or job.evidence is None:
            raise SoftwareFactoryError("job has no validated promotion proposal")
        return PromotionProposal(f"proposal-{job.evidence.evidence_id[9:29]}", job_id, job.evidence)

    def repository_impact(
        self, request: SoftwareFactoryRequest
    ) -> tuple[RepositorySnapshot, ImpactAnalysis]:
        """Read repository state and derive validation scope without execution authority."""
        repository = request.repository.root.resolve()
        if _git_head(repository) != request.repository.base_sha:
            raise SoftwareFactoryError("repository base SHA changed")
        analyzer = RepositoryAnalyzer(repository)
        snapshot = analyzer.snapshot()
        changed = tuple(
            sorted(
                {
                    path
                    for change in request.changeset.changes
                    for path in (change.path, change.destination)
                    if path is not None
                }
            )
        )
        return snapshot, analyzer.impact(snapshot, changed)

    def promote(self, job_id: str) -> None:
        if job_id not in self._jobs:
            raise SoftwareFactoryError("unknown factory job")
        raise SoftwareFactoryError("direct production promotion is forbidden")

    def _prepare_workspace(self, job_id: str, request: SoftwareFactoryRequest) -> Workspace:
        repository = request.repository.root.resolve()
        if not repository.is_dir() or repository.is_symlink():
            raise SoftwareFactoryError("repository must be a regular directory")
        actual_sha = _git_head(repository)
        if actual_sha != request.repository.base_sha:
            raise SoftwareFactoryError("repository base SHA changed")
        if repository == self._workspace_root or repository in self._workspace_root.parents:
            raise SoftwareFactoryError("workspace store must be outside the repository")
        workspace_path = self._workspace_root / job_id
        if workspace_path.exists():
            raise SoftwareFactoryError("workspace identity already exists")
        self._workspace_root.mkdir(parents=True, exist_ok=True)
        if any(path.is_symlink() for path in repository.rglob("*")):
            raise SoftwareFactoryError("repository symlinks are outside workspace policy")
        shutil.copytree(repository, workspace_path, ignore=shutil.ignore_patterns(".git"))
        return Workspace(job_id, workspace_path, request.repository)

    def _apply_changeset(self, root: Path, changeset: ChangeSet, policy: ExecutionPolicy) -> None:
        if len(changeset.changes) > policy.max_files:
            raise SoftwareFactoryError("change set exceeds file limit")
        total = sum(len(change.content or b"") for change in changeset.changes)
        if total > policy.max_bytes:
            raise SoftwareFactoryError("change set exceeds byte limit")
        staging = root.parent / f".{root.name}-transaction"
        if staging.exists():
            raise SoftwareFactoryError("change transaction already exists")
        shutil.copytree(root, staging)
        try:
            for change in changeset.changes:
                self._apply_change(staging, change, policy)
            backup = root.parent / f".{root.name}-previous"
            root.rename(backup)
            try:
                staging.rename(root)
            except Exception:
                backup.rename(root)
                raise
            shutil.rmtree(backup)
        except Exception:
            if staging.exists():
                shutil.rmtree(staging)
            raise

    def _apply_change(self, root: Path, change: Change, policy: ExecutionPolicy) -> None:
        source = _bounded_target(root, change.path, policy.allowed_roots)
        if change.operation is ChangeOperation.CREATE:
            if source.exists() or change.content is None:
                raise SoftwareFactoryError("create requires new path and content")
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(change.content)
        elif change.operation is ChangeOperation.MODIFY:
            _require_regular_file(source, change.expected_sha256)
            if change.content is None:
                raise SoftwareFactoryError("modify requires content")
            source.write_bytes(change.content)
        elif change.operation is ChangeOperation.DELETE:
            _require_regular_file(source, change.expected_sha256)
            source.unlink()
        elif change.operation is ChangeOperation.RENAME:
            _require_regular_file(source, change.expected_sha256)
            if change.destination is None:
                raise SoftwareFactoryError("rename requires destination")
            destination = _bounded_target(root, change.destination, policy.allowed_roots)
            if destination.exists():
                raise SoftwareFactoryError("rename destination already exists")
            destination.parent.mkdir(parents=True, exist_ok=True)
            source.rename(destination)

    def _validate(self, root: Path, plan: ValidationPlan, policy: ExecutionPolicy) -> ValidationResult:
        checks = ("bounded-workspace", "default-deny-network", "default-deny-secrets")
        if plan.commands and (
            policy.secure_mode or not policy.network_allowed or not policy.secrets_allowed
        ):
            return ValidationResult(
                False,
                checks,
                ("command sandbox cannot enforce the requested network and secret policy",),
            )
        errors: list[str] = []
        for command in plan.commands:
            if not command:
                errors.append("empty validation command")
                continue
            completed = subprocess.run(command, cwd=root, check=False, capture_output=True, text=True,
                                       timeout=policy.timeout_seconds, env={"PATH": os.environ.get("PATH", "")})
            if completed.returncode:
                errors.append(f"{' '.join(command)} exited {completed.returncode}")
        return ValidationResult(not errors, checks + tuple(" ".join(c) for c in plan.commands), tuple(errors))

    def _write_proposal(self, job: FactoryJob) -> None:
        assert job.evidence is not None
        directory = self._proposal_root / job.job_id
        self._proposal_root.mkdir(parents=True, exist_ok=True)
        directory.mkdir()
        (directory / "proposal.json").write_text(
            json.dumps(_jsonable(job), sort_keys=True, separators=(",", ":")), encoding="utf-8"
        )


class GovernedSoftwareFactory:
    """Canonical SF-4 gate sequence in front of the Software Factory engine."""

    def __init__(
        self,
        factory: SoftwareFactory,
        tenants: TenantBoundary,
        authorization: AuthorizationEngine,
        policy: FactoryPolicyEvaluator,
        finance: SecurityFinanceGate,
        grants: GrantPolicy,
        audit: AuditEngine,
        evidence: EvidenceChain,
    ) -> None:
        self._factory = factory
        self._tenants = tenants
        self._authorization = authorization
        self._policy = policy
        self._finance = finance
        self._grants = grants
        self._audit = audit
        self._evidence = evidence

    def submit(
        self,
        request: SoftwareFactoryRequest,
        context: FactoryGovernanceContext,
    ) -> FactoryJob:
        details = {
            "request_id": request.request_id,
            "principal_id": context.principal.principal_id,
            "tenant_id": context.principal.tenant_id,
            "risk": context.risk,
        }
        try:
            if not context.principal.principal_id or not context.principal.tenant_id:
                raise SoftwareFactoryError("resolved actor and tenant are required")
            self._tenants.authorize(
                context.principal.tenant_id,
                resource_tenant=context.access_request.resource_tenant_id,
                region=context.tenant_region,
            )
            self._authorization.authorize(
                context.principal, context.access_request, context.now
            )
            if not self._policy.permits(context.principal, request):
                raise SoftwareFactoryError("policy denied factory execution")
            self._finance.authorize(WorkRequest(request.request_id, context.risk))
            self._grants.authorize(
                context.execution_grant,
                subject_id=context.principal.principal_id,
                action="software-factory.execute",
                resource=request.request_id,
                now=context.now,
            )
        except Exception:
            self._record_governance("denied", details)
            raise
        self._record_governance("success", details)
        job = self._factory.submit(request, authority=_GOVERNED_FACTORY_AUTHORITY)
        self._grants.record_side_effect(context.execution_grant, request.request_id)
        return job

    def _record_governance(self, status: str, details: Mapping[str, str]) -> None:
        record = self._audit.record(
            "software_factory", "governance.admission", status, details
        )
        material = json.dumps(
            {
                "timestamp": record.timestamp.isoformat(),
                "component": record.component,
                "action": record.action,
                "status": record.status,
                "details": dict(record.details),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        previous = self._evidence.get_records()
        self._evidence.add_record(
            EvidenceRecord(
                record.timestamp,
                "software_factory.governance",
                hashlib.sha256(material.encode()).hexdigest(),
                None if not previous else previous[-1].chain_hash,
            )
        )


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


def _git_head(root: Path) -> str:
    completed = subprocess.run(
        ("git", "rev-parse", "HEAD"), cwd=root, check=False, capture_output=True, text=True
    )
    sha = completed.stdout.strip()
    if completed.returncode or re.fullmatch(r"[0-9a-f]{40}", sha) is None:
        raise SoftwareFactoryError("repository HEAD is unavailable")
    return sha


def _bounded_target(root: Path, value: str, allowed_roots: frozenset[str]) -> Path:
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or ".." in path.parts or "" in path.parts:
        raise SoftwareFactoryError("change path escapes workspace")
    if path.parts[0] not in allowed_roots:
        raise SoftwareFactoryError("change path is outside the bounded allowlist")
    target = root.joinpath(*path.parts)
    resolved_parent = target.parent.resolve()
    if root.resolve() != resolved_parent and root.resolve() not in resolved_parent.parents:
        raise SoftwareFactoryError("change path escapes workspace")
    return target


def _require_regular_file(path: Path, expected_sha256: str | None) -> None:
    if not path.is_file() or path.is_symlink():
        raise SoftwareFactoryError("change target must be a regular file")
    if expected_sha256 is not None and hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha256:
        raise SoftwareFactoryError("change target hash does not match")


def _changeset_digest(changeset: ChangeSet) -> str:
    digest = hashlib.sha256()
    for change in changeset.changes:
        digest.update(change.operation.value.encode())
        digest.update(b"\0" + change.path.encode() + b"\0")
        digest.update((change.destination or "").encode() + b"\0")
        digest.update((change.expected_sha256 or "").encode() + b"\0")
        digest.update(change.content or b"")
        digest.update(b"\0")
    return digest.hexdigest()


def _request_fingerprint(request: SoftwareFactoryRequest) -> str:
    digest = hashlib.sha256()
    digest.update(request.request_id.encode() + b"\0")
    digest.update(str(request.repository.root).encode() + b"\0")
    digest.update(request.repository.base_sha.encode() + b"\0")
    digest.update(_changeset_digest(request.changeset).encode())
    digest.update(json.dumps(_jsonable(request.policy), sort_keys=True).encode())
    digest.update(json.dumps(_jsonable(request.validation_plan), sort_keys=True).encode())
    return digest.hexdigest()


def _make_evidence(
    request: SoftwareFactoryRequest, workspace: Path, validation: ValidationResult
) -> EvidenceBundle:
    changeset_sha = _changeset_digest(request.changeset)
    workspace_sha = _snapshot(workspace)
    identity = hashlib.sha256(
        request.repository.base_sha.encode() + changeset_sha.encode() + workspace_sha.encode()
    ).hexdigest()
    return EvidenceBundle(
        f"evidence-{identity}", request.repository.base_sha, changeset_sha, workspace_sha,
        validation, datetime.now(timezone.utc).isoformat()
    )


def _jsonable(value: object) -> object:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, bytes):
        return {"sha256": hashlib.sha256(value).hexdigest(), "size": len(value)}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, frozenset):
        return sorted(value)
    if hasattr(value, "__dataclass_fields__"):
        return {
            key: _jsonable(item)
            for key, item in asdict(cast(Any, value)).items()
        }
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value


def _snapshot(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode() + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()
