"""Artifact-bound execution boundary for selective Video Factory repairs.

The existing ``SelectiveRepairController`` decides *what* bounded target may be
repaired and enforces attempt limits. This module executes one already-approved
``RepairRequest`` through an injected action, verifies exact source/output
artifacts, and emits immutable evidence. It does not choose repair targets,
select providers, grant authority, or orchestrate retries.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Protocol

from .video_skills import RepairRequest


class SelectiveRepairExecutionError(ValueError):
    """Raised when bounded repair execution cannot be evidenced safely."""


@dataclass(frozen=True, slots=True)
class RepairExecutionEvidence:
    """Immutable evidence for one bounded repair attempt."""

    repair_id: str
    finding_id: str
    target: str
    attempt: int
    source_artifact_sha256: str
    output_artifact_sha256: str
    output_path: str
    output_byte_length: int
    executor_id: str
    provenance_reference: str

    def __post_init__(self) -> None:
        for name in (
            "repair_id",
            "finding_id",
            "target",
            "output_path",
            "executor_id",
            "provenance_reference",
        ):
            _require_text(name, getattr(self, name))
        if self.attempt <= 0:
            raise SelectiveRepairExecutionError("repair attempt must be positive")
        _require_sha256(self.source_artifact_sha256)
        _require_sha256(self.output_artifact_sha256)
        if self.source_artifact_sha256 == self.output_artifact_sha256:
            raise SelectiveRepairExecutionError(
                "successful repair evidence must reference a changed artifact"
            )
        if self.output_byte_length <= 0:
            raise SelectiveRepairExecutionError(
                "repair output_byte_length must be positive"
            )


class RepairAction(Protocol):
    """Injected bounded mutation implementation for one repair request."""

    @property
    def executor_id(self) -> str:
        """Return a stable repair implementation identifier."""

    def execute(
        self,
        request: RepairRequest,
        *,
        source_path: Path,
        output_path: Path,
    ) -> None:
        """Materialize exactly one repaired output artifact."""


class SelectiveRepairExecutionCoordinator:
    """Verify source identity, execute one bounded repair, and verify output."""

    def __init__(self, action: RepairAction) -> None:
        _require_text("executor_id", action.executor_id)
        self._action = action

    def execute(
        self,
        request: RepairRequest,
        *,
        source_path: str | Path,
        source_artifact_sha256: str,
        source_byte_length: int,
        output_directory: str | Path,
        provenance_reference: str,
    ) -> RepairExecutionEvidence:
        for name in ("repair_id", "finding_id", "target"):
            _require_text(name, getattr(request, name))
        if request.attempt <= 0:
            raise SelectiveRepairExecutionError("repair attempt must be positive")
        _require_sha256(source_artifact_sha256)
        _require_text("provenance_reference", provenance_reference)
        if source_byte_length <= 0:
            raise SelectiveRepairExecutionError(
                "source_byte_length must be positive"
            )

        source = Path(source_path)
        if source.is_symlink():
            raise SelectiveRepairExecutionError(
                "symbolic-link repair sources are prohibited"
            )
        if not source.exists() or not source.is_file():
            raise SelectiveRepairExecutionError(
                "repair source must be an existing regular file"
            )
        source_body = source.read_bytes()
        if not source_body:
            raise SelectiveRepairExecutionError("repair source must not be empty")
        if len(source_body) != source_byte_length:
            raise SelectiveRepairExecutionError("repair source byte length mismatch")
        if sha256(source_body).hexdigest() != source_artifact_sha256:
            raise SelectiveRepairExecutionError("repair source SHA-256 mismatch")

        output_root = Path(output_directory)
        if output_root.exists() and not output_root.is_dir():
            raise SelectiveRepairExecutionError(
                "output_directory must reference a directory"
            )
        output_root.mkdir(parents=True, exist_ok=True)
        identity = "|".join(
            (
                request.repair_id,
                request.finding_id,
                request.target,
                str(request.attempt),
                source_artifact_sha256,
                self._action.executor_id,
                provenance_reference,
            )
        )
        output = output_root / (
            f"repair-{sha256(identity.encode('utf-8')).hexdigest()[:20]}.mp4"
        )
        if output.resolve() == source.resolve():
            raise SelectiveRepairExecutionError(
                "repair output cannot overwrite its source artifact"
            )
        if output.exists() or output.is_symlink():
            raise SelectiveRepairExecutionError(
                "repair output identity already exists"
            )

        self._action.execute(request, source_path=source, output_path=output)

        if output.is_symlink():
            raise SelectiveRepairExecutionError(
                "symbolic-link repair outputs are prohibited"
            )
        if not output.exists() or not output.is_file():
            raise SelectiveRepairExecutionError(
                "repair action did not emit a regular output file"
            )
        output_body = output.read_bytes()
        if not output_body:
            raise SelectiveRepairExecutionError("repair output must not be empty")
        output_sha = sha256(output_body).hexdigest()
        if output_sha == source_artifact_sha256:
            raise SelectiveRepairExecutionError(
                "repair action did not change the source artifact"
            )

        return RepairExecutionEvidence(
            repair_id=request.repair_id,
            finding_id=request.finding_id,
            target=request.target,
            attempt=request.attempt,
            source_artifact_sha256=source_artifact_sha256,
            output_artifact_sha256=output_sha,
            output_path=str(output.resolve()),
            output_byte_length=len(output_body),
            executor_id=self._action.executor_id,
            provenance_reference=provenance_reference,
        )


def _require_sha256(value: str) -> None:
    if len(value) != 64 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise SelectiveRepairExecutionError(
            "artifact identity must be lowercase SHA-256"
        )


def _require_text(name: str, value: str) -> None:
    if not value or value != value.strip():
        raise SelectiveRepairExecutionError(
            f"{name} must be non-blank and trimmed"
        )
