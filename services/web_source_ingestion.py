"""Fail-closed ingestion of existing Web source into immutable ILAIOS snapshots.

This boundary accepts an uploaded ZIP source bundle, validates it without executing
any imported code, and materializes a content-addressed copy under the configured
artifact root. Imported source is untrusted input: ingestion grants no build,
mutation, deployment, provider, routing, policy, approval, or acceptance authority.
"""

from __future__ import annotations

import hashlib
import io
import json
import shutil
import stat
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import cast

MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 5_000
MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_TOTAL_UNCOMPRESSED_BYTES = 200 * 1024 * 1024
MAX_COMPRESSION_RATIO = 120
MAX_PATH_CHARS = 240

_FORBIDDEN_SEGMENTS = frozenset({".git", ".next", "node_modules", "__pycache__"})
_FORBIDDEN_BASENAMES = frozenset(
    {
        ".npmrc",
        ".netrc",
        "id_rsa",
        "id_ed25519",
        "credentials",
        "credentials.json",
        "secrets.json",
    }
)
_FORBIDDEN_SUFFIXES = frozenset({".pem", ".key", ".p12", ".pfx"})
_SOURCE_SUFFIXES = frozenset({".js", ".jsx", ".ts", ".tsx"})


class WebSourceIngestionError(RuntimeError):
    """An existing Web source bundle failed the governed import boundary."""


@dataclass(frozen=True, slots=True)
class WebSourceFile:
    relative_path: str
    sha256: str
    size_bytes: int

    def to_dict(self) -> dict[str, object]:
        return {
            "relative_path": self.relative_path,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
        }


@dataclass(frozen=True, slots=True)
class WebSourceSnapshot:
    schema_version: str
    snapshot_id: str
    root_path: str
    archive_sha256: str
    tree_sha256: str
    framework: str
    router: str
    routes: tuple[str, ...]
    files: tuple[WebSourceFile, ...]
    executable_code_ran: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "snapshot_id": self.snapshot_id,
            "root_path": self.root_path,
            "archive_sha256": self.archive_sha256,
            "tree_sha256": self.tree_sha256,
            "framework": self.framework,
            "router": self.router,
            "routes": list(self.routes),
            "files": [item.to_dict() for item in self.files],
            "executable_code_ran": self.executable_code_ran,
        }


class WebSourceArchiveIngestor:
    """Validate and snapshot one bounded Next.js source archive without execution."""

    schema_version = "ilaios.web.source-snapshot.v1"

    def __init__(self, artifact_root: Path) -> None:
        self._artifact_root = artifact_root.resolve()
        if artifact_root.is_symlink():
            raise WebSourceIngestionError("Web source artifact root must not be a symlink")
        self._snapshot_root = self._artifact_root / "imported-source-snapshots"
        self._snapshot_root.mkdir(parents=True, exist_ok=True)
        if self._snapshot_root.is_symlink():
            raise WebSourceIngestionError("Web source snapshot root must not be a symlink")

    def ingest_zip(self, archive: bytes) -> WebSourceSnapshot:
        if not archive:
            raise WebSourceIngestionError("Web source archive must not be empty")
        if len(archive) > MAX_ARCHIVE_BYTES:
            raise WebSourceIngestionError("Web source archive exceeds the upload limit")
        archive_sha256 = hashlib.sha256(archive).hexdigest()
        try:
            bundle = zipfile.ZipFile(io.BytesIO(archive), "r")
        except (zipfile.BadZipFile, OSError) as error:
            raise WebSourceIngestionError("Web source archive is not a valid ZIP") from error

        with bundle:
            infos = bundle.infolist()
            if not infos:
                raise WebSourceIngestionError("Web source archive contains no files")
            if len(infos) > MAX_ARCHIVE_ENTRIES:
                raise WebSourceIngestionError("Web source archive contains too many entries")

            prefix = _common_wrapper_prefix(infos)
            files: dict[str, bytes] = {}
            total_uncompressed = 0
            for info in infos:
                if info.flag_bits & 0x1:
                    raise WebSourceIngestionError("encrypted Web source archives are not supported")
                relative = _safe_relative_path(info.filename, prefix=prefix)
                if relative is None:
                    continue
                _validate_zip_entry_type(info)
                if info.is_dir():
                    continue
                _validate_source_path(relative)
                if info.file_size <= 0:
                    raise WebSourceIngestionError(
                        f"Web source file is empty: {relative.as_posix()}"
                    )
                if info.file_size > MAX_FILE_BYTES:
                    raise WebSourceIngestionError(
                        f"Web source file exceeds the per-file limit: {relative.as_posix()}"
                    )
                total_uncompressed += info.file_size
                if total_uncompressed > MAX_TOTAL_UNCOMPRESSED_BYTES:
                    raise WebSourceIngestionError(
                        "Web source archive exceeds the uncompressed size limit"
                    )
                if info.compress_size == 0:
                    if info.file_size > 0:
                        raise WebSourceIngestionError(
                            "Web source archive contains an unsafe compression entry"
                        )
                elif info.file_size > info.compress_size * MAX_COMPRESSION_RATIO:
                    raise WebSourceIngestionError(
                        "Web source archive exceeds the compression-ratio safety limit"
                    )
                try:
                    body = bundle.read(info)
                except (RuntimeError, zipfile.BadZipFile, OSError) as error:
                    raise WebSourceIngestionError(
                        f"Web source file could not be read safely: {relative.as_posix()}"
                    ) from error
                if len(body) != info.file_size:
                    raise WebSourceIngestionError(
                        f"Web source file size changed during extraction: {relative.as_posix()}"
                    )
                key = relative.as_posix()
                if key in files:
                    raise WebSourceIngestionError("Web source archive contains duplicate paths")
                files[key] = body

        if not files:
            raise WebSourceIngestionError("Web source archive contains no importable files")
        package = _package_document(files)
        framework = _detect_framework(package)
        router, routes = _detect_routes(files)
        if not routes:
            raise WebSourceIngestionError("Next.js source contains no bounded application routes")

        tree_sha256, inventory = _tree_digest(files)
        snapshot_id = f"ilaios-web-source-{tree_sha256[:20]}"
        destination = (self._snapshot_root / snapshot_id).resolve()
        if self._snapshot_root != destination.parent:
            raise WebSourceIngestionError("Web source snapshot escaped its artifact root")
        if destination.exists():
            _verify_existing_snapshot(destination, tree_sha256)
        else:
            _materialize_snapshot(destination, files)
            observed, _ = _disk_tree_digest(destination)
            if observed != tree_sha256:
                shutil.rmtree(destination, ignore_errors=True)
                raise WebSourceIngestionError("materialized Web source snapshot failed integrity verification")

        return WebSourceSnapshot(
            schema_version=self.schema_version,
            snapshot_id=snapshot_id,
            root_path=str(destination),
            archive_sha256=archive_sha256,
            tree_sha256=tree_sha256,
            framework=framework,
            router=router,
            routes=routes,
            files=inventory,
        )


