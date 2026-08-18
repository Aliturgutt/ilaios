from __future__ import annotations

import gc
import hashlib
import json
import os
import shutil
import struct
import sys
import tempfile
import time
import zlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.control_plane.api import ControlPlane, ControlPlaneConfig
from services.control_plane.workflows import WorkflowStore, WorkflowStoreConfig
from services.desktop_execution_coordinator import DesktopExecutionCoordinator
from services.evidence import EvidenceStore
from services.governance import GovernedRuntimeGateway
from services.integrations.product_runtime import DurableVideoProductRuntime
from services.integrations.reference_aware_provider_video_runtime import (
    ReferenceAwareProviderBackedDesktopVideoRuntime,
)
from services.reference_asset_admission import ReferenceAssetAdmissionStore
from services.reference_assets import ReferenceAssetRole
from services.reference_brief_cache import ReferenceBriefCache
from services.runtime import DurableGrantPolicy, DurableWorkerScheduler, GovernedRuntime
from src.video_automation.ffmpeg_media_engine import FfmpegMediaEngine
from src.video_automation.openrouter_video_provider import (
    SEEDANCE_FREE_MODEL_ID,
    OpenRouterVideoGenerationJobPoller,
)


def main() -> int:
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required for live reference-provider E2E")
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise RuntimeError("live reference-provider E2E requires ffmpeg and ffprobe")

    proof_root = Path(
        os.environ.get(
            "VIDEO_DESKTOP_REFERENCE_PROVIDER_PROOF_DIR",
            "artifacts/video-desktop-reference-provider-proof",
        )
    ).resolve()
    proof_root.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix="ilaios-reference-provider-e2e-"))
    try:
        _run_reference_finished_product_acceptance(
            root=temporary,
            proof_root=proof_root,
            api_key=api_key,
        )
    finally:
        gc.collect()
        for attempt in range(5):
            try:
                shutil.rmtree(temporary)
                break
            except PermissionError:
                if attempt == 4:
                    raise
                gc.collect()
                time.sleep(0.25 * (attempt + 1))
    return 0


