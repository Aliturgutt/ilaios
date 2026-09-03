"""Source-level 3D capability integration for generated Web Factory content.

This module composes the optional native WebGL artifact into an already-generated
website bundle without changing the canonical Web runtime, router, governance, or
deployment authorities. It is an integration seam only; callers must still supply
governed acceptance and production evidence before claiming Phase-16 readiness.
"""

from __future__ import annotations

import hashlib
import json
import posixpath
from dataclasses import dataclass

from services.web_3d_runtime import Web3DRuntimePlan, render_native_webgl_artifact

_RUNTIME_PATH = "assets/3d/index.html"
_STYLESHEET_PATH = "assets/site.css"
_HOME_MARKER = '<main id="main">'
_EMBED_STYLE = b"""
.ilaios-web3d{margin:0 0 clamp(2rem,6vw,6rem);display:grid;gap:1rem}
.ilaios-web3d-frame{width:100%;min-height:min(72vh,760px);border:0;border-radius:18px;background:#0a0a0a}
.ilaios-web3d-fallback{margin:0;color:var(--muted,#808080)}
@media (max-width:720px){.ilaios-web3d-frame{min-height:58vh;border-radius:12px}}
@media (prefers-reduced-motion:reduce){.ilaios-web3d-frame{min-height:42vh}}
"""


class Web3DIntegrationError(ValueError):
    """Generated Web content cannot be safely augmented with the optional 3D pack."""


@dataclass(frozen=True, slots=True)
class Web3DIntegratedFile:
    relative_path: str
    sha256: str
    size: int


@dataclass(frozen=True, slots=True)
class Web3DIntegratedBundle:
    schema_version: str
    plan_sha256: str
    runtime_source_sha256: str
    runtime_path: str
    home_routes: tuple[str, ...]
    files: tuple[Web3DIntegratedFile, ...]
    content: dict[str, bytes]
    bundle_sha256: str


def integrate_web_3d_into_generated_content(
    content: dict[str, bytes],
    plan: Web3DRuntimePlan,
    *,
    home_routes: tuple[str, ...],
) -> Web3DIntegratedBundle:
    """Inject a sandboxed same-origin 3D runtime into explicit home routes."""
    if not content:
        raise Web3DIntegrationError("generated Web content must be non-empty")
    if not home_routes or len(set(home_routes)) != len(home_routes):
        raise Web3DIntegrationError("3D integration home routes must be unique and non-empty")
    if _STYLESHEET_PATH not in content:
        raise Web3DIntegrationError("generated Web content is missing the canonical stylesheet")

    for route in home_routes:
        if route not in content:
            raise Web3DIntegrationError(f"3D integration home route is missing: {route}")
        if posixpath.basename(route) != "index.html":
            raise Web3DIntegrationError(
                "3D integration may only target generated home index routes"
            )

    artifact = render_native_webgl_artifact(plan)
    runtime_bytes = artifact.source.encode("utf-8")
    existing_runtime = content.get(_RUNTIME_PATH)
    if existing_runtime is not None and existing_runtime != runtime_bytes:
        raise Web3DIntegrationError("existing 3D runtime path has conflicting content")

    integrated = dict(content)
    integrated[_RUNTIME_PATH] = runtime_bytes
    for route in home_routes:
        raw = content[route]
        try:
            html = raw.decode("utf-8")
        except UnicodeDecodeError as error:
            raise Web3DIntegrationError(
                f"3D integration home route is not UTF-8: {route}"
            ) from error
        if html.count(_HOME_MARKER) != 1:
            raise Web3DIntegrationError(
                f"3D integration requires one canonical main marker: {route}"
            )
        relative_runtime = posixpath.relpath(
            _RUNTIME_PATH,
            start=posixpath.dirname(route) or ".",
        )
        embed = _embed_markup(relative_runtime, plan.plan_sha256)
        integrated[route] = html.replace(
            _HOME_MARKER,
            f"{_HOME_MARKER}{embed}",
            1,
        ).encode("utf-8")

    stylesheet = integrated[_STYLESHEET_PATH]
    if _EMBED_STYLE not in stylesheet:
        integrated[_STYLESHEET_PATH] = stylesheet.rstrip() + b"\n" + _EMBED_STYLE

    files = tuple(
        Web3DIntegratedFile(
            relative_path=path,
            sha256=hashlib.sha256(body).hexdigest(),
            size=len(body),
        )
        for path, body in sorted(integrated.items())
    )
    bundle_sha = _bundle_sha256(files, plan.plan_sha256)
    return Web3DIntegratedBundle(
        schema_version="ilaios.web.3d-integrated-bundle.v1",
        plan_sha256=plan.plan_sha256,
        runtime_source_sha256=artifact.source_sha256,
        runtime_path=_RUNTIME_PATH,
        home_routes=home_routes,
        files=files,
        content=integrated,
        bundle_sha256=bundle_sha,
    )


def _embed_markup(relative_runtime: str, plan_sha256: str) -> str:
    return (
        '<section class="ilaios-web3d" aria-label="Interactive 3D presentation" '
        f'data-plan-sha="{plan_sha256}">'
        '<iframe class="ilaios-web3d-frame" '
        'title="Interactive 3D product presentation" '
        f'src="{relative_runtime}" sandbox="allow-scripts" '
        'referrerpolicy="no-referrer"></iframe>'
        '<p class="ilaios-web3d-fallback">'
        "3D motion is optional; equivalent page content remains available "
        "without the interactive scene."
        "</p></section>"
    )


def _bundle_sha256(
    files: tuple[Web3DIntegratedFile, ...],
    plan_sha256: str,
) -> str:
    canonical = {
        "files": [
            {
                "path": item.relative_path,
                "sha256": item.sha256,
                "size": item.size,
            }
            for item in files
        ],
        "plan_sha256": plan_sha256,
    }
    encoded = json.dumps(
        canonical,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


__all__ = [
    "Web3DIntegratedBundle",
    "Web3DIntegratedFile",
    "Web3DIntegrationError",
    "integrate_web_3d_into_generated_content",
]