def _common_wrapper_prefix(infos: list[zipfile.ZipInfo]) -> str | None:
    first_segments: set[str] = set()
    saw_root_file = False
    for info in infos:
        raw = info.filename.replace("\\", "/")
        parts = tuple(part for part in PurePosixPath(raw).parts if part not in {"", "."})
        if not parts:
            continue
        if len(parts) == 1 and not info.is_dir():
            saw_root_file = True
        first_segments.add(parts[0])
    if not saw_root_file and len(first_segments) == 1:
        candidate = next(iter(first_segments))
        if candidate not in {"..", "/"}:
            return candidate
    return None


def _safe_relative_path(filename: str, *, prefix: str | None) -> PurePosixPath | None:
    if not filename or "\x00" in filename:
        raise WebSourceIngestionError("Web source archive contains an invalid path")
    raw = filename.replace("\\", "/")
    if raw.startswith("/") or (len(raw) >= 2 and raw[1] == ":"):
        raise WebSourceIngestionError("Web source archive contains an absolute path")
    path = PurePosixPath(raw)
    parts = tuple(part for part in path.parts if part not in {"", "."})
    if any(part == ".." for part in parts):
        raise WebSourceIngestionError("Web source archive contains path traversal")
    if prefix is not None:
        if not parts or parts[0] != prefix:
            raise WebSourceIngestionError("Web source archive wrapper directory is inconsistent")
        parts = parts[1:]
    if not parts:
        return None
    relative = PurePosixPath(*parts)
    if len(relative.as_posix()) > MAX_PATH_CHARS:
        raise WebSourceIngestionError("Web source path exceeds the bounded length")
    return relative


def _validate_zip_entry_type(info: zipfile.ZipInfo) -> None:
    mode = (info.external_attr >> 16) & 0xFFFF
    if mode == 0:
        return
    kind = stat.S_IFMT(mode)
    if kind == stat.S_IFLNK:
        raise WebSourceIngestionError("Web source archive symlinks are forbidden")
    if info.is_dir():
        if kind not in {0, stat.S_IFDIR}:
            raise WebSourceIngestionError("Web source archive directory entry is unsafe")
        return
    if kind not in {0, stat.S_IFREG}:
        raise WebSourceIngestionError("Web source archive contains a non-regular file")


