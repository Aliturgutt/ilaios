"""Optional governed 3D / Motion / WebGL runtime foundation for Web Factory.

This module starts Phase 16 without creating a second Web runtime. It converts an
explicit 3D/motion Web objective into a deterministic, auditable runtime plan and
can emit a dependency-free browser artifact using native WebGL. The artifact is a
local executable source proof only; it is not deployment, production, or live-E2E
evidence.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Literal

_MAX_OBJECTIVE_CHARS = 20_000
_SHA256_LEN = 64

Web3DFeature = Literal[
    "3d-hero",
    "scroll-camera",
    "product-rotation",
    "parallax",
    "particles",
    "webgl-background",
    "3d-typography",
    "pointer-interaction",
]
Web3DAssetRole = Literal["model", "texture", "poster"]
Web3DAssetMediaType = Literal[
    "model/gltf+json",
    "model/gltf-binary",
    "image/png",
    "image/jpeg",
    "image/webp",
]

_ALLOWED_MEDIA_TYPES: frozenset[str] = frozenset(
    {
        "model/gltf+json",
        "model/gltf-binary",
        "image/png",
        "image/jpeg",
        "image/webp",
    }
)
_WEB_TERMS = (
    "website",
    "web site",
    "web app",
    "web application",
    "web sitesi",
    "web uygulaması",
    "web uygulamasi",
)
_EXPLICIT_3D_TERMS = (
    "3d",
    "webgl",
    "webgpu",
    "three-dimensional",
    "three dimensional",
    "üç boyutlu",
    "uc boyutlu",
)


class Web3DRuntimeError(ValueError):
    """The bounded 3D runtime request cannot be represented safely."""


@dataclass(frozen=True, slots=True)
class Web3DAssetRef:
    """Immutable metadata for an already-admitted model/texture/poster asset."""

    sha256: str
    media_type: Web3DAssetMediaType
    byte_size: int
    role: Web3DAssetRole

    def __post_init__(self) -> None:
        if len(self.sha256) != _SHA256_LEN or any(
            char not in "0123456789abcdef" for char in self.sha256
        ):
            raise Web3DRuntimeError("3D asset sha256 must be lowercase hexadecimal")
        if self.media_type not in _ALLOWED_MEDIA_TYPES:
            raise Web3DRuntimeError("3D asset media type is not allowlisted")
        if self.byte_size < 1:
            raise Web3DRuntimeError("3D asset byte_size must be positive")
        if self.byte_size > 16 * 1024 * 1024:
            raise Web3DRuntimeError("individual 3D asset exceeds the 16 MiB budget")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class Web3DPerformanceBudget:
    max_bundle_bytes: int = 220_000
    max_total_asset_bytes: int = 32 * 1024 * 1024
    max_device_pixel_ratio: float = 2.0
    min_target_fps: int = 30
    max_webgl_contexts: int = 1

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class Web3DRuntimePlan:
    schema_version: str
    objective_sha256: str
    features: tuple[Web3DFeature, ...]
    assets: tuple[Web3DAssetRef, ...]
    performance: Web3DPerformanceBudget
    capability_detection: str
    reduced_motion_mode: str
    fallback_mode: str
    renderer: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "objective_sha256": self.objective_sha256,
            "features": list(self.features),
            "assets": [asset.to_dict() for asset in self.assets],
            "performance": self.performance.to_dict(),
            "capability_detection": self.capability_detection,
            "reduced_motion_mode": self.reduced_motion_mode,
            "fallback_mode": self.fallback_mode,
            "renderer": self.renderer,
        }

    @property
    def plan_sha256(self) -> str:
        encoded = json.dumps(
            self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class Web3DArtifact:
    filename: str
    media_type: str
    source: str
    source_sha256: str
    bundle_bytes: int
    plan_sha256: str


def compile_web_3d_runtime_plan(
    objective: str,
    *,
    assets: tuple[Web3DAssetRef, ...] = (),
) -> Web3DRuntimePlan:
    """Compile an explicit Web 3D request into a deterministic fail-closed plan."""
    if not objective or objective != objective.strip():
        raise Web3DRuntimeError("3D Web objective must be non-blank and trimmed")
    if len(objective) > _MAX_OBJECTIVE_CHARS:
        raise Web3DRuntimeError("3D Web objective exceeds the input limit")

    normalized = " ".join(objective.casefold().split())
    if not any(term in normalized for term in _WEB_TERMS):
        raise Web3DRuntimeError("objective does not explicitly target a Web surface")
    if not any(term in normalized for term in _EXPLICIT_3D_TERMS):
        raise Web3DRuntimeError(
            "objective does not explicitly require the optional 3D/WebGL capability"
        )

    if len(assets) > 12:
        raise Web3DRuntimeError("3D asset count exceeds the bounded limit")
    if sum(asset.byte_size for asset in assets) > 32 * 1024 * 1024:
        raise Web3DRuntimeError("3D assets exceed the 32 MiB total budget")

    features = _features(normalized)
    return Web3DRuntimePlan(
        schema_version="ilaios.web.3d-runtime-plan.v1",
        objective_sha256=hashlib.sha256(objective.encode("utf-8")).hexdigest(),
        features=features,
        assets=assets,
        performance=Web3DPerformanceBudget(),
        capability_detection="webgl2->webgl1->static-2d",
        reduced_motion_mode="static-2d-no-continuous-animation",
        fallback_mode="static-2d",
        renderer="native-webgl-bounded-v1",
    )


def render_native_webgl_artifact(plan: Web3DRuntimePlan) -> Web3DArtifact:
    """Emit a dependency-free browser artifact for the bounded native WebGL proof."""
    if plan.renderer != "native-webgl-bounded-v1":
        raise Web3DRuntimeError("unsupported 3D renderer")
    if plan.performance.max_webgl_contexts != 1:
        raise Web3DRuntimeError("native 3D proof requires exactly one WebGL context")

    features_json = json.dumps(list(plan.features), separators=(",", ":"))
    source = _html_source(plan, features_json)
    bundle_bytes = len(source.encode("utf-8"))
    if bundle_bytes > plan.performance.max_bundle_bytes:
        raise Web3DRuntimeError("generated 3D browser artifact exceeds bundle budget")
    source_sha = hashlib.sha256(source.encode("utf-8")).hexdigest()
    return Web3DArtifact(
        filename="index.html",
        media_type="text/html; charset=utf-8",
        source=source,
        source_sha256=source_sha,
        bundle_bytes=bundle_bytes,
        plan_sha256=plan.plan_sha256,
    )


def _features(normalized: str) -> tuple[Web3DFeature, ...]:
    selected: list[Web3DFeature] = []

    def add(feature: Web3DFeature) -> None:
        if feature not in selected:
            selected.append(feature)

    if any(term in normalized for term in ("hero", "landing", "launch", "tanıtım", "tanitim")):
        add("3d-hero")
    if any(
        term in normalized
        for term in ("scroll", "camera", "kamera", "scroll-driven", "scroll driven")
    ):
        add("scroll-camera")
    if any(
        term in normalized
        for term in ("rotate", "rotation", "product model", "model rotation", "döndür", "dondur")
    ):
        add("product-rotation")
    if any(term in normalized for term in ("parallax", "paralaks")):
        add("parallax")
    if any(term in normalized for term in ("particle", "particles", "parçacık", "parcacik")):
        add("particles")
    if any(term in normalized for term in ("webgl background", "3d background", "3d arka plan")):
        add("webgl-background")
    if any(term in normalized for term in ("3d typography", "3d text", "3d tipografi")):
        add("3d-typography")
    if any(
        term in normalized
        for term in ("interactive", "mouse", "pointer", "touch", "etkileşim", "etkilesim")
    ):
        add("pointer-interaction")
    if not selected:
        add("3d-hero")
    return tuple(selected)


def _html_source(plan: Web3DRuntimePlan, features_json: str) -> str:
    max_dpr = plan.performance.max_device_pixel_ratio
    min_fps = plan.performance.min_target_fps
    return f"""<!doctype html>
