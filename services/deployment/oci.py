"""Engine-independent OCI image-layout builder with immutable identities."""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import subprocess
import sys
import sysconfig
import tarfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class OciBuildResult:
    index_digest: str
    manifest_digest: str
    config_digest: str
    layer_digest: str
    layer_diff_id: str
    layout_path: str


def build_oci_layout(repository: Path, output: Path) -> OciBuildResult:
    if output.exists():
        raise ValueError("OCI output path already exists")
    output.mkdir(parents=True)
    blobs = output / "blobs" / "sha256"
    blobs.mkdir(parents=True)
    layer_tar = _runtime_layer(repository.resolve())
    layer_diff_id = _sha(layer_tar)
    compressed = gzip.compress(layer_tar, compresslevel=9, mtime=0)
    layer_digest = _write_blob(blobs, compressed)
    config = json.dumps(
        {
            "architecture": "amd64",
            "config": {
                "Entrypoint": ["/usr/bin/python3.12", "-m", "services.deployment.runtime"],
                "Env": ["PYTHONPATH=/opt/ilaios", "PYTHONUNBUFFERED=1"],
                "WorkingDir": "/opt/ilaios",
            },
            "created": "1970-01-01T00:00:00Z",
            "os": "linux",
            "rootfs": {"diff_ids": [f"sha256:{layer_diff_id}"], "type": "layers"},
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    config_digest = _write_blob(blobs, config)
    manifest = json.dumps(
        {
            "schemaVersion": 2,
            "config": _descriptor(config_digest, len(config), "application/vnd.oci.image.config.v1+json"),
            "layers": [
                _descriptor(
                    layer_digest,
                    len(compressed),
                    "application/vnd.oci.image.layer.v1.tar+gzip",
                )
            ],
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    manifest_digest = _write_blob(blobs, manifest)
    index = json.dumps(
        {
            "schemaVersion": 2,
            "manifests": [
                _descriptor(
                    manifest_digest,
                    len(manifest),
                    "application/vnd.oci.image.manifest.v1+json",
                )
                | {"annotations": {"org.opencontainers.image.ref.name": "ilaios:recovery"}}
            ],
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    (output / "index.json").write_bytes(index)
    (output / "oci-layout").write_text(
        '{"imageLayoutVersion":"1.0.0"}\n', encoding="utf-8"
    )
    return OciBuildResult(
        _sha(index),
        manifest_digest,
        config_digest,
        layer_digest,
        layer_diff_id,
        str(output),
    )


def _runtime_layer(repository: Path) -> bytes:
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as archive:
        executable = Path(sys.executable).resolve()
        _add_file(archive, executable, Path("usr/bin/python3.12"))
        stdlib = Path(sysconfig.get_path("stdlib"))
        stdlib_files = tuple(
            sorted(item for item in stdlib.rglob("*") if item.is_file())
        )
        for source in stdlib_files:
            _add_file(archive, source, Path(str(source).lstrip("/")))
        linked_inputs = (executable,) + tuple(
            source for source in stdlib_files if source.suffix == ".so"
        )
        linked_libraries = _linked_libraries(linked_inputs)
        scanner_files: set[Path] = set()
        for target, source in linked_libraries.items():
            _add_file(archive, source, target)
            scanner_files.add(source)
            host_target = Path("/") / target
            if host_target.exists():
                scanner_files.add(host_target)
        _add_scanner_metadata(archive, tuple(sorted(scanner_files)))
        for root_name in ("apps", "packages", "services", "src"):
            root = repository / root_name
            for source in sorted(root.rglob("*.py")):
                _add_file(
                    archive,
                    source,
                    Path("opt/ilaios") / source.relative_to(repository),
                )
    return stream.getvalue()


def _add_scanner_metadata(
    archive: tarfile.TarFile, runtime_system_files: tuple[Path, ...]
) -> None:
    """Add distro metadata for packages that are actually present in the image."""
    os_release = Path("/etc/os-release")
    if os_release.is_file():
        _add_file(archive, os_release, Path("etc/os-release"))

    package_names = _owning_debian_packages(runtime_system_files)
    package_status = _filtered_dpkg_status(package_names)
    if package_status:
        _add_bytes(
            archive,
            package_status.encode("utf-8"),
            Path("var/lib/dpkg/status"),
            mode=0o644,
        )


def _owning_debian_packages(files: tuple[Path, ...]) -> tuple[str, ...]:
    packages: set[str] = set()
    if not Path("/usr/bin/dpkg-query").is_file():
        return ()
    for source in files:
        completed = subprocess.run(
            ("dpkg-query", "--search", str(source)),
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            continue
        for line in completed.stdout.splitlines():
            owner_field, separator, _ = line.partition(": ")
            if not separator:
                continue
            for owner in owner_field.split(", "):
                package = owner.split(":", 1)[0].strip()
                if package:
                    packages.add(package)
    return tuple(sorted(packages))


def _filtered_dpkg_status(packages: tuple[str, ...]) -> str:
    status_path = Path("/var/lib/dpkg/status")
    if not packages or not status_path.is_file():
        return ""
    wanted = set(packages)
    selected: list[str] = []
    for stanza in status_path.read_text(encoding="utf-8", errors="strict").split("\n\n"):
        package_name = ""
        installed = False
        for line in stanza.splitlines():
            if line.startswith("Package: "):
                package_name = line.removeprefix("Package: ").strip()
            elif line == "Status: install ok installed":
                installed = True
        if package_name in wanted and installed:
            selected.append(stanza.rstrip())
    if not selected:
        return ""
    return "\n\n".join(sorted(selected)) + "\n"


def _linked_libraries(inputs: tuple[Path, ...]) -> dict[Path, Path]:
    libraries: dict[Path, Path] = {}
    for executable in inputs:
        completed = subprocess.run(
            ("ldd", str(executable)), check=False, capture_output=True, text=True
        )
        if completed.returncode not in {0, 1}:
            continue
        for line in completed.stdout.splitlines():
            tokens = line.strip().split()
            candidates = [token for token in tokens if token.startswith("/")]
            if candidates:
                raw = Path(candidates[0])
                libraries[Path(str(raw).lstrip("/"))] = raw.resolve()
    return dict(sorted(libraries.items()))


def _add_file(archive: tarfile.TarFile, source: Path, target: Path) -> None:
    _add_bytes(
        archive,
        source.read_bytes(),
        target,
        mode=source.stat().st_mode & 0o777,
    )


def _add_bytes(
    archive: tarfile.TarFile, content: bytes, target: Path, *, mode: int
) -> None:
    info = tarfile.TarInfo(target.as_posix())
    info.size = len(content)
    info.mode = mode
    info.uid = info.gid = 0
    info.mtime = 0
    archive.addfile(info, io.BytesIO(content))


def _descriptor(digest: str, size: int, media_type: str) -> dict[str, object]:
    return {"digest": f"sha256:{digest}", "mediaType": media_type, "size": size}


def _write_blob(root: Path, content: bytes) -> str:
    digest = _sha(content)
    (root / digest).write_bytes(content)
    return digest


def _sha(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