def _validate_source_path(path: PurePosixPath) -> None:
    lowered = tuple(part.casefold() for part in path.parts)
    if any(part in _FORBIDDEN_SEGMENTS for part in lowered):
        raise WebSourceIngestionError(
            f"Web source archive contains a forbidden generated/private path: {path.as_posix()}"
        )
    name = lowered[-1]
    if name.startswith(".env") or name in _FORBIDDEN_BASENAMES:
        raise WebSourceIngestionError(
            f"Web source archive contains a secret-bearing path: {path.as_posix()}"
        )
    if any(name.endswith(suffix) for suffix in _FORBIDDEN_SUFFIXES):
        raise WebSourceIngestionError(
            f"Web source archive contains a private-key/certificate path: {path.as_posix()}"
        )


def _package_document(files: dict[str, bytes]) -> dict[str, object]:
    body = files.get("package.json")
    if body is None:
        raise WebSourceIngestionError("existing Web source must include package.json")
    if len(body) > 1_000_000:
        raise WebSourceIngestionError("package.json exceeds the bounded metadata size")
    try:
        decoded = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise WebSourceIngestionError("package.json is not valid UTF-8 JSON") from error
    if not isinstance(decoded, dict):
        raise WebSourceIngestionError("package.json must be a JSON object")
    return cast(dict[str, object], decoded)


def _detect_framework(package: dict[str, object]) -> str:
    dependency_names: set[str] = set()
    for field in ("dependencies", "devDependencies", "peerDependencies"):
        value = package.get(field)
        if value is None:
            continue
        if not isinstance(value, dict):
            raise WebSourceIngestionError(f"package.json {field} must be an object")
        dependency_names.update(str(key) for key in value)
    if "next" not in dependency_names or "react" not in dependency_names:
        raise WebSourceIngestionError(
            "existing Web source is outside the initial verified Next.js/React ingestion scope"
        )
    return "nextjs-react"


def _detect_routes(files: dict[str, bytes]) -> tuple[str, tuple[str, ...]]:
    app_routes: set[str] = set()
    page_routes: set[str] = set()
    for relative in files:
        path = PurePosixPath(relative)
        if path.suffix.casefold() not in _SOURCE_SUFFIXES:
            continue
        parts = path.parts
        if len(parts) >= 2 and parts[0] == "app" and path.stem == "page":
            route = _app_route(parts[1:-1])
            if route is not None:
                app_routes.add(route)
        if len(parts) >= 2 and parts[0] == "pages":
            route = _pages_route(parts[1:])
            if route is not None:
                page_routes.add(route)
    if app_routes and page_routes:
        router = "hybrid"
    elif app_routes:
        router = "app-router"
    elif page_routes:
        router = "pages-router"
    else:
        router = "unknown"
    return router, tuple(sorted(app_routes | page_routes))


def _app_route(segments: tuple[str, ...]) -> str | None:
    visible: list[str] = []
    for segment in segments:
        if segment.startswith("@"):
            continue
        if segment.startswith("(") and segment.endswith(")"):
            continue
        if segment.startswith("(.)") or segment.startswith("(..)"):
            return None
        visible.append(segment)
    return "/" + "/".join(visible) if visible else "/"


def _pages_route(parts: tuple[str, ...]) -> str | None:
    if not parts:
        return None
    first = parts[0]
    if first == "api":
        return None
    stemmed = list(parts)
    filename = PurePosixPath(stemmed[-1])
    stem = filename.stem
    if stem in {"_app", "_document", "_error", "404", "500"}:
        return None
    stemmed[-1] = stem
    if stemmed[-1] == "index":
        stemmed = stemmed[:-1]
    return "/" + "/".join(stemmed) if stemmed else "/"


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


def _materialize_snapshot(destination: Path, files: dict[str, bytes]) -> None:
    destination.mkdir(parents=True, exist_ok=False)
    try:
        for relative, body in sorted(files.items()):
            target = (destination / relative).resolve()
            if destination != target and destination not in target.parents:
                raise WebSourceIngestionError("Web source file escaped the snapshot root")
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() or target.is_symlink():
                raise WebSourceIngestionError("Web source snapshot path already exists")
            target.write_bytes(body)
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise


def _disk_tree_digest(root: Path) -> tuple[str, tuple[WebSourceFile, ...]]:
    files: dict[str, bytes] = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise WebSourceIngestionError("Web source snapshot contains a symlink")
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        files[relative] = path.read_bytes()
    return _tree_digest(files)


def _verify_existing_snapshot(destination: Path, expected_digest: str) -> None:
    if destination.is_symlink() or not destination.is_dir():
        raise WebSourceIngestionError("existing Web source snapshot path is unsafe")
    observed, _ = _disk_tree_digest(destination)
    if observed != expected_digest:
        raise WebSourceIngestionError("existing Web source snapshot integrity mismatch")
