"""Governed copy-on-write mutation of imported Web source snapshots.

This module does not decide policy, choose providers, or generate its own patch
plan. It applies an already-produced bounded revision plan only after canonical
ExecutionGrant authorization, verifies exact preimages, writes a new immutable
content-addressed source tree, and appends the receipt to the existing EvidenceStore.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Literal, Protocol

from services.evidence import EvidenceStore
from services.runtime import ExecutionGrant
from services.web_source_ingestion import WebSourceFile, WebSourceSnapshot

MAX_REVISION_OPERATIONS = 50
MAX_CHANGED_FILE_BYTES = 1 * 1024 * 1024
MAX_TOTAL_CHANGED_BYTES = 5 * 1024 * 1024
MAX_REVISION_OBJECTIVE_CHARS = 20_000
_ALLOWED_ROOTS = frozenset({"app", "pages", "components", "styles", "src"})
_ALLOWED_SUFFIXES = frozenset({".ts", ".tsx", ".js", ".jsx", ".css", ".json", ".md", ".mdx", ".html"})
_REQUEST_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_FORBIDDEN_CHANGED_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("javascript-url", re.compile(r"javascript\s*:", re.IGNORECASE)),
    ("dangerous-html", re.compile(r"dangerouslySetInnerHTML")),
    ("eval", re.compile(r"\beval\s*\(")),
    ("document-write", re.compile(r"document\.write\s*\(")),
)


class WebSourceRevisionError(RuntimeError):
    """A source revision failed a deterministic governance or integrity gate."""


class WebRevisionGrantBoundary(Protocol):
    """Existing canonical grant boundary; implementations must fail closed."""

    def authorize(
        self,
        grant: ExecutionGrant,
        *,
        subject_id: str,
        action: str,
        resource: str,
        now: datetime,
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class WebSourceRevisionRequest:
    request_id: str
    objective: str
    semantic_analysis_sha256: str | None = None

    def __post_init__(self) -> None:
        if not _REQUEST_ID.fullmatch(self.request_id):
            raise WebSourceRevisionError("Web revision request_id is invalid")
        if not self.objective or self.objective != self.objective.strip():
            raise WebSourceRevisionError("Web revision objective must be non-blank and trimmed")
        if len(self.objective) > MAX_REVISION_OBJECTIVE_CHARS:
            raise WebSourceRevisionError("Web revision objective exceeds the bounded input limit")
        if self.semantic_analysis_sha256 is not None and not _SHA256.fullmatch(
            self.semantic_analysis_sha256
        ):
            raise WebSourceRevisionError("Web revision semantic evidence digest is invalid")


@dataclass(frozen=True, slots=True)
class WebSourceRevisionOperation:
    operation: Literal["create", "replace", "delete"]
    relative_path: str
    expected_sha256: str | None = None
    content: bytes | None = None

    def __post_init__(self) -> None:
        _revision_path(self.relative_path)
        if self.operation == "create":
            if self.expected_sha256 is not None or self.content is None:
                raise WebSourceRevisionError("create requires content and no preimage digest")
        elif self.operation == "replace":
            if self.expected_sha256 is None or self.content is None:
                raise WebSourceRevisionError("replace requires content and an exact preimage digest")
        elif self.operation == "delete":
            if self.expected_sha256 is None or self.content is not None:
                raise WebSourceRevisionError("delete requires a preimage digest and no content")
        else:
            raise WebSourceRevisionError("unsupported Web source revision operation")
        if self.expected_sha256 is not None and not _SHA256.fullmatch(self.expected_sha256):
            raise WebSourceRevisionError("Web revision preimage digest is invalid")
        if self.content is not None:
            _validate_changed_content(self.relative_path, self.content)


@dataclass(frozen=True, slots=True)
class WebSourceRevisionPlan:
    plan_id: str
    source_tree_sha256: str
    operations: tuple[WebSourceRevisionOperation, ...]
    semantic_analysis_sha256: str | None = None

    def __post_init__(self) -> None:
        if not _REQUEST_ID.fullmatch(self.plan_id):
            raise WebSourceRevisionError("Web revision plan_id is invalid")
        if not _SHA256.fullmatch(self.source_tree_sha256):
            raise WebSourceRevisionError("Web revision source tree digest is invalid")
        if self.semantic_analysis_sha256 is not None and not _SHA256.fullmatch(
            self.semantic_analysis_sha256
        ):
            raise WebSourceRevisionError("Web revision plan semantic digest is invalid")
        if not self.operations:
            raise WebSourceRevisionError("Web revision plan must contain at least one operation")
        if len(self.operations) > MAX_REVISION_OPERATIONS:
            raise WebSourceRevisionError("Web revision plan exceeds the operation bound")
        paths = [item.relative_path for item in self.operations]
        if len(set(paths)) != len(paths):
            raise WebSourceRevisionError("Web revision plan contains duplicate target paths")
        total = sum(len(item.content or b"") for item in self.operations)
        if total > MAX_TOTAL_CHANGED_BYTES:
            raise WebSourceRevisionError("Web revision plan exceeds the changed-byte budget")


@dataclass(frozen=True, slots=True)
class WebSourceRevisionReceipt:
    schema_version: str
    request_id: str
    plan_id: str
    source_snapshot_id: str
    source_tree_sha256: str
    revised_snapshot_id: str
    revised_root_path: str
    revised_tree_sha256: str
    semantic_analysis_sha256: str | None
    changed_paths: tuple[str, ...]
    evidence_artifact_sha256: str
    evidence_record_hash: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "request_id": self.request_id,
            "plan_id": self.plan_id,
            "source_snapshot_id": self.source_snapshot_id,
            "source_tree_sha256": self.source_tree_sha256,
            "revised_snapshot_id": self.revised_snapshot_id,
            "revised_root_path": self.revised_root_path,
            "revised_tree_sha256": self.revised_tree_sha256,
            "semantic_analysis_sha256": self.semantic_analysis_sha256,
            "changed_paths": list(self.changed_paths),
            "evidence_artifact_sha256": self.evidence_artifact_sha256,
            "evidence_record_hash": self.evidence_record_hash,
        }


class GovernedWebSourceRevisionEngine:
    """Apply one authorized, digest-bound source plan into a derived snapshot."""

    schema_version = "ilaios.web.source-revision.v1"

    def __init__(
        self,
        artifact_root: Path,
        grants: WebRevisionGrantBoundary,
        evidence: EvidenceStore,
    ) -> None:
        self._artifact_root = artifact_root.resolve()
        if artifact_root.is_symlink():
            raise WebSourceRevisionError("Web revision artifact root must not be a symlink")
        self._revision_root = self._artifact_root / "revised-source-snapshots"
        self._revision_root.mkdir(parents=True, exist_ok=True)
        if self._revision_root.is_symlink():
            raise WebSourceRevisionError("Web revision snapshot root must not be a symlink")
        self._grants = grants
        self._evidence = evidence

    def apply(
        self,
        snapshot: WebSourceSnapshot,
        request: WebSourceRevisionRequest,
        plan: WebSourceRevisionPlan,
        *,
        grant: ExecutionGrant,
        now: datetime,
    ) -> WebSourceRevisionReceipt:
        if now.tzinfo is None:
            raise WebSourceRevisionError("Web revision time must be timezone-aware")
        if plan.source_tree_sha256 != snapshot.tree_sha256:
            raise WebSourceRevisionError("Web revision plan does not target the exact source tree")
        if request.semantic_analysis_sha256 != plan.semantic_analysis_sha256:
            raise WebSourceRevisionError("Web revision plan is not bound to the request semantic evidence")

        source_files = _verified_snapshot_files(snapshot)
        revised = dict(source_files)
        _validate_plan_preimages(revised, plan)
        for operation in plan.operations:
            if operation.operation == "delete":
                del revised[operation.relative_path]
            else:
                assert operation.content is not None
                revised[operation.relative_path] = operation.content
        _validate_revised_tree(revised)
        revised_tree_sha256, revised_inventory = _tree_digest(revised)
        if revised_tree_sha256 == snapshot.tree_sha256:
            raise WebSourceRevisionError("Web revision produced no source change")

        self._grants.authorize(
            grant,
            subject_id=grant.subject_id,
            action="web.source.revise",
            resource=snapshot.snapshot_id,
            now=now,
        )

        revised_snapshot_id = f"ilaios-web-revision-{revised_tree_sha256[:20]}"
        destination = (self._revision_root / revised_snapshot_id).resolve()
        if destination.parent != self._revision_root:
            raise WebSourceRevisionError("Web revision output escaped the artifact root")
        if destination.exists():
            observed, _ = _disk_tree_digest(destination)
            if observed != revised_tree_sha256:
                raise WebSourceRevisionError("existing Web revision snapshot integrity mismatch")
        else:
            _materialize(destination, revised)
            observed, _ = _disk_tree_digest(destination)
            if observed != revised_tree_sha256:
                shutil.rmtree(destination, ignore_errors=True)
                raise WebSourceRevisionError("Web revision output failed integrity verification")

        changed_paths = tuple(sorted(operation.relative_path for operation in plan.operations))
        evidence_payload = {
            "schema_version": self.schema_version,
            "request_id": request.request_id,
            "plan_id": plan.plan_id,
            "subject_id": grant.subject_id,
            "grant_id": grant.grant_id,
            "source_snapshot_id": snapshot.snapshot_id,
            "source_tree_sha256": snapshot.tree_sha256,
            "revised_snapshot_id": revised_snapshot_id,
            "revised_tree_sha256": revised_tree_sha256,
            "semantic_analysis_sha256": request.semantic_analysis_sha256,
            "changed_paths": list(changed_paths),
            "operations": [
                {
                    "operation": item.operation,
                    "relative_path": item.relative_path,
                    "expected_sha256": item.expected_sha256,
                    "result_sha256": hashlib.sha256(item.content).hexdigest()
                    if item.content is not None
                    else None,
                }
                for item in plan.operations
            ],
            "revised_files": [item.to_dict() for item in revised_inventory],
        }
        serialized = json.dumps(
            evidence_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        artifact = self._evidence.put_artifact(serialized)
        provenance = self._evidence.append_provenance(
            request.request_id, artifact, "web.source.revision"
        )
        return WebSourceRevisionReceipt(
            schema_version=self.schema_version,
            request_id=request.request_id,
            plan_id=plan.plan_id,
            source_snapshot_id=snapshot.snapshot_id,
            source_tree_sha256=snapshot.tree_sha256,
            revised_snapshot_id=revised_snapshot_id,
            revised_root_path=str(destination),
            revised_tree_sha256=revised_tree_sha256,
            semantic_analysis_sha256=request.semantic_analysis_sha256,
            changed_paths=changed_paths,
            evidence_artifact_sha256=artifact.digest,
            evidence_record_hash=provenance.record_hash,
        )


def _revision_path(relative_path: str) -> PurePosixPath:
    if not relative_path or "\x00" in relative_path or "\\" in relative_path:
        raise WebSourceRevisionError("Web revision path is invalid")
    if relative_path.startswith("/") or (len(relative_path) >= 2 and relative_path[1] == ":"):
        raise WebSourceRevisionError("Web revision path must be relative")
    path = PurePosixPath(relative_path)
    if any(part in {"", ".", ".."} for part in path.parts):
        raise WebSourceRevisionError("Web revision path traversal is forbidden")
    if not path.parts or path.parts[0] not in _ALLOWED_ROOTS:
        raise WebSourceRevisionError("Web revision path is outside the bounded source roots")
    if path.suffix.casefold() not in _ALLOWED_SUFFIXES:
        raise WebSourceRevisionError("Web revision file type is outside the bounded text scope")
    if len(path.as_posix()) > 240:
        raise WebSourceRevisionError("Web revision path exceeds the bounded length")
    return path


def _validate_changed_content(relative_path: str, content: bytes) -> None:
    if not content:
        raise WebSourceRevisionError("Web revision content must not be empty")
    if len(content) > MAX_CHANGED_FILE_BYTES:
        raise WebSourceRevisionError("Web revision content exceeds the per-file byte bound")
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise WebSourceRevisionError("Web revision content must be UTF-8 text") from error
    if "\x00" in text:
        raise WebSourceRevisionError("Web revision content contains a NUL byte")
    for code, pattern in _FORBIDDEN_CHANGED_PATTERNS:
        if pattern.search(text):
            raise WebSourceRevisionError(
                f"Web revision content contains forbidden source pattern: {code} ({relative_path})"
            )


def _verified_snapshot_files(snapshot: WebSourceSnapshot) -> dict[str, bytes]:
    root = Path(snapshot.root_path).resolve()
    if root.is_symlink() or not root.is_dir():
        raise WebSourceRevisionError("source snapshot root is missing or unsafe")
    expected = {item.relative_path: item for item in snapshot.files}
    observed: dict[str, bytes] = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise WebSourceRevisionError("source snapshot contains a symlink")
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        record = expected.get(relative)
        if record is None:
            raise WebSourceRevisionError("source snapshot contains an unrecorded file")
        body = path.read_bytes()
        if len(body) != record.size_bytes or hashlib.sha256(body).hexdigest() != record.sha256:
            raise WebSourceRevisionError("source snapshot file integrity mismatch")
        observed[relative] = body
    if set(observed) != set(expected):
        raise WebSourceRevisionError("source snapshot is missing recorded files")
    digest, _ = _tree_digest(observed)
    if digest != snapshot.tree_sha256:
        raise WebSourceRevisionError("source snapshot tree digest mismatch")
    return observed


def _validate_plan_preimages(files: dict[str, bytes], plan: WebSourceRevisionPlan) -> None:
    for operation in plan.operations:
        current = files.get(operation.relative_path)
        if operation.operation == "create":
            if current is not None:
                raise WebSourceRevisionError("Web revision create target already exists")
            continue
        if current is None:
            raise WebSourceRevisionError("Web revision target does not exist")
        observed = hashlib.sha256(current).hexdigest()
        if observed != operation.expected_sha256:
            raise WebSourceRevisionError("Web revision preimage digest mismatch")


def _validate_revised_tree(files: dict[str, bytes]) -> None:
    if "package.json" not in files:
        raise WebSourceRevisionError("Web revision cannot remove package.json")
    has_page = any(
        relative.startswith("app/") and PurePosixPath(relative).stem == "page"
        or relative.startswith("pages/")
        and PurePosixPath(relative).suffix.casefold() in {".js", ".jsx", ".ts", ".tsx"}
        and PurePosixPath(relative).stem not in {"_app", "_document", "_error"}
        for relative in files
    )
    if not has_page:
        raise WebSourceRevisionError("Web revision removed all application page routes")


def _tree_digest(files: dict[str, bytes]) -> tuple[str, tuple[WebSourceFile, ...]]:
    digest = hashlib.sha256()
    inventory: list[WebSourceFile] = []
    for relative, body in sorted(files.items()):
        file_sha = hashlib.sha256(body).hexdigest()
        inventory.append(WebSourceFile(relative, file_sha, len(body)))
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_sha.encode("ascii"))
        digest.update(b"\0")
        digest.update(str(len(body)).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest(), tuple(inventory)


def _materialize(destination: Path, files: dict[str, bytes]) -> None:
    destination.mkdir(parents=True, exist_ok=False)
    try:
        for relative, body in sorted(files.items()):
            target = (destination / relative).resolve()
            if destination != target and destination not in target.parents:
                raise WebSourceRevisionError("Web revision file escaped the output root")
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() or target.is_symlink():
                raise WebSourceRevisionError("Web revision output path already exists")
            target.write_bytes(body)
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise


def _disk_tree_digest(root: Path) -> tuple[str, tuple[WebSourceFile, ...]]:
    files: dict[str, bytes] = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise WebSourceRevisionError("Web revision snapshot contains a symlink")
        if path.is_file():
            files[path.relative_to(root).as_posix()] = path.read_bytes()
    return _tree_digest(files)
