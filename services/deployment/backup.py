"""Verified provider-neutral runtime backup and restore."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import cast


class BackupError(RuntimeError):
    """Raised when backup integrity or restore isolation fails."""


class RuntimeBackupManager:
    def backup(self, state_root: Path, archive: Path) -> dict[str, object]:
        state_root = state_root.resolve()
        if not state_root.is_dir() or archive.exists():
            raise BackupError("valid state root and new archive path are required")
        files: dict[str, bytes] = {}
        with tempfile.TemporaryDirectory(prefix="ilaios-backup-") as temporary:
            temporary_root = Path(temporary)
            for source in sorted(item for item in state_root.rglob("*") if item.is_file()):
                relative = source.relative_to(state_root).as_posix()
                if source.suffix == ".sqlite3":
                    snapshot = temporary_root / relative
                    snapshot.parent.mkdir(parents=True, exist_ok=True)
                    with sqlite3.connect(source) as current, sqlite3.connect(snapshot) as target:
                        current.backup(target)
                    files[relative] = snapshot.read_bytes()
                else:
                    files[relative] = source.read_bytes()
        manifest: dict[str, object] = {
            "format": "ILAIOS_RUNTIME_BACKUP_V1",
            "files": {
                path: {"sha256": hashlib.sha256(content).hexdigest(), "size": len(content)}
                for path, content in sorted(files.items())
            },
        }
        archive.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as bundle:
            for relative, content in sorted(files.items()):
                _write_deterministic(bundle, relative, content)
            _write_deterministic(
                bundle,
                "manifest.json",
                json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode(),
            )
        return manifest

    def restore(self, archive: Path, target_root: Path) -> dict[str, object]:
        if not archive.is_file() or (target_root.exists() and any(target_root.iterdir())):
            raise BackupError("archive must exist and restore target must be empty")
        with zipfile.ZipFile(archive) as bundle:
            names = set(bundle.namelist())
            if "manifest.json" not in names:
                raise BackupError("backup manifest is missing")
            raw_manifest: object = json.loads(bundle.read("manifest.json"))
            if not isinstance(raw_manifest, dict):
                raise BackupError("backup manifest is invalid")
            manifest = cast(dict[str, object], raw_manifest)
            if manifest.get("format") != "ILAIOS_RUNTIME_BACKUP_V1":
                raise BackupError("backup format is invalid")
            raw_expected = manifest.get("files")
            if not isinstance(raw_expected, dict) or not all(
                isinstance(path, str) for path in raw_expected
            ):
                raise BackupError("backup file set is invalid")
            expected = cast(dict[str, object], raw_expected)
            if names != set(expected) | {"manifest.json"}:
                raise BackupError("backup file set is invalid")
            restored: dict[str, bytes] = {}
            for relative, metadata in expected.items():
                path = PurePosixPath(relative)
                if path.is_absolute() or ".." in path.parts:
                    raise BackupError("backup path escapes restore root")
                content = bundle.read(relative)
                if (
                    not isinstance(metadata, dict)
                    or hashlib.sha256(content).hexdigest() != metadata.get("sha256")
                    or len(content) != metadata.get("size")
                ):
                    raise BackupError("backup content integrity failed")
                restored[relative] = content
        target_root.mkdir(parents=True, exist_ok=True)
        for relative, content in restored.items():
            destination = target_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
        return manifest


def _write_deterministic(bundle: zipfile.ZipFile, path: str, content: bytes) -> None:
    info = zipfile.ZipInfo(path, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100600 << 16
    bundle.writestr(info, content)