def _run_reference_finished_product_acceptance(
    *, root: Path, proof_root: Path, api_key: str
) -> None:
    token = "test"
    principal_id = "ci-reference-provider-video-user"
    tenant_id = "ci-reference-provider-video-tenant"
    request_id = "desktop-reference-provider-video-real-e2e"

    database = root / "control-plane.sqlite3"
    control_plane = ControlPlane(ControlPlaneConfig(database, token))
    workflows = WorkflowStore(WorkflowStoreConfig(database))
    governed_runtime = GovernedRuntime(database)
    scheduler = DurableWorkerScheduler(database, lease_duration=timedelta(seconds=30))
    grants = DurableGrantPolicy(database)
    evidence = EvidenceStore(root / "evidence")
    governance = GovernedRuntimeGateway(
        root / "governance.sqlite3",
        governed_runtime,
        hard_cap_minor=100,
    )
    references = ReferenceAssetAdmissionStore(
        root / "reference-assets.sqlite3",
        root / "reference-assets" / "blobs",
    )

    def resolve_objective(job_id: str) -> str:
        job = control_plane.get_job(token, job_id)
        return control_plane.get_goal(token, job.goal_id).objective

    poller = OpenRouterVideoGenerationJobPoller(
        api_key,
        provider_id=ReferenceAwareProviderBackedDesktopVideoRuntime.PROVIDER_ID,
    )
    video = ReferenceAwareProviderBackedDesktopVideoRuntime(
        root / "video",
        grants,
        governance,
        evidence,
        objective_resolver=resolve_objective,
        api_key=api_key,
        model_id=os.environ.get("ILAIOS_VIDEO_MODEL_ID", SEEDANCE_FREE_MODEL_ID).strip(),
        qa_model_id=os.environ.get("ILAIOS_VIDEO_QA_MODEL_ID", "openrouter/free").strip(),
        resolution=os.environ.get("ILAIOS_VIDEO_E2E_RESOLUTION", "480p").strip(),
        poll_interval_seconds=5.0,
        max_poll_rounds=144,
        poller=poller,
        reference_assets=references,
    )
    product = DurableVideoProductRuntime(
        root / "product-proof.sqlite3",
        control_plane,
        workflows,
        scheduler,
        grants,
        governance,
        video,
    )
    coordinator = DesktopExecutionCoordinator(
        root / "execution-coordinator.sqlite3",
        control_plane,
        governance,
        grants,
        product,
        evidence,
    )

    objective = (
        "Video creation task: Create a finished cinematic product video exactly 8 seconds long. "
        "Use the attached product reference as the visual source of truth. Preserve its observable "
        "matte dark geometry, cyan illuminated vertical feature, orange circular emblem placement, "
        "and light accent marks. Present the same product as a premium studio reveal with realistic "
        "material response, controlled camera motion, subtle atmospheric depth, and clean audio. "
        "The result must be continuous visual footage, not title cards, presentation slides, static "
        "text panels, or generic motion graphics. Do not publish anywhere."
    )
    now = datetime.now(timezone.utc)
    prepared = coordinator.prepare(
        request_id,
        objective,
        token=token,
        principal_id=principal_id,
        tenant_id=tenant_id,
        now=now,
    )
    if prepared.get("execution_status") != "ADMITTED":
        raise RuntimeError(f"reference video request was not admitted: {prepared}")
    if prepared.get("adapter_id") != "video.product-runtime.v1":
        raise RuntimeError(f"wrong video adapter: {prepared}")

    asset = references.put(
        content=_reference_png_bytes(),
        claimed_mime_type="image/png",
        original_filename="reference-product.png",
        role=ReferenceAssetRole.PRODUCT,
        instruction=(
            "Preserve visible product geometry, color relationships, illuminated feature, "
            "emblem placement, and light accent marks."
        ),
        principal_id=principal_id,
        tenant_id=tenant_id,
    )
    references.bind_request(
        request_id,
        (asset.asset_id,),
        principal_id=principal_id,
        tenant_id=tenant_id,
    )
    raw_blob = root / "reference-assets" / "blobs" / asset.sha256
    if not raw_blob.is_file():
        raise RuntimeError("bound reference raw blob is missing before execution")

    try:
        manifest = coordinator.resume(
            request_id,
            token=token,
            now=now + timedelta(seconds=1),
        )
    except Exception as exc:
        _write_provider_evidence(proof_root, poller)
        (proof_root / "failure.json").write_text(
            json.dumps(
                {
                    "schema": "ilaios.desktop.reference-provider-video-e2e.failure.v1",
                    "status": "FAIL",
                    "revision_sha": os.environ.get("GITHUB_SHA", "local"),
                    "reference_sha256": asset.sha256,
                    "error_type": exc.__class__.__name__,
                    "error": str(exc),
                },
                sort_keys=True,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        raise

    if manifest.get("accepted") is not True:
        raise RuntimeError(f"reference AcceptanceManifest did not pass: {manifest}")
    coordinator_state = coordinator.get(request_id)
    if coordinator_state.get("execution_status") != "ACCEPTED":
        raise RuntimeError(f"reference execution did not reach ACCEPTED: {coordinator_state}")

    bound = references.for_request(request_id)
    if len(bound) != 1 or bound[0].sha256 != asset.sha256:
        raise RuntimeError("immutable reference binding was not retained")
    if raw_blob.exists():
        raise RuntimeError("successful reference execution did not release raw image bytes")

    frozen = ReferenceBriefCache(root / "reference-briefs.sqlite3").get(request_id)
    if frozen is None or not frozen.text.strip():
        raise RuntimeError("real multimodal reference analysis did not freeze a visual brief")
    if frozen.reference_sha256s != (asset.sha256,):
        raise RuntimeError("frozen visual brief digest does not match the bound reference")
    if not frozen.analyzer_id.startswith("openrouter-reference-analysis:"):
        raise RuntimeError(f"unexpected reference analyzer: {frozen.analyzer_id}")
    brief_sha256 = hashlib.sha256(frozen.text.encode("utf-8")).hexdigest()

    delivery_id = manifest.get("delivery_id")
    if not isinstance(delivery_id, str) or not delivery_id:
        raise RuntimeError("reference AcceptanceManifest is missing delivery_id")
    delivery = video.get_delivery(delivery_id)
    rendered = Path(str(delivery["path"]))
    if not rendered.is_file() or rendered.stat().st_size <= 100_000:
        raise RuntimeError("reference-provider MP4 delivery is missing or unexpectedly small")
    artifact_digest = manifest.get("artifact_digest")
    if not isinstance(artifact_digest, str) or delivery.get("sha256") != artifact_digest:
        raise RuntimeError("reference delivery SHA does not match AcceptanceManifest")
    if hashlib.sha256(rendered.read_bytes()).hexdigest() != artifact_digest:
        raise RuntimeError("persisted reference-provider video does not match its manifest")

    probe = FfmpegMediaEngine(timeout_seconds=60).probe(rendered)
    video_stream = next(
        (stream for stream in probe.streams if stream.get("codec_type") == "video"),
        None,
    )
    audio_stream = next(
        (stream for stream in probe.streams if stream.get("codec_type") == "audio"),
        None,
    )
    if video_stream is None or audio_stream is None:
        raise RuntimeError("reference-provider output is missing required audio/video streams")
    if video_stream.get("codec_name") != "h264" or audio_stream.get("codec_name") != "aac":
        raise RuntimeError("reference-provider output codecs are outside the delivery contract")
    if int(str(video_stream.get("width"))) != 1920 or int(str(video_stream.get("height"))) != 1080:
        raise RuntimeError("reference-provider finished product is not 1920x1080")
    if not 7.0 <= float(probe.duration_seconds) <= 9.0:
        raise RuntimeError(f"reference-provider duration is outside tolerance: {probe.duration_seconds}")

    qa = manifest.get("qa")
    if not isinstance(qa, dict) or qa.get("passed") is not True:
        raise RuntimeError(f"reference-provider QA is not proven: {qa}")
    if qa.get("semantic_passed") is not True or qa.get("technical_passed") is not True:
        raise RuntimeError(f"reference-provider semantic/technical QA is incomplete: {qa}")
    if qa.get("provider_cost_zero") is not True:
        raise RuntimeError(f"reference free-route cost evidence is not proven: {qa}")
    if int(qa.get("generated_shot_count", 0)) != 2:
        raise RuntimeError(f"unexpected reference generated shot count: {qa}")

    terminal = {job_id: dict(value) for job_id, value in poller.terminal_evidence.items()}
    if len(terminal) != 2:
        raise RuntimeError(f"expected two provider terminal records, got {len(terminal)}")
    if any(float(value["cost"]) != 0.0 for value in terminal.values()):
        raise RuntimeError("reference provider terminal cost is not exactly zero")
    generation_ids = [
        str(value["generation_id"])
        for value in terminal.values()
        if str(value.get("generation_id", "")).strip()
        and str(value.get("generation_id")) != "unavailable"
    ]
    if len(generation_ids) != 2:
        raise RuntimeError("reference provider generation IDs are not fully evidenced")
    sources = sorted({str(value["source"]) for value in terminal.values()})
    _write_provider_evidence(proof_root, poller)

    copied_video = proof_root / "desktop-reference-provider-finished-product.mp4"
    shutil.copy2(rendered, copied_video)
    receipt = {
        "schema": "ilaios.desktop.reference-provider-video-e2e.v1",
        "status": "PASS",
        "revision_sha": os.environ.get("GITHUB_SHA", "local"),
        "request_id": request_id,
        "execution_status": coordinator_state["execution_status"],
        "provider_model": os.environ.get("ILAIOS_VIDEO_MODEL_ID", SEEDANCE_FREE_MODEL_ID),
        "provider_generation_id": generation_ids[0],
        "provider_generation_ids": generation_ids,
        "provider_cost_usd": 0.0,
        "provider_cost_zero": True,
        "provider_cost_evidence_source": ",".join(sources),
        "qa_model": os.environ.get("ILAIOS_VIDEO_QA_MODEL_ID", "openrouter/free"),
        "reference_asset_count": 1,
        "reference_asset_sha256": asset.sha256,
        "reference_role": asset.role.value,
        "reference_binding_retained": True,
        "reference_analyzer_id": frozen.analyzer_id,
        "reference_visual_brief_sha256": brief_sha256,
        "reference_conditioning_mode": "private-multimodal-brief",
        "provider_native_reference_url_used": False,
        "raw_reference_blob_released": True,
        "artifact_sha256": artifact_digest,
        "artifact_bytes": copied_video.stat().st_size,
        "duration_seconds": probe.duration_seconds,
        "width": int(str(video_stream.get("width"))),
        "height": int(str(video_stream.get("height"))),
        "video_codec": video_stream.get("codec_name"),
        "audio_codec": audio_stream.get("codec_name"),
        "semantic_score": qa.get("semantic_score"),
        "semantic_threshold": qa.get("semantic_threshold"),
        "generated_shot_count": qa.get("generated_shot_count"),
        "generation_mode": "provider-backed-reference-conditioned-video",
    }
    (proof_root / "receipt.json").write_text(
        json.dumps(receipt, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, sort_keys=True))
    print("ILAIOS_DESKTOP_REFERENCE_PROVIDER_VIDEO_E2E=PASS")


def _reference_png_bytes() -> bytes:
    width, height = 640, 360
    rows = bytearray()
    for y in range(height):
        rows.append(0)
        for x in range(width):
            color = (236, 233, 225)
            if 150 <= x < 490 and 70 <= y < 290:
                color = (38, 43, 49)
            if 302 <= x < 338 and 92 <= y < 268:
                color = (0, 194, 209)
            if (x - 424) ** 2 + (y - 128) ** 2 <= 30**2:
                color = (236, 115, 44)
            if 205 <= x < 270 and 220 <= y < 232:
                color = (242, 242, 238)
            if 205 <= x < 285 and 244 <= y < 256:
                color = (242, 242, 238)
            rows.extend(color)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", zlib.compress(bytes(rows), level=9))
        + _png_chunk(b"IEND", b"")
    )


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    body = kind + payload
    return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


def _write_provider_evidence(
    proof_root: Path,
    poller: OpenRouterVideoGenerationJobPoller,
) -> None:
    evidence = {job_id: dict(value) for job_id, value in poller.terminal_evidence.items()}
    if evidence:
        (proof_root / "provider-terminal-evidence.json").write_text(
            json.dumps(evidence, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    raise SystemExit(main())
