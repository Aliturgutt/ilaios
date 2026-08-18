"""Reference-image aware extension of the verified Web finished-product runtime."""

from __future__ import annotations

import hashlib
import json
import os
import threading
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import cast

from services.control_plane import BudgetEnvelope, DataClass
from services.reference_assets import ReferenceAssetRecord, get_reference_asset_store

from .web_factory import WebsiteSpec
from .web_product_runtime import WebProductRuntimeError
from .web_product_runtime_recovery import RecoverableWebProductRuntime


class ReferenceAwareRecoverableWebProductRuntime(RecoverableWebProductRuntime):
    """Bind user reference images into design context, rendered source, and evidence."""

    def prepare(
        self,
        request_id: str,
        objective: str,
        *,
        token: str,
        now: datetime,
        requester_id: str,
        tenant_id: str,
        risk: str = "medium",
        data_class: DataClass = DataClass.INTERNAL,
        budget: BudgetEnvelope = BudgetEnvelope(2, 120, 0),
    ) -> dict[str, object]:
        prepared = super().prepare(
            request_id,
            objective,
            token=token,
            now=now,
            requester_id=requester_id,
            tenant_id=tenant_id,
            risk=risk,
            data_class=data_class,
            budget=budget,
        )
        references = get_reference_asset_store().for_request(request_id)
        if not references:
            return prepared

        with self._connect() as connection:
            row = connection.execute(
                "SELECT spec_json FROM web_product_requests WHERE request_id=?",
                (request_id,),
            ).fetchone()
            if row is None:
                raise WebProductRuntimeError("reference-aware Web request disappeared")
            value = json.loads(str(row["spec_json"]))
            if not isinstance(value, dict):
                raise WebProductRuntimeError("stored WebsiteSpec is malformed")
            spec = WebsiteSpec.from_dict(cast(dict[str, object], value))
            enriched = replace(spec, visual_asset_availability="rich")
            connection.execute(
                "UPDATE web_product_requests SET spec_json=? WHERE request_id=?",
                (
                    json.dumps(
                        enriched.to_dict(), sort_keys=True, separators=(",", ":")
                    ),
                    request_id,
                ),
            )

        result = dict(prepared)
        result["reference_asset_count"] = len(references)
        result["reference_assets"] = [item.public_metadata() for item in references]
        result["visual_asset_availability"] = "rich"
        return result

    def recover_finalizing(
        self,
        request_id: str,
        *,
        token: str,
        now: datetime,
    ) -> dict[str, object]:
        references = get_reference_asset_store().for_request(request_id)
        if references:
            self._bind_references_before_assurance(request_id, references)
        manifest = super().recover_finalizing(request_id, token=token, now=now)
        if references:
            self._verify_reference_acceptance(manifest, references)
        return manifest

    def _bind_references_before_assurance(
        self,
        request_id: str,
        references: tuple[ReferenceAssetRecord, ...],
    ) -> None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT status, manifest_json FROM web_product_requests WHERE request_id=?",
                (request_id,),
            ).fetchone()
        if row is None:
            raise WebProductRuntimeError("unknown reference-aware Web request")
        if row["status"] == "accepted":
            return
        if row["status"] != "finalizing" or row["manifest_json"] is None:
            return
        value = json.loads(str(row["manifest_json"]))
        if not isinstance(value, dict):
            raise WebProductRuntimeError("stored finalizing Web manifest is malformed")
        manifest = cast(dict[str, object], value)
        expected_metadata = [item.public_metadata() for item in references]
        if (
            manifest.get("reference_assets") == expected_metadata
            and manifest.get("reference_asset_rendered") is True
        ):
            self._verify_reference_acceptance(manifest, references)
            return

        source_value = manifest.get("source_project_path")
        if not isinstance(source_value, str) or not source_value:
            raise WebProductRuntimeError("Web source path is missing before reference binding")
        source_root = Path(source_value)
        if not source_root.is_dir():
            raise WebProductRuntimeError("Web source path is unavailable before reference binding")

        # Source projects are content addressed and can be shared by equivalent
        # executions. Never mutate the original project in place. Build a new
        # deterministic copy-on-write project whose digest includes references.
        project_files = _project_files(source_root)
        emitted: list[dict[str, object]] = []
        store = get_reference_asset_store()
        for index, record in enumerate(references, start=1):
            extension = _extension(record.media_type)
            relative_path = (
                f"public/reference-assets/reference-{index:02d}-"
                f"{record.sha256[:12]}{extension}"
            )
            project_files[relative_path] = store.read_bytes(record)
            emitted.append({**record.public_metadata(), "source_path": relative_path})

        render_paths = _bind_rendered_reference_gallery(project_files, emitted)
        reference_manifest = {
            "schema": "ilaios.web.reference-assets.v1",
            "usage": "asset-led-design-and-source",
            "rendered": True,
            "render_paths": render_paths,
            "assets": emitted,
        }
        project_files["public/reference-assets/manifest.json"] = json.dumps(
            reference_manifest,
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
        ).encode("utf-8")

        site_body = project_files.get("site.json")
        if site_body is None:
            raise WebProductRuntimeError("generated Web site.json is missing")
        site_value = json.loads(site_body.decode("utf-8"))
        if not isinstance(site_value, dict):
            raise WebProductRuntimeError("generated Web site.json is malformed")
        site_value["reference_assets"] = emitted
        site_value["reference_asset_usage"] = "asset-led-design-and-source"
        site_value["reference_asset_rendered"] = True
        site_value["reference_asset_render_paths"] = render_paths
        project_files["site.json"] = json.dumps(
            site_value,
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
        ).encode("utf-8")

        digest = _project_digest(project_files)
        project_id = f"ilaios-next-{digest[:20]}"
        derived_root = source_root.parent / project_id
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
        manifest["reference_asset_usage"] = "asset-led-design-and-source"
        manifest["reference_asset_rendered"] = True
        manifest["reference_asset_render_paths"] = render_paths
        design = manifest.get("design_strategy")
        if not isinstance(design, dict) or design.get("imagery_behavior") != "asset-led":
            raise WebProductRuntimeError(
                "Web design strategy did not consume the supplied visual references"
            )
        self._verify_reference_acceptance(manifest, references)
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

    def _verify_reference_acceptance(
        self,
        manifest: dict[str, object],
        references: tuple[ReferenceAssetRecord, ...],
    ) -> None:
        expected = [item.public_metadata() for item in references]
        if manifest.get("reference_assets") != expected:
            raise WebProductRuntimeError(
                "accepted Web manifest does not bind the supplied reference images"
            )
        if manifest.get("reference_asset_usage") != "asset-led-design-and-source":
            raise WebProductRuntimeError(
                "accepted Web manifest does not prove reference image usage"
            )
        if manifest.get("reference_asset_rendered") is not True:
            raise WebProductRuntimeError(
                "accepted Web manifest does not prove rendered reference image usage"
            )
        render_paths = manifest.get("reference_asset_render_paths")
        if not isinstance(render_paths, list) or len(render_paths) != len(references):
            raise WebProductRuntimeError(
                "accepted Web manifest has incomplete reference render paths"
            )
        if not all(
            isinstance(path, str) and path.startswith("/reference-assets/")
            for path in render_paths
        ):
            raise WebProductRuntimeError("accepted Web reference render path is malformed")
        source_value = manifest.get("source_project_path")
        if not isinstance(source_value, str) or not source_value:
            raise WebProductRuntimeError("accepted Web source path is missing")
        source_root = Path(source_value)
        shell_path = source_root / "components" / "PageShell.tsx"
        try:
            shell_source = shell_path.read_text(encoding="utf-8")
        except OSError as error:
            raise WebProductRuntimeError(
                "accepted Web source does not contain the reference renderer"
            ) from error
        for render_path, reference in zip(render_paths, references, strict=True):
            if not isinstance(render_path, str) or render_path not in shell_source:
                raise WebProductRuntimeError(
                    "accepted Web source does not reference every supplied image"
                )
            asset_path = source_root / "public" / render_path.removeprefix("/")
            try:
                body = asset_path.read_bytes()
            except OSError as error:
                raise WebProductRuntimeError(
                    "accepted Web reference image is missing from rendered source"
                ) from error
            if hashlib.sha256(body).hexdigest() != reference.sha256:
                raise WebProductRuntimeError(
                    "accepted Web rendered reference image failed digest verification"
                )


