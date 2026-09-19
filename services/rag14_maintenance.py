"""Canary-only backup/restore evidence runner for the RAG.14 production gate.

The module is executed only by an explicitly overridden one-off ECS task. It
never mutates the live state tree: the backup is read from the mounted EFS state
and every restore is performed into ephemeral container storage.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import zipfile
from pathlib import Path

from services.deployment.backup import BackupError, RuntimeBackupManager
from services.knowledge_runtime import (
    DurableKnowledgeRuntime,
    KnowledgeRuntimeConfig,
    KnowledgeRuntimePolicy,
)
from services.rag14_embedding_provider import PRODUCTION_EMBEDDING_MODE


class RAG14MaintenanceError(RuntimeError):
    """Canary maintenance evidence violated a fail-closed invariant."""


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RAG14MaintenanceError(f"required environment variable is missing: {name}")
    return value


def _set_env(name: str) -> frozenset[str]:
    values = frozenset(
        item.strip() for item in _required_env(name).split(",") if item.strip()
    )
    if not values:
        raise RAG14MaintenanceError(f"{name} must contain at least one value")
    return values


def _policy() -> KnowledgeRuntimePolicy:
    return KnowledgeRuntimePolicy(
        principal_id=_required_env("ILAIOS_KNOWLEDGE_PRINCIPAL_ID"),
        tenant_id=_required_env("ILAIOS_KNOWLEDGE_TENANT_ID"),
        project_id=_required_env("ILAIOS_KNOWLEDGE_PROJECT_ID"),
        allowed_classifications=_set_env("ILAIOS_KNOWLEDGE_CLASSIFICATIONS"),
        allowed_purposes=_set_env("ILAIOS_KNOWLEDGE_PURPOSES"),
        allowed_residencies=_set_env("ILAIOS_KNOWLEDGE_RESIDENCIES"),
    )


def _corrupt_archive(source: Path, target: Path) -> None:
    """Create a structurally valid ZIP whose manifest no longer matches one file."""
    with zipfile.ZipFile(source) as archive:
        names = [name for name in archive.namelist() if name != "manifest.json"]
        if not names:
            raise RAG14MaintenanceError("backup archive contains no state files")
        corrupt_name = names[0]
        entries = {name: archive.read(name) for name in archive.namelist()}
    original = entries[corrupt_name]
    entries[corrupt_name] = (
        b"X" if not original else bytes([original[0] ^ 1]) + original[1:]
    )
    with zipfile.ZipFile(target, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in entries.items():
            archive.writestr(name, content)


def run_backup_restore_drill(state_root: Path) -> dict[str, object]:
    """Take an online backup, restore it, and prove corrupt restore rejection."""
    if os.environ.get("ILAIOS_RELEASE_STATE") != "CANARY":
        raise RAG14MaintenanceError("RAG.14 maintenance drill is CANARY-only")
    if _required_env("ILAIOS_KNOWLEDGE_EMBEDDING_MODE") != PRODUCTION_EMBEDDING_MODE:
        raise RAG14MaintenanceError(
            "maintenance drill requires the pinned production provider"
        )
    if not state_root.is_absolute() or not state_root.is_dir():
        raise RAG14MaintenanceError("state root must be an existing absolute directory")

    manager = RuntimeBackupManager()
    with tempfile.TemporaryDirectory(prefix="ilaios-rag14-maintenance-") as temporary:
        root = Path(temporary)
        archive = root / "runtime-backup.zip"
        restored = root / "restored"
        started_files = tuple(
            sorted(
                path.relative_to(state_root).as_posix()
                for path in state_root.rglob("*")
                if path.is_file()
            )
        )
        if not started_files:
            raise RAG14MaintenanceError("live state root is empty")

        manifest = manager.backup(state_root, archive)
        restored_manifest = manager.restore(archive, restored)
        if manifest != restored_manifest:
            raise RAG14MaintenanceError(
                "restored backup manifest differs from source manifest"
            )

        policy = _policy()
        restored_runtime = DurableKnowledgeRuntime(
            KnowledgeRuntimeConfig(
                metadata_database=restored / "knowledge" / "knowledge.sqlite3",
                vector_database=restored / "knowledge" / "vectors.sqlite3",
                policy=policy,
            )
        )
        verification = restored_runtime.verify()
        state = restored_runtime.state()
        if verification.get("event_chain") != "verified":
            raise RAG14MaintenanceError(
                "restored Knowledge event chain failed verification"
            )
        if verification.get("vector_index_integrity") is not True:
            raise RAG14MaintenanceError(
                "restored vector index failed integrity verification"
            )
        if state.get("tenant_id") != policy.tenant_id or state.get("project_id") != policy.project_id:
            raise RAG14MaintenanceError("restored Knowledge scope binding drifted")
        provider_id = str(state.get("embedding_provider_id", ""))
        if not provider_id.startswith("ilaios.embedding.multilingual-e5-small.qint8.v1@"):
            raise RAG14MaintenanceError(
                "restored runtime is not using the pinned production provider"
            )

        vector_state = state.get("vector_index")
        vector_row_count = (
            vector_state.get("row_count") if isinstance(vector_state, dict) else None
        )
        if vector_row_count != 0:
            raise RAG14MaintenanceError(
                "deleted/revoked Knowledge vectors resurrected after backup restore"
            )

        corrupted = root / "runtime-backup-corrupted.zip"
        _corrupt_archive(archive, corrupted)
        corrupt_restore_rejected = False
        try:
            manager.restore(corrupted, root / "corrupt-restore")
        except (BackupError, zipfile.BadZipFile):
            corrupt_restore_rejected = True
        if not corrupt_restore_rejected:
            raise RAG14MaintenanceError("corrupted backup was accepted")

        archive_bytes = archive.read_bytes()
        files = manifest.get("files")
        file_count = len(files) if isinstance(files, dict) else 0
        report: dict[str, object] = {
            "event": "rag14_backup_restore",
            "status": "PASS",
            "release_state": "CANARY",
            "tenant_id": state.get("tenant_id"),
            "project_id": state.get("project_id"),
            "embedding_provider_id": provider_id,
            "archive_sha256": hashlib.sha256(archive_bytes).hexdigest(),
            "archive_size_bytes": len(archive_bytes),
            "manifest_file_count": file_count,
            "source_file_count": len(started_files),
            "restored_event_count": verification.get("event_count"),
            "restored_vector_index_evidence_sha256": verification.get(
                "vector_index_evidence_sha256"
            ),
            "restored_vector_row_count": vector_row_count,
            "corrupt_restore_rejected": True,
            "production_authority": False,
        }
        print(json.dumps(report, sort_keys=True), flush=True)
        return report


def main() -> int:
    mode = _required_env("ILAIOS_RAG14_MAINTENANCE_MODE")
    if mode != "backup_restore_test":
        raise RAG14MaintenanceError("unsupported RAG.14 maintenance mode")
    state_root = Path(_required_env("ILAIOS_STATE_ROOT"))
    run_backup_restore_drill(state_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
