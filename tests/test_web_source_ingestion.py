from __future__ import annotations

import io
import json
import stat
import zipfile
from pathlib import Path

import pytest

from services.web_source_ingestion import (
    WebSourceArchiveIngestor,
    WebSourceIngestionError,
)


def _archive(files: dict[str, bytes], *, wrapper: str | None = None) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for relative, body in files.items():
            name = f"{wrapper}/{relative}" if wrapper else relative
            bundle.writestr(name, body)
    return buffer.getvalue()


def _next_files() -> dict[str, bytes]:
    return {
        "package.json": json.dumps(
            {
                "name": "existing-site",
                "private": True,
                "dependencies": {
                    "next": "16.2.11",
                    "react": "19.2.0",
                    "react-dom": "19.2.0",
                },
                "scripts": {"build": "next build"},
            },
            sort_keys=True,
        ).encode(),
        "app/page.tsx": b"export default function Page(){return <main>Home</main>}",
        "app/dashboard/page.tsx": b"export default function Page(){return <main>Dashboard</main>}",
        "app/(marketing)/about/page.tsx": b"export default function Page(){return <main>About</main>}",
        "app/api/health/route.ts": b"export function GET(){return new Response('ok')}",
        "public/logo.svg": b"<svg xmlns='http://www.w3.org/2000/svg'></svg>",
    }


def test_ingestion_materializes_content_addressed_next_snapshot_without_execution(
    tmp_path: Path,
) -> None:
    archive = _archive(_next_files(), wrapper="customer-site")
    ingestor = WebSourceArchiveIngestor(tmp_path / "artifacts")

    snapshot = ingestor.ingest_zip(archive)

    assert snapshot.schema_version == "ilaios.web.source-snapshot.v1"
    assert snapshot.snapshot_id.startswith("ilaios-web-source-")
    assert snapshot.framework == "nextjs-react"
    assert snapshot.router == "app-router"
    assert snapshot.routes == ("/", "/about", "/dashboard")
    assert snapshot.executable_code_ran is False
    assert len(snapshot.archive_sha256) == 64
    assert len(snapshot.tree_sha256) == 64
    root = Path(snapshot.root_path)
    assert root.is_dir()
    assert (root / "package.json").is_file()
    assert (root / "app/dashboard/page.tsx").is_file()
    assert not (root / "node_modules").exists()

    repeated = ingestor.ingest_zip(archive)
    assert repeated.to_dict() == snapshot.to_dict()


def test_ingestion_detects_pages_router_routes(tmp_path: Path) -> None:
    files = _next_files()
    files.pop("app/page.tsx")
    files.pop("app/dashboard/page.tsx")
    files.pop("app/(marketing)/about/page.tsx")
    files["pages/index.tsx"] = b"export default function Page(){return <main>Home</main>}"
    files["pages/projects/[id].tsx"] = b"export default function Page(){return null}"
    files["pages/api/ping.ts"] = b"export default function handler(){}"
    files["pages/_app.tsx"] = b"export default function App(){return null}"

    snapshot = WebSourceArchiveIngestor(tmp_path / "artifacts").ingest_zip(
        _archive(files)
    )

    assert snapshot.router == "pages-router"
    assert snapshot.routes == ("/", "/projects/[id]")


def test_ingestion_rejects_zip_slip_path_traversal(tmp_path: Path) -> None:
    files = _next_files()
    files["../escape.txt"] = b"escape"

    with pytest.raises(WebSourceIngestionError, match="path traversal"):
        WebSourceArchiveIngestor(tmp_path / "artifacts").ingest_zip(_archive(files))


def test_ingestion_rejects_symlink_entries(tmp_path: Path) -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as bundle:
        for relative, body in _next_files().items():
            bundle.writestr(relative, body)
        link = zipfile.ZipInfo("app/leak.ts")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        bundle.writestr(link, "../../secret")

    with pytest.raises(WebSourceIngestionError, match="symlinks are forbidden"):
        WebSourceArchiveIngestor(tmp_path / "artifacts").ingest_zip(buffer.getvalue())


def test_ingestion_rejects_secret_bearing_paths(tmp_path: Path) -> None:
    for secret_path in (
        ".env",
        ".env.production",
        ".npmrc",
        "config/private.key",
        "certs/site.p12",
    ):
        files = _next_files()
        files[secret_path] = b"do-not-import"

        with pytest.raises(
            WebSourceIngestionError,
            match="secret-bearing path|private-key/certificate path",
        ):
            WebSourceArchiveIngestor(tmp_path / "artifacts").ingest_zip(_archive(files))


def test_ingestion_rejects_generated_dependency_trees(tmp_path: Path) -> None:
    files = _next_files()
    files["node_modules/pkg/index.js"] = b"module.exports = {}"

    with pytest.raises(WebSourceIngestionError, match="forbidden generated/private path"):
        WebSourceArchiveIngestor(tmp_path / "artifacts").ingest_zip(_archive(files))


def test_ingestion_rejects_non_next_source(tmp_path: Path) -> None:
    files = _next_files()
    files["package.json"] = json.dumps(
        {"dependencies": {"react": "19.2.0"}}
    ).encode()

    with pytest.raises(WebSourceIngestionError, match="initial verified Next.js/React"):
        WebSourceArchiveIngestor(tmp_path / "artifacts").ingest_zip(_archive(files))


def test_ingestion_rejects_malformed_package_json(tmp_path: Path) -> None:
    files = _next_files()
    files["package.json"] = b"{not-json"

    with pytest.raises(WebSourceIngestionError, match="valid UTF-8 JSON"):
        WebSourceArchiveIngestor(tmp_path / "artifacts").ingest_zip(_archive(files))


def test_ingestion_rejects_extreme_compression_ratio(tmp_path: Path) -> None:
    files = _next_files()
    files["public/repeated.txt"] = b"A" * 1_000_000

    with pytest.raises(WebSourceIngestionError, match="compression-ratio"):
        WebSourceArchiveIngestor(tmp_path / "artifacts").ingest_zip(_archive(files))


def test_existing_snapshot_tamper_fails_closed(tmp_path: Path) -> None:
    archive = _archive(_next_files())
    ingestor = WebSourceArchiveIngestor(tmp_path / "artifacts")
    first = ingestor.ingest_zip(archive)
    (Path(first.root_path) / "app/page.tsx").write_text("tampered", encoding="utf-8")

    with pytest.raises(WebSourceIngestionError, match="integrity mismatch"):
        ingestor.ingest_zip(archive)