def _bind_rendered_reference_gallery(
    project_files: dict[str, bytes],
    emitted: list[dict[str, object]],
) -> list[str]:
    shell_key = "components/PageShell.tsx"
    shell_body = project_files.get(shell_key)
    if shell_body is None:
        raise WebProductRuntimeError("generated Web PageShell source is missing")
    shell = shell_body.decode("utf-8")
    render_assets: list[dict[str, str]] = []
    for item in emitted:
        source_path = item.get("source_path")
        sha256 = item.get("sha256")
        if not isinstance(source_path, str) or not source_path.startswith("public/"):
            raise WebProductRuntimeError("reference image source path is malformed")
        if not isinstance(sha256, str) or len(sha256) != 64:
            raise WebProductRuntimeError("reference image digest is malformed")
        render_assets.append(
            {"src": "/" + source_path.removeprefix("public/"), "sha256": sha256}
        )
    render_paths = [asset["src"] for asset in render_assets]

    declaration_anchor = "const labels: Record<string, Record<string, string>> = {"
    if declaration_anchor not in shell:
        raise WebProductRuntimeError("generated Web reference declaration anchor is missing")
    declaration = (
        "const referenceAssets = "
        + json.dumps(render_assets, ensure_ascii=False, separators=(",", ":"))
        + " as const;\n\n"
    )
    shell = shell.replace(declaration_anchor, declaration + declaration_anchor, 1)

    render_anchor = '''          {props.pageName === "home" && (
            <aside className="composition-note"'''
    if render_anchor not in shell:
        raise WebProductRuntimeError("generated Web reference render anchor is missing")
    gallery = '''          {props.pageName === "home" && referenceAssets.length > 0 && (
            <section className="reference-gallery" aria-label={props.locale === "tr" ? "Referans görseller" : "Reference visuals"}>
              {referenceAssets.map((asset, index) => (
                <figure className="reference-visual" key={asset.sha256}>
                  <img
                    src={asset.src}
                    alt={`${props.businessName} ${props.locale === "tr" ? "referans görseli" : "reference visual"} ${index + 1}`}
                    loading={index === 0 ? "eager" : "lazy"}
                  />
                </figure>
              ))}
            </section>
          )}
'''
    shell = shell.replace(render_anchor, gallery + render_anchor, 1)
    if not all(path in shell for path in render_paths):
        raise WebProductRuntimeError(
            "generated Web source did not bind every reference render path"
        )
    project_files[shell_key] = shell.encode("utf-8")

    css_key = "app/globals.css"
    css_body = project_files.get(css_key)
    if css_body is None:
        raise WebProductRuntimeError("generated Web global stylesheet is missing")
    css = css_body.decode("utf-8")
    css += '''

.reference-gallery {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;
  margin-top: 1.5rem;
}
.reference-visual {
  margin: 0;
  min-height: 180px;
  overflow: hidden;
  border: 1px solid currentColor;
  border-radius: 1rem;
  background: rgba(127, 127, 127, 0.08);
}
.reference-visual img {
  display: block;
  width: 100%;
  height: 100%;
  min-height: 180px;
  max-height: 420px;
  object-fit: contain;
}
'''
    project_files[css_key] = css.encode("utf-8")
    return render_paths


def _materialize_derived_project(root: Path, files: dict[str, bytes]) -> None:
    if root.exists():
        existing = _project_files(root)
        if existing != files:
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
            existing = _project_files(root)
            if existing != files:
                raise WebProductRuntimeError(
                    "concurrent Web reference project has conflicting bytes"
                )
    finally:
        if temporary.exists():
            for item in sorted(temporary.rglob("*"), reverse=True):
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    item.rmdir()
            temporary.rmdir()


def _extension(media_type: str) -> str:
    return {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/webp": ".webp",
    }[media_type]


def _project_files(root: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        if relative.startswith(".next/") or relative.startswith("node_modules/"):
            continue
        files[relative] = path.read_bytes()
    if not files:
        raise WebProductRuntimeError("reference-aware Web source project is empty")
    return files


def _project_digest(files: dict[str, bytes]) -> str:
    material = b"".join(
        path.encode("utf-8") + b"\0" + body + b"\0"
        for path, body in sorted(files.items())
    )
    return hashlib.sha256(material).hexdigest()
