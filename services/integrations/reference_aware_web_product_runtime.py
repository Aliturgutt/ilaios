"""Reference-aware extension of the canonical recoverable Web Factory runtime.

This module keeps the existing ``web.product-runtime.v1`` authority and assurance
chain. It only binds already-admitted, tenant-scoped reference images into the
existing WebsiteSpec/design strategy and the generated Next.js source before the
canonical source-assurance gate runs.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import cast

from services.control_plane import ControlPlane
from services.governance import GovernedRuntimeGateway
from services.reference_asset_admission import ReferenceAssetAdmissionStore
from services.reference_assets import ReferenceAssetRecord
from services.runtime import DurableGrantPolicy

from .web_factory import WebsiteSpec
from .web_product_runtime import WebProductRuntimeError
from .web_product_runtime_recovery import RecoverableWebProductRuntime as _BaseRecoverableWebProductRuntime

_REFERENCE_USAGE = "asset-led-design-and-rendered-source"
_REFERENCE_SCHEMA = "ilaios.web.reference-assets.v1"
_PAGE_SHELL_PATH = "components/PageShell.tsx"
_GLOBAL_CSS_PATH = "app/globals.css"
_SITE_JSON_PATH = "site.json"
_REFERENCE_MARKER = "ilaios-reference-assets-v1"


class ReferenceAwareRecoverableWebProductRuntime(_BaseRecoverableWebProductRuntime):
    """Canonical Web runtime with governed user-reference consumption."""

    def __init__(
        self,
        database_path: Path,
        control_plane: ControlPlane,
        grants: DurableGrantPolicy,
        governance: GovernedRuntimeGateway,
        artifact_root: Path,
    ) -> None:
        super().__init__(database_path, control_plane, grants, governance, artifact_root)
        data_root = artifact_root.parent
        self._reference_assets = ReferenceAssetAdmissionStore(
            data_root / "reference-assets.sqlite3",
            data_root / "reference-assets" / "blobs",
        )

    def execute(
        self,
        request_id: str,
        grant_id: str,
        *,
        token: str,
        now: datetime,
    ) -> dict[str, object]:
        references = self._reference_assets.for_request(request_id)
        if references:
            self._promote_reference_design_context(request_id, references)
        return super().execute(request_id, grant_id, token=token, now=now)

    def recover_finalizing(
        self,
        request_id: str,
        *,
        token: str,
        now: datetime,
    ) -> dict[str, object]:
        references = self._reference_assets.for_request(request_id)
        if references:
            self._bind_references_before_assurance(request_id, references)
        return super().recover_finalizing(request_id, token=token, now=now)

    def _assert_accepted_assurance(
        self,
        request_id: str,
        manifest: dict[str, object],
    ) -> None:
        super()._assert_accepted_assurance(request_id, manifest)
        references = self._reference_assets.for_request(request_id)
        if not references:
            return
        expected = [_public_metadata(record) for record in references]
        if manifest.get("reference_assets") != expected:
            raise WebProductRuntimeError(
                "accepted Web evidence does not bind the supplied reference images"
            )
        if manifest.get("reference_asset_usage") != _REFERENCE_USAGE:
            raise WebProductRuntimeError(
                "accepted Web evidence does not prove rendered reference usage"
            )
        design = manifest.get("design_strategy")
        if not isinstance(design, dict) or design.get("imagery_behavior") != "asset-led":
            raise WebProductRuntimeError(
                "accepted Web design strategy is not reference-asset-led"
            )
        source_files = manifest.get("source_project_files")
        if not isinstance(source_files, list):
            raise WebProductRuntimeError("accepted Web source evidence is malformed")
        source_paths = {
            str(item.get("path"))
            for item in source_files
            if isinstance(item, dict) and isinstance(item.get("path"), str)
        }
        expected_paths = {
            str(item["source_path"])
            for item in cast(list[dict[str, object]], manifest.get("reference_asset_source_files", []))
        }
        if not expected_paths or not expected_paths.issubset(source_paths):
            raise WebProductRuntimeError(
                "accepted Web source evidence is missing rendered reference assets"
            )
        if _PAGE_SHELL_PATH not in source_paths:
            raise WebProductRuntimeError(
                "accepted Web source evidence is missing the reference render component"
            )

    def _promote_reference_design_context(
        self,
        request_id: str,
        references: tuple[ReferenceAssetRecord, ...],
    ) -> None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT status, principal_id, tenant_id, spec_json "
                "FROM web_product_requests WHERE request_id=?",
                (request_id,),
            ).fetchone()
            if row is None:
                raise WebProductRuntimeError("unknown reference-aware Web request")
            if row["status"] != "pending":
                return
            _assert_reference_ownership(
                references,
                principal_id=str(row["principal_id"]),
                tenant_id=str(row["tenant_id"]),
            )
            value = json.loads(str(row["spec_json"]))
            if not isinstance(value, dict):
                raise WebProductRuntimeError("stored WebsiteSpec is malformed")
            spec = WebsiteSpec.from_dict(cast(dict[str, object], value))
            if spec.visual_asset_availability == "rich":
                return
            enriched = replace(spec, visual_asset_availability="rich")
            changed = connection.execute(
                "UPDATE web_product_requests SET spec_json=? "
                "WHERE request_id=? AND status='pending'",
                (
                    json.dumps(
                        enriched.to_dict(), sort_keys=True, separators=(",", ":")
                    ),
                    request_id,
                ),
            ).rowcount
        if changed != 1:
            raise WebProductRuntimeError(
                "Web reference design context changed concurrently"
            )

    def _bind_references_before_assurance(
        self,
        request_id: str,
        references: tuple[ReferenceAssetRecord, ...],
    ) -> None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT status, principal_id, tenant_id, manifest_json "
                "FROM web_product_requests WHERE request_id=?",
                (request_id,),
            ).fetchone()
        if row is None:
            raise WebProductRuntimeError("unknown reference-aware Web request")
        if row["status"] == "accepted":
            return
        if row["status"] != "finalizing" or row["manifest_json"] is None:
            return
        _assert_reference_ownership(
            references,
            principal_id=str(row["principal_id"]),
            tenant_id=str(row["tenant_id"]),
        )
        value = json.loads(str(row["manifest_json"]))
        if not isinstance(value, dict):
            raise WebProductRuntimeError("stored finalizing Web manifest is malformed")
        manifest = cast(dict[str, object], value)
        expected_metadata = [_public_metadata(record) for record in references]
        if (
            manifest.get("reference_assets") == expected_metadata
            and manifest.get("reference_asset_usage") == _REFERENCE_USAGE
        ):
            return

        design = manifest.get("design_strategy")
        if not isinstance(design, dict) or design.get("imagery_behavior") != "asset-led":
            raise WebProductRuntimeError(
                "Web design strategy did not consume supplied reference images"
            )
        source_value = manifest.get("source_project_path")
        if not isinstance(source_value, str) or not source_value:
            raise WebProductRuntimeError("Web source path is missing before reference binding")
        source_root = Path(source_value).resolve()
        allowed_root = (self._artifact_root / "source-projects").resolve()
        if source_root == allowed_root or allowed_root not in source_root.parents:
            raise WebProductRuntimeError(
                "Web source path escaped the governed source-project root"
            )
        if not source_root.is_dir() or source_root.is_symlink():
            raise WebProductRuntimeError(
                "Web source path is unavailable or unsafe before reference binding"
            )

        project_files = _read_project_files(source_root)
        emitted: list[dict[str, object]] = []
        render_assets: list[dict[str, str]] = []
        for index, record in enumerate(references, start=1):
            extension = _extension(record.mime_type)
            relative_path = (
                f"public/reference-assets/reference-{index:02d}-"
                f"{record.sha256[:12]}{extension}"
            )
            body = self._reference_assets.read_bytes(record)
            project_files[relative_path] = body
            metadata = {
                **_public_metadata(record),
                "source_path": relative_path,
            }
            emitted.append(metadata)
            render_assets.append(
                {
                    "src": "/" + relative_path.removeprefix("public/"),
                    "alt": _reference_alt(record, index),
                    "role": record.role.value,
                    "instruction": record.instruction or "",
                    "sha256": record.sha256,
                }
            )

        project_files[_PAGE_SHELL_PATH] = _patch_page_shell(
            project_files.get(_PAGE_SHELL_PATH), render_assets
        )
        project_files[_GLOBAL_CSS_PATH] = _patch_css(
            project_files.get(_GLOBAL_CSS_PATH)
        )
        project_files[_SITE_JSON_PATH] = _patch_site_json(
            project_files.get(_SITE_JSON_PATH), emitted
        )
        project_files["public/reference-assets/manifest.json"] = json.dumps(
            {
                "schema": _REFERENCE_SCHEMA,
                "usage": _REFERENCE_USAGE,
                "assets": emitted,
            },
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
        ).encode("utf-8")

        digest = _project_digest(project_files)
        project_id = f"ilaios-next-{digest[:20]}"
        derived_root = allowed_root / project_id
        _materialize_derived_project(derived_root, project_files)

        manifest["source_project_id"] = project_id
        manifest["source_project_path"] = str(derived_root)
        manifest["source_project_digest"] = digest
        manifest["source_project_files"] = [
            {
                "path": path,
                "sha256": hashlib.sha256(body).hexdigest(),
                "size": len(body),
            }
            for path, body in sorted(project_files.items())
        ]
        manifest["reference_assets"] = expected_metadata
        manifest["reference_asset_source_files"] = emitted
        manifest["reference_asset_usage"] = _REFERENCE_USAGE
        manifest["reference_asset_render_component"] = _PAGE_SHELL_PATH
        qa = manifest.get("qa")
        if isinstance(qa, dict):
            qa = dict(qa)
            qa["reference_assets_bound"] = True
            qa["reference_asset_count"] = len(references)
            qa["reference_asset_rendered_source"] = True
            manifest["qa"] = qa

        serialized = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            changed = connection.execute(
                "UPDATE web_product_requests SET manifest_json=? "
                "WHERE request_id=? AND status='finalizing'",
                (serialized, request_id),
            ).rowcount
        if changed != 1:
            raise WebProductRuntimeError(
                "Web reference image evidence could not be bound to finalization"
            )


def _assert_reference_ownership(
    references: tuple[ReferenceAssetRecord, ...],
    *,
    principal_id: str,
    tenant_id: str,
) -> None:
    if any(
        record.principal_id != principal_id or record.tenant_id != tenant_id
        for record in references
    ):
        raise WebProductRuntimeError(
            "Web reference image ownership does not match execution identity"
        )


def _public_metadata(record: ReferenceAssetRecord) -> dict[str, object]:
    return {
        "asset_id": record.asset_id,
        "sha256": record.sha256,
        "mime_type": record.mime_type,
        "original_filename": record.original_filename,
        "width": record.width,
        "height": record.height,
        "size_bytes": record.size_bytes,
        "role": record.role.value,
        "instruction": record.instruction,
    }


def _reference_alt(record: ReferenceAssetRecord, index: int) -> str:
    role = record.role.value.replace("_", " ")
    filename = record.original_filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ")
    clean = " ".join(filename.split())[:80]
    return f"Reference {index}: {role} — {clean or 'user supplied image'}"


def _extension(mime_type: str) -> str:
    try:
        return {
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/webp": ".webp",
        }[mime_type]
    except KeyError as error:
        raise WebProductRuntimeError(
            "unsupported admitted Web reference image type"
        ) from error


def _read_project_files(root: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise WebProductRuntimeError(
                "Web source project contains a symbolic link before reference binding"
            )
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative.startswith(".next/") or relative.startswith("node_modules/"):
            continue
        files[relative] = path.read_bytes()
    if not files:
        raise WebProductRuntimeError("reference-aware Web source project is empty")
    return files


def _patch_page_shell(
    body: bytes | None,
    render_assets: list[dict[str, str]],
) -> bytes:
    if body is None:
        raise WebProductRuntimeError("generated Web PageShell.tsx is missing")
    text = body.decode("utf-8")
    if _REFERENCE_MARKER in text:
        return body
    assets_json = json.dumps(render_assets, ensure_ascii=False, separators=(",", ":"))
    labels_marker = "const labels: Record<string, Record<string, string>> = {"
    if labels_marker not in text:
        raise WebProductRuntimeError(
            "generated Web PageShell reference insertion point is missing"
        )
    text = text.replace(
        labels_marker,
        (
            f"// {_REFERENCE_MARKER}\n"
            f"const referenceAssets = {assets_json} as const;\n\n"
            + labels_marker
        ),
        1,
    )
    aside_prefix = '            <aside className="composition-note"'
    strong_marker = '              <strong>{props.primaryComposition.replaceAll("-", " ")}</strong>'
    if text.count(aside_prefix) != 1:
        raise WebProductRuntimeError(
            "generated Web reference render insertion point is missing"
        )
    aside_start = text.index(aside_prefix)
    strong_start = text.find(strong_marker, aside_start)
    if strong_start < 0:
        raise WebProductRuntimeError(
            "generated Web reference render insertion point is missing"
        )
    aside_open_end = text.find("\n", aside_start, strong_start)
    if aside_open_end < 0 or text[aside_open_end + 1 : strong_start].strip():
        raise WebProductRuntimeError(
            "generated Web reference render insertion point is missing"
        )
    asset_render = (
        '              {referenceAssets.length > 0 && (\n'
        '                <div className="reference-assets" aria-label={props.locale === "tr" ? "Referans görseller" : "Reference images"}>\n'
        '                  {referenceAssets.map((asset) => (\n'
        '                    <figure className="reference-asset" key={asset.sha256}>\n'
        '                      <img src={asset.src} alt={asset.alt} loading="eager" decoding="async" />\n'
        '                      {asset.instruction && <figcaption>{asset.instruction}</figcaption>}\n'
        '                    </figure>\n'
        '                  ))}\n'
        '                </div>\n'
        '              )}\n'
    )
    text = text[:strong_start] + asset_render + text[strong_start:]
    return text.encode("utf-8")


def _patch_css(body: bytes | None) -> bytes:
    if body is None:
        raise WebProductRuntimeError("generated Web globals.css is missing")
    text = body.decode("utf-8")
    if f"/* {_REFERENCE_MARKER} */" in text:
        return body
    addition = (
        f"\n/* {_REFERENCE_MARKER} */\n"
        ".reference-assets{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.65rem;margin-bottom:1rem}"
        ".reference-asset{margin:0;display:grid;gap:.35rem}"
        ".reference-asset img{display:block;width:100%;aspect-ratio:4/3;object-fit:cover;border:1px solid var(--line);background:var(--surface)}"
        ".reference-asset figcaption{font-size:.72rem;line-height:1.35;color:var(--muted)}"
        "@media(max-width:768px){.reference-assets{grid-template-columns:repeat(2,minmax(0,1fr))}}"
        "@media(max-width:430px){.reference-assets{grid-template-columns:1fr}}\n"
    )
    return (text + addition).encode("utf-8")


def _patch_site_json(
    body: bytes | None,
    emitted: list[dict[str, object]],
) -> bytes:
    if body is None:
        raise WebProductRuntimeError("generated Web site.json is missing")
    try:
        value = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise WebProductRuntimeError("generated Web site.json is malformed") from error
    if not isinstance(value, dict):
        raise WebProductRuntimeError("generated Web site.json is malformed")
    value["reference_assets"] = emitted
    value["reference_asset_usage"] = _REFERENCE_USAGE
    return json.dumps(
        value,
        sort_keys=True,
        indent=2,
        ensure_ascii=False,
    ).encode("utf-8")


def _project_digest(files: dict[str, bytes]) -> str:
    material = b"".join(
        path.encode() + b"\0" + body + b"\0"
        for path, body in sorted(files.items())
    )
    return hashlib.sha256(material).hexdigest()


def _materialize_derived_project(root: Path, files: dict[str, bytes]) -> None:
    if root.exists():
        if root.is_symlink() or _read_project_files(root) != files:
            raise WebProductRuntimeError(
                "content-addressed Web reference project has conflicting bytes"
            )
        return
    temporary = root.with_name(
        f".{root.name}.{os.getpid()}.{threading.get_ident()}.tmp"
    )
    if temporary.exists():
        raise WebProductRuntimeError("stale Web reference project staging path exists")
    temporary.mkdir(parents=True)
    try:
        for relative_path, body in sorted(files.items()):
            target = temporary / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
        try:
            temporary.rename(root)
        except FileExistsError:
            if root.is_symlink() or _read_project_files(root) != files:
                raise WebProductRuntimeError(
                    "concurrent Web reference project has conflicting bytes"
                )
    finally:
        if temporary.exists():
            for item in sorted(temporary.rglob("*"), reverse=True):
                if item.is_symlink() or item.is_file():
                    item.unlink()
                elif item.is_dir():
                    item.rmdir()
            temporary.rmdir()


# Preserve the canonical import name for composition roots that already import
# RecoverableWebProductRuntime from services.integrations.
RecoverableWebProductRuntime = ReferenceAwareRecoverableWebProductRuntime

__all__ = ["RecoverableWebProductRuntime", "ReferenceAwareRecoverableWebProductRuntime"]
