"""Governed deterministic Web Factory golden workflow with real artifacts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from services.design_quality import DesignAssessment
from services.runtime import ExecutionGrant, GrantPolicy


@dataclass(frozen=True, slots=True)
class WebsiteFile:
    relative_path: str
    sha256: str
    size: int


@dataclass(frozen=True, slots=True)
class WebsiteAcceptance:
    manifest_version: str
    site_id: str
    artifact_hash: str
    bundle_id: str
    bundle_path: str
    required_pages: tuple[str, ...]
    official_brand: str
    files: tuple[WebsiteFile, ...]
    accepted: bool


class GovernedWebFactory:
    def __init__(self, grants: GrantPolicy, artifact_root: Path) -> None:
        self._grants = grants
        self._artifact_root = artifact_root

    @staticmethod
    def accept_design_quality(assessment: DesignAssessment) -> None:
        """Fail closed without introducing another policy or evidence runtime."""
        if assessment.evaluator_id != "design.final-polish":
            raise ValueError("unrecognized design quality evaluator")
        if assessment.status != "PASS" or assessment.blocking_findings:
            raise ValueError("website design quality gate failed")

    def build_official_site(
        self,
        site_id: str,
        pages: tuple[str, ...],
        *,
        grant: ExecutionGrant,
        now: datetime,
    ) -> WebsiteAcceptance:
        self._grants.authorize(
            grant,
            subject_id=grant.subject_id,
            action="web.build",
            resource=site_id,
            now=now,
        )
        if site_id != "ilaios-official":
            raise ValueError("official website requires the canonical site identity")
        required = ("home", "product", "security", "contact")
        if tuple(sorted(set(pages))) != tuple(sorted(required)):
            raise ValueError("official website requires the canonical page set")
        content = _site_content(required)
        identity_material = b"".join(
            path.encode() + b"\0" + body + b"\0"
            for path, body in sorted(content.items())
        )
        artifact_hash = hashlib.sha256(identity_material).hexdigest()
        bundle_id = f"ilaios-site-{artifact_hash[:20]}"
        bundle = self._artifact_root / bundle_id
        if bundle.exists():
            _verify_existing(bundle, content)
        else:
            bundle.mkdir(parents=True)
            for relative_path, body in content.items():
                path = bundle / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(body)
        files = tuple(
            WebsiteFile(path, hashlib.sha256(body).hexdigest(), len(body))
            for path, body in sorted(content.items())
        )
        _validate_site(bundle, required, files)
        acceptance = WebsiteAcceptance(
            "1.0",
            site_id,
            artifact_hash,
            bundle_id,
            str(bundle),
            required,
            "ILAIOS",
            files,
            True,
        )
        manifest_path = bundle / "acceptance.json"
        manifest_bytes = json.dumps(
            {
                "accepted": acceptance.accepted,
                "artifact_hash": acceptance.artifact_hash,
                "brand": acceptance.official_brand,
                "bundle_id": acceptance.bundle_id,
                "files": [
                    {
                        "path": item.relative_path,
                        "sha256": item.sha256,
                        "size": item.size,
                    }
                    for item in acceptance.files
                ],
                "manifest_version": acceptance.manifest_version,
                "required_pages": acceptance.required_pages,
                "site_id": acceptance.site_id,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        if manifest_path.exists() and manifest_path.read_bytes() != manifest_bytes:
            raise ValueError("website acceptance manifest was tampered")
        manifest_path.write_bytes(manifest_bytes)
        self._grants.record_side_effect(grant, site_id)
        return acceptance


def _site_content(pages: tuple[str, ...]) -> dict[str, bytes]:
    navigation = "".join(
        f'<a href="{page}.html">{page.title()}</a>' for page in pages
    )
    messages = {
        "home": "Governed intelligence for durable outcomes.",
        "product": "ILAIOS coordinates agents, evidence, and delivery.",
        "security": "Fail-closed grants and tamper-evident execution.",
        "contact": "Contact the ILAIOS team through governed channels.",
    }
    files = {
        f"{page}.html": (
            "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            f"<title>ILAIOS | {page.title()}</title>"
            '<link rel="stylesheet" href="assets/site.css"></head><body>'
            f"<header><strong>ILAIOS</strong><nav>{navigation}</nav></header>"
            f"<main><h1>{page.title()}</h1><p>{messages[page]}</p></main>"
            "</body></html>"
        ).encode()
        for page in pages
    }
    files["assets/site.css"] = (
        b"body{font-family:sans-serif;margin:2rem;color:#17223b}"
        b"header{display:flex;justify-content:space-between}nav a{margin:.5rem}"
    )
    return files


def _verify_existing(bundle: Path, expected: dict[str, bytes]) -> None:
    actual_paths = {
        path.relative_to(bundle).as_posix()
        for path in bundle.rglob("*")
        if path.is_file() and path.name != "acceptance.json"
    }
    if actual_paths != set(expected):
        raise ValueError("website artifact bundle file set was tampered")
    for relative_path, body in expected.items():
        if (bundle / relative_path).read_bytes() != body:
            raise ValueError("website artifact bundle content was tampered")


def _validate_site(
    bundle: Path, required: tuple[str, ...], files: tuple[WebsiteFile, ...]
) -> None:
    file_map = {item.relative_path: item for item in files}
    for page in required:
        relative_path = f"{page}.html"
        body = (bundle / relative_path).read_text(encoding="utf-8")
        if "ILAIOS" not in body or f"<h1>{page.title()}</h1>" not in body:
            raise ValueError("website brand or page content validation failed")
        for target in required:
            if f'href="{target}.html"' not in body:
                raise ValueError("website navigation validation failed")
        item = file_map[relative_path]
        encoded = body.encode()
        if hashlib.sha256(encoded).hexdigest() != item.sha256:
            raise ValueError("website file hash validation failed")