<html lang=\"en\">
<head>
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<title>ILAIOS Web 3D Runtime Proof</title>
<style>
html,body{{margin:0;min-height:100%;background:#0A0A0A;color:#FFFFFF;font-family:system-ui,sans-serif}}
main{{min-height:180vh}}
.hero{{position:sticky;top:0;height:100vh;overflow:hidden;display:grid;place-items:center}}
canvas{{position:absolute;inset:0;width:100%;height:100%}}
.copy{{position:relative;z-index:2;text-align:center;pointer-events:none}}
.copy h1{{font-size:clamp(2rem,7vw,6rem);margin:0;letter-spacing:-.04em}}
.copy p{{max-width:42rem;margin:1rem auto 0;color:#B3B3B3}}
.fallback{{position:absolute;inset:0;display:none;place-items:center;background:#141414}}
.fallback-card{{border:1px solid #2A2A2A;padding:2rem;border-radius:16px;max-width:34rem}}
[data-fallback=\"on\"] .fallback{{display:grid}}
[data-fallback=\"on\"] canvas{{display:none}}
</style>
</head>
<body>
<main>
<section class=\"hero\" id=\"ilaios-3d-root\" data-plan-sha=\"{plan.plan_sha256}\">
<canvas id=\"scene\" aria-hidden=\"true\"></canvas>
<div class=\"fallback\"><div class=\"fallback-card\"><strong>3D preview unavailable</strong><p>The same content remains available without motion.</p></div></div>
<div class=\"copy\"><h1>3D Web Runtime</h1><p>Native WebGL capability proof with bounded motion, pointer input, scroll response, and deterministic 2D fallback.</p></div>
</section>
</main>
<script>
(()=>{{
'use strict';
const FEATURES={features_json};
const root=document.getElementById('ilaios-3d-root');
const canvas=document.getElementById('scene');
const reduce=window.matchMedia('(prefers-reduced-motion: reduce)');
if(!(root instanceof HTMLElement)||!(canvas instanceof HTMLCanvasElement))return;
const fallback=()=>root.setAttribute('data-fallback','on');
if(reduce.matches){{fallback();return;}}
const gl=canvas.getContext('webgl2',{{alpha:false,antialias:true,powerPreference:'high-performance'}})||canvas.getContext('webgl',{{alpha:false,antialias:true,powerPreference:'high-performance'}});
if(!gl){{fallback();return;}}
const vs=`attribute vec3 p;uniform float t;uniform float s;uniform vec2 m;void main(){{float a=t*.00045+s*1.8+m.x*.35;float c=cos(a),q=sin(a);vec3 v=vec3(p.x*c-p.z*q,p.y+m.y*.12,p.x*q+p.z*c);float z=v.z+4.2;gl_Position=vec4(v.x/z*1.65,v.y/z*1.65,(z-2.0)/6.0,1.0);}}`;
const fs=`precision mediump float;void main(){{gl_FragColor=vec4(.9019608,.9019608,.9019608,1.0);}}`;
const shader=(type,src)=>{{const sh=gl.createShader(type);if(!sh)throw new Error('shader');gl.shaderSource(sh,src);gl.compileShader(sh);if(!gl.getShaderParameter(sh,gl.COMPILE_STATUS))throw new Error('shader-compile');return sh;}};
let program;
try{{program=gl.createProgram();if(!program)throw new Error('program');gl.attachShader(program,shader(gl.VERTEX_SHADER,vs));gl.attachShader(program,shader(gl.FRAGMENT_SHADER,fs));gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw new Error('program-link');}}catch(_error){{fallback();return;}}
gl.useProgram(program);
const verts=new Float32Array([-1,-1,-1,1,-1,-1,1,1,-1,-1,1,-1,-1,-1,1,1,-1,1,1,1,1,-1,1,1]);
const idx=new Uint16Array([0,1,2,0,2,3,4,6,5,4,7,6,0,4,5,0,5,1,3,2,6,3,6,7,1,5,6,1,6,2,0,3,7,0,7,4]);
const vb=gl.createBuffer(),ib=gl.createBuffer();if(!vb||!ib){{fallback();return;}}
gl.bindBuffer(gl.ARRAY_BUFFER,vb);gl.bufferData(gl.ARRAY_BUFFER,verts,gl.STATIC_DRAW);gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,ib);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,idx,gl.STATIC_DRAW);
const loc=gl.getAttribLocation(program,'p');gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,3,gl.FLOAT,false,0,0);
const timeLoc=gl.getUniformLocation(program,'t'),scrollLoc=gl.getUniformLocation(program,'s'),mouseLoc=gl.getUniformLocation(program,'m');
let mx=0,my=0,last=0;
const interactive=FEATURES.includes('pointer-interaction')||FEATURES.includes('product-rotation');
if(interactive)window.addEventListener('pointermove',e=>{{mx=e.clientX/Math.max(1,innerWidth)*2-1;my=1-e.clientY/Math.max(1,innerHeight)*2;}},{{passive:true}});
const resize=()=>{{const d=Math.min({max_dpr},window.devicePixelRatio||1);const w=Math.max(1,Math.floor(canvas.clientWidth*d)),h=Math.max(1,Math.floor(canvas.clientHeight*d));if(canvas.width!==w||canvas.height!==h){{canvas.width=w;canvas.height=h;gl.viewport(0,0,w,h);}}}};
const frame=now=>{{if(reduce.matches){{fallback();return;}}resize();const minDelta=1000/{min_fps};if(now-last>=minDelta){{last=now;gl.clearColor(.0392157,.0392157,.0392157,1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.enable(gl.DEPTH_TEST);const scroll=FEATURES.includes('scroll-camera')?window.scrollY/Math.max(1,document.documentElement.scrollHeight-innerHeight):0;gl.uniform1f(timeLoc,now);gl.uniform1f(scrollLoc,scroll);gl.uniform2f(mouseLoc,mx,my);gl.drawElements(gl.TRIANGLES,idx.length,gl.UNSIGNED_SHORT,0);}}requestAnimationFrame(frame);}};
requestAnimationFrame(frame);
}})();
</script>
</body>
</html>"""


__all__ = [
    "Web3DArtifact",
    "Web3DAssetRef",
    "Web3DPerformanceBudget",
    "Web3DRuntimeError",
    "Web3DRuntimePlan",
    "compile_web_3d_runtime_plan",
    "render_native_webgl_artifact",
]
