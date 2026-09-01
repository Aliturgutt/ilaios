from __future__ import annotations

import gc
import hashlib
import json
import shutil
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from services.control_plane.api import ControlPlane, ControlPlaneConfig
from services.control_plane.workflows import WorkflowStore, WorkflowStoreConfig
from services.evidence import EvidenceStore
from services.execution_coordinator import ExecutionCoordinator
from services.governance import GovernedRuntimeGateway
from services.integrations.desktop_video_runtime import DesktopPromptVideoRuntime
from services.integrations.product_runtime import DurableVideoProductRuntime
from services.runtime import DurableGrantPolicy, DurableWorkerScheduler, GovernedRuntime
from src.video_automation.ffmpeg_media_engine import FfmpegMediaEngine


def main() -> int:
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise RuntimeError("Windows runner must provide ffmpeg and ffprobe")
    if shutil.which("powershell.exe") is None:
        raise RuntimeError("Windows SAPI voice path requires powershell.exe")

    repo_root = Path(__file__).resolve().parents[3]
    logo = repo_root / "brand" / "assets" / "03-ilaios-symbol-dark.jpg"
    if not logo.is_file():
        raise RuntimeError("official ILAIOS brand logo is unavailable")
    logo_hash_before = hashlib.sha256(logo.read_bytes()).hexdigest()

    temporary = Path(tempfile.mkdtemp(prefix="ilaios-video-e2e-"))
    try:
        _run_finished_product_acceptance(
            root=temporary,
            logo=logo,
            logo_hash_before=logo_hash_before,
        )
    finally:
        # All runtime objects are scoped inside _run_finished_product_acceptance,
        # so by this point only sqlite finalizers can still be releasing Windows
        # file handles. Product assertions remain strict; this only retries teardown.
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
    *, root: Path, logo: Path, logo_hash_before: str
) -> None:
    token = "desktop-video-e2e-token"
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

    video = DesktopPromptVideoRuntime(
        root / "video",
        grants,
        governance,
        evidence,
        objective_resolver=resolve_objective,
        brand_logo=logo,
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
    coordinator = ExecutionCoordinator(
        root / "execution-coordinator.sqlite3",
        control_plane,
        governance,
        grants,
        product,
    )

    request_id = "desktop-video-real-render-e2e"
    objective = (
        "Create a premium 20 second ILAIOS brand video. "
        "Show one prompt, governed autonomous execution, and a verified finished product. "
        "Use the official ILAIOS logo, English voiceover, subtitles, background music, "
        "and deliver a 1080p 16:9 MP4."
    )
    now = datetime.now(timezone.utc)
    prepared = coordinator.prepare(
        request_id,
        objective,
        token=token,
        principal_id="ci-desktop-user",
        tenant_id="ci-desktop-tenant",
        now=now,
    )
    if prepared.get("execution_status") != "ADMITTED":
        raise RuntimeError(f"video request was not admitted: {prepared}")
    if prepared.get("adapter_id") != "video.product-runtime.v1":
        raise RuntimeError(f"wrong video adapter: {prepared}")

    manifest = coordinator.resume(
        request_id,
        token=token,
        now=now + timedelta(seconds=1),
    )
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
        raise RuntimeError("verified MP4 delivery is missing or unexpectedly small")
    if delivery.get("sha256") != manifest.get("artifact_digest"):
        raise RuntimeError("delivery SHA does not match AcceptanceManifest artifact digest")

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
        raise RuntimeError("finished product is missing required audio/video streams")
    if video_stream.get("codec_name") != "h264":
        raise RuntimeError(f"unexpected video codec: {video_stream.get('codec_name')}")
    if audio_stream.get("codec_name") != "aac":
        raise RuntimeError(f"unexpected audio codec: {audio_stream.get('codec_name')}")
    if int(str(video_stream.get("width"))) != 1920 or int(str(video_stream.get("height"))) != 1080:
        raise RuntimeError("finished product is not 1920x1080")
    if not 19.0 <= float(probe.duration_seconds) <= 21.0:
        raise RuntimeError(
            f"finished product duration is outside 20s tolerance: {probe.duration_seconds}"
        )

    run_root = root / "video" / request_id
    required_stage_evidence = (
        "research.json",
        "script.json",
        "storyboard.json",
        "shot-plan.json",
        "asset-plan.json",
        "voice.wav",
        "music.wav",
        "captions.srt",
        "timeline.json",
        "final.mp4",
    )
    missing = [name for name in required_stage_evidence if not (run_root / name).is_file()]
    if missing:
        raise RuntimeError(f"finished-product stage evidence is missing: {missing}")

    logo_hash_after = hashlib.sha256(logo.read_bytes()).hexdigest()
    if logo_hash_after != logo_hash_before:
        raise RuntimeError("official ILAIOS logo was mutated during render")

    qa = manifest.get("qa")
    if not isinstance(qa, dict) or qa.get("passed") is not True:
        raise RuntimeError(f"visual/audio QA is not proven: {qa}")

    print(
        json.dumps(
            {
                "acceptance_manifest": "PASS",
                "artifact_sha256": delivery["sha256"],
                "audio_codec": audio_stream.get("codec_name"),
                "duration_seconds": probe.duration_seconds,
                "execution_status": coordinator_state["execution_status"],
                "height": video_stream.get("height"),
                "logo_immutable": True,
                "stage_evidence_count": len(required_stage_evidence),
                "video_codec": video_stream.get("codec_name"),
                "width": video_stream.get("width"),
            },
            sort_keys=True,
        )
    )
    print("ILAIOS_DESKTOP_VIDEO_FINISHED_PRODUCT_E2E=PASS")


if __name__ == "__main__":
    raise SystemExit(main())
