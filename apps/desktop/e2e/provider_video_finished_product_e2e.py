from __future__ import annotations

import gc
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
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
from services.integrations.provider_video_runtime import ProviderBackedDesktopVideoRuntime
from services.runtime import DurableGrantPolicy, DurableWorkerScheduler, GovernedRuntime
from src.video_automation.ffmpeg_media_engine import FfmpegMediaEngine
from src.video_automation.openrouter_video_provider import (
    SEEDANCE_FREE_MODEL_ID,
    OpenRouterVideoGenerationJobPoller,
)


def main() -> int:
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required for real provider-backed E2E")
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise RuntimeError("provider-backed E2E requires ffmpeg and ffprobe")

    proof_root = Path(
        os.environ.get(
            "VIDEO_DESKTOP_PROVIDER_PROOF_DIR",
            "artifacts/video-desktop-provider-proof",
        )
    ).resolve()
    proof_root.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix="ilaios-provider-video-e2e-"))
    try:
        _run_finished_product_acceptance(
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


def _run_finished_product_acceptance(
    *, root: Path, proof_root: Path, api_key: str
) -> None:
    token = "desktop-provider-video-e2e-token"
    database = root / "control-plane.sqlite3"
    control_plane = ControlPlane(ControlPlaneConfig(database, token))
    workflows = WorkflowStore(WorkflowStoreConfig(database))
    governed_runtime = GovernedRuntime(database)
    scheduler = DurableWorkerScheduler(
        database,
        lease_duration=timedelta(seconds=30),
    )
    grants = DurableGrantPolicy(database)
    evidence = EvidenceStore(root / "evidence")
    governance = GovernedRuntimeGateway(
        root / "governance.sqlite3",
        governed_runtime,
        hard_cap_minor=100,
    )

    def resolve_objective(job_id: str) -> str:
        job = control_plane.get_job(token, job_id)
        goal = control_plane.get_goal(token, job.goal_id)
        return goal.objective

    poller = OpenRouterVideoGenerationJobPoller(
        api_key,
        provider_id=ProviderBackedDesktopVideoRuntime.PROVIDER_ID,
    )
    video = ProviderBackedDesktopVideoRuntime(
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

    request_id = "desktop-provider-video-real-e2e"
    objective = (
        "Create a finished cinematic video exactly 8 seconds long. "
        "Show a futuristic coastal city at night during light rain. "
        "The first shot is a wide aerial view with wet streets reflecting restrained blue "
        "and amber city lights. The second shot moves to street level in the same city as "
        "one small spherical autonomous drone with a cyan optical light rises toward the "
        "skyline. Preserve the same world, weather, lighting, and drone design across the "
        "two shots. Use realistic motion, rain, reflections, atmospheric depth, and cinematic "
        "camera movement. The result must be continuous visual footage with audio, not title "
        "cards, presentation slides, static text panels, or generic motion graphics. "
        "Do not publish anywhere."
    )
    now = datetime.now(timezone.utc)
    prepared = coordinator.prepare(
        request_id,
        objective,
        token=token,
        principal_id="ci-provider-video-user",
        tenant_id="ci-provider-video-tenant",
        now=now,
    )
    if prepared.get("execution_status") != "ADMITTED":
        raise RuntimeError(f"provider video request was not admitted: {prepared}")
    if prepared.get("adapter_id") != "video.product-runtime.v1":
        raise RuntimeError(f"wrong video adapter: {prepared}")

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
                    "schema": "ilaios.desktop.provider-video-e2e.failure.v1",
                    "status": "FAIL",
                    "revision_sha": os.environ.get("GITHUB_SHA", "local"),
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
        raise RuntimeError(f"AcceptanceManifest did not pass: {manifest}")

    coordinator_state = coordinator.get(request_id)
    if coordinator_state.get("execution_status") != "ACCEPTED":
        raise RuntimeError(f"coordinator did not reach ACCEPTED: {coordinator_state}")

    delivery_id = manifest.get("delivery_id")
    if not isinstance(delivery_id, str) or not delivery_id:
        raise RuntimeError("AcceptanceManifest is missing delivery_id")
    delivery = video.get_delivery(delivery_id)
    rendered = Path(str(delivery["path"]))
    if not rendered.is_file() or rendered.stat().st_size <= 100_000:
        raise RuntimeError("verified provider MP4 delivery is missing or unexpectedly small")
    artifact_digest = manifest.get("artifact_digest")
    if not isinstance(artifact_digest, str) or delivery.get("sha256") != artifact_digest:
        raise RuntimeError("delivery SHA does not match AcceptanceManifest artifact digest")
    if hashlib.sha256(rendered.read_bytes()).hexdigest() != artifact_digest:
        raise RuntimeError("persisted provider video content does not match manifest digest")

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
        raise RuntimeError("provider finished product is missing required audio/video streams")
    if video_stream.get("codec_name") != "h264":
        raise RuntimeError(f"unexpected video codec: {video_stream.get('codec_name')}")
    if audio_stream.get("codec_name") != "aac":
        raise RuntimeError(f"unexpected audio codec: {audio_stream.get('codec_name')}")
    if int(str(video_stream.get("width"))) != 1920 or int(str(video_stream.get("height"))) != 1080:
        raise RuntimeError("provider finished product is not 1920x1080")
    if not 7.0 <= float(probe.duration_seconds) <= 9.0:
        raise RuntimeError(
            f"provider finished product duration is outside 8s tolerance: {probe.duration_seconds}"
        )

    qa = manifest.get("qa")
    if not isinstance(qa, dict) or qa.get("passed") is not True:
        raise RuntimeError(f"provider finished product QA is not proven: {qa}")
    if qa.get("semantic_passed") is not True:
        raise RuntimeError(f"semantic acceptance is not proven: {qa}")
    if qa.get("technical_passed") is not True:
        raise RuntimeError(f"technical acceptance is not proven: {qa}")
    if qa.get("provider_cost_zero") is not True:
        raise RuntimeError(f"zero-cost provider evidence is not proven: {qa}")
    if int(qa.get("generated_shot_count", 0)) != 2:
        raise RuntimeError(f"unexpected generated shot count: {qa}")

    terminal_evidence = {
        job_id: dict(evidence)
        for job_id, evidence in poller.terminal_evidence.items()
    }
    if len(terminal_evidence) != 2:
        raise RuntimeError(
            f"expected terminal zero-cost evidence for 2 provider jobs, got {len(terminal_evidence)}"
        )
    costs = [float(evidence["cost"]) for evidence in terminal_evidence.values()]
    if any(cost != 0.0 for cost in costs):
        raise RuntimeError(f"provider cost evidence is not exactly zero: {costs}")
    generation_ids = [
        str(evidence["generation_id"])
        for evidence in terminal_evidence.values()
        if str(evidence.get("generation_id", "")).strip()
        and str(evidence.get("generation_id")) != "unavailable"
    ]
    if len(generation_ids) != 2:
        raise RuntimeError("provider generation IDs are not fully evidenced")
    sources = sorted({str(evidence["source"]) for evidence in terminal_evidence.values()})
    _write_provider_evidence(proof_root, poller)

    copied_video = proof_root / "desktop-provider-finished-product.mp4"
    shutil.copy2(rendered, copied_video)
    receipt = {
        "schema": "ilaios.desktop.provider-video-e2e.v2",
        "status": "PASS",
        "revision_sha": os.environ.get("GITHUB_SHA", "local"),
        "provider_model": os.environ.get("ILAIOS_VIDEO_MODEL_ID", SEEDANCE_FREE_MODEL_ID),
        "provider_generation_id": generation_ids[0],
        "provider_generation_ids": generation_ids,
        "provider_cost_usd": 0.0,
        "provider_cost_zero": True,
        "provider_cost_evidence_source": ",".join(sources),
        "qa_model": os.environ.get("ILAIOS_VIDEO_QA_MODEL_ID", "openrouter/free"),
        "request_id": request_id,
        "execution_status": coordinator_state["execution_status"],
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
        "generation_mode": "provider-backed-cinematic-video",
    }
    (proof_root / "receipt.json").write_text(
        json.dumps(receipt, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, sort_keys=True))
    print("ILAIOS_DESKTOP_PROVIDER_VIDEO_FINISHED_PRODUCT_E2E=PASS")


def _write_provider_evidence(
    proof_root: Path,
    poller: OpenRouterVideoGenerationJobPoller,
) -> None:
    evidence = {
        job_id: dict(value)
        for job_id, value in poller.terminal_evidence.items()
    }
    if not evidence:
        return
    (proof_root / "provider-terminal-evidence.json").write_text(
        json.dumps(evidence, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
