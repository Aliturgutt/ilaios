from __future__ import annotations

# ruff: noqa: E402

import gc
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.control_plane.api import ControlPlane, ControlPlaneConfig
from services.control_plane.workflows import WorkflowStore, WorkflowStoreConfig
from services.desktop_execution_coordinator import DesktopExecutionCoordinator
from services.evidence import EvidenceStore
from services.governance import GovernedRuntimeGateway
from services.integrations.managed_provider_video_runtime import (
    ManagedProviderBackedDesktopVideoRuntime,
)
from services.integrations.product_runtime import DurableVideoProductRuntime
from services.runtime import DurableGrantPolicy, DurableWorkerScheduler, GovernedRuntime
from src.video_automation.ffmpeg_media_engine import FfmpegMediaEngine

_MAX_CERTIFICATION_SPEND_USD = Decimal("1.00")


def main() -> int:
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required for managed Desktop E2E")
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise RuntimeError("managed Desktop E2E requires ffmpeg and ffprobe")
    max_total_cost_usd = _managed_e2e_budget()

    proof_root = Path(
        os.environ.get(
            "VIDEO_DESKTOP_MANAGED_PROVIDER_PROOF_DIR",
            "artifacts/video-desktop-managed-provider-proof",
        )
    ).resolve()
    proof_root.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix="ilaios-managed-provider-video-e2e-"))
    try:
        _run_finished_product_acceptance(
            root=temporary,
            proof_root=proof_root,
            api_key=api_key,
            max_total_cost_usd=max_total_cost_usd,
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
    *,
    root: Path,
    proof_root: Path,
    api_key: str,
    max_total_cost_usd: Decimal,
) -> None:
    token = "ci-token"
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

    video = ManagedProviderBackedDesktopVideoRuntime(
        root / "video",
        grants,
        governance,
        evidence,
        objective_resolver=resolve_objective,
        api_key=api_key,
        max_total_cost_usd=max_total_cost_usd,
        model_id=os.environ.get(
            "ILAIOS_VIDEO_MANAGED_MODEL_ID",
            "bytedance/seedance-2.0-fast",
        ).strip(),
        qa_model_id=os.environ.get(
            "ILAIOS_VIDEO_QA_MODEL_ID",
            "openrouter/free",
        ).strip(),
        resolution=os.environ.get(
            "ILAIOS_VIDEO_E2E_RESOLUTION",
            "480p",
        ).strip(),
        poll_interval_seconds=5.0,
        max_poll_rounds=144,
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

    request_id = "desktop-managed-provider-video-real-e2e"
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
        principal_id="ci-managed-provider-video-user",
        tenant_id="ci-managed-provider-video-tenant",
        now=now,
    )
    if prepared.get("execution_status") != "ADMITTED":
        raise RuntimeError(f"managed provider video request was not admitted: {prepared}")
    if prepared.get("adapter_id") != "video.product-runtime.v1":
        raise RuntimeError(f"wrong video adapter: {prepared}")

    try:
        manifest = coordinator.resume(
            request_id,
            token=token,
            now=now + timedelta(seconds=1),
        )
    except Exception as exc:
        (proof_root / "failure.json").write_text(
            json.dumps(
                {
                    "schema": "ilaios.desktop.managed-provider-video-e2e.failure.v1",
                    "status": "FAIL",
                    "revision_sha": os.environ.get("GITHUB_SHA", "local"),
                    "max_total_cost_usd": str(max_total_cost_usd),
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
        raise RuntimeError("verified managed-provider MP4 is missing or unexpectedly small")
    artifact_digest = manifest.get("artifact_digest")
    if not isinstance(artifact_digest, str) or delivery.get("sha256") != artifact_digest:
        raise RuntimeError("delivery SHA does not match AcceptanceManifest artifact digest")
    if hashlib.sha256(rendered.read_bytes()).hexdigest() != artifact_digest:
        raise RuntimeError("persisted managed-provider video does not match manifest digest")

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
        raise RuntimeError("managed-provider finished product is missing audio/video streams")
    if video_stream.get("codec_name") != "h264":
        raise RuntimeError(f"unexpected video codec: {video_stream.get('codec_name')}")
    if audio_stream.get("codec_name") != "aac":
        raise RuntimeError(f"unexpected audio codec: {audio_stream.get('codec_name')}")
    if int(str(video_stream.get("width"))) != 1920 or int(str(video_stream.get("height"))) != 1080:
        raise RuntimeError("managed-provider finished product is not 1920x1080")
    if not 7.0 <= float(probe.duration_seconds) <= 9.0:
        raise RuntimeError(
            "managed-provider finished product duration is outside 8s tolerance: "
            f"{probe.duration_seconds}"
        )

    qa = manifest.get("qa")
    if not isinstance(qa, dict) or qa.get("passed") is not True:
        raise RuntimeError(f"managed-provider finished product QA is not proven: {qa}")
    if qa.get("semantic_passed") is not True or qa.get("technical_passed") is not True:
        raise RuntimeError(f"managed-provider semantic/technical acceptance failed: {qa}")
    if qa.get("provider_cost_mode") != "managed-bounded":
        raise RuntimeError(f"managed provider cost mode is not proven: {qa}")
    if qa.get("provider_cost_proven") is not True:
        raise RuntimeError(f"managed provider terminal cost is not proven: {qa}")
    provider_cost_microusd = qa.get("provider_cost_microusd")
    if isinstance(provider_cost_microusd, bool) or not isinstance(
        provider_cost_microusd, int
    ):
        raise RuntimeError("managed provider cost must be integer microUSD")
    max_total_microusd = _usd_to_microusd(max_total_cost_usd)
    if provider_cost_microusd < 0 or provider_cost_microusd > max_total_microusd:
        raise RuntimeError("managed provider actual cost exceeded the authorized $1 proof cap")
    provider_ceiling_microusd = qa.get("provider_cost_ceiling_microusd")
    if provider_ceiling_microusd != max_total_microusd:
        raise RuntimeError("managed provider evidence is not bound to the exact proof cap")
    if int(qa.get("generated_shot_count", 0)) != 2:
        raise RuntimeError(f"unexpected generated shot count: {qa}")

    copied_video = proof_root / "desktop-managed-provider-finished-product.mp4"
    shutil.copy2(rendered, copied_video)
    receipt = {
        "schema": "ilaios.desktop.managed-provider-video-e2e.v1",
        "status": "PASS",
        "revision_sha": os.environ.get("GITHUB_SHA", "local"),
        "provider_model": os.environ.get(
            "ILAIOS_VIDEO_MANAGED_MODEL_ID",
            "bytedance/seedance-2.0-fast",
        ),
        "provider_cost_mode": "managed-bounded",
        "provider_cost_proven": True,
        "provider_cost_zero": qa.get("provider_cost_zero"),
        "provider_cost_microusd": provider_cost_microusd,
        "provider_cost_usd": str(
            Decimal(provider_cost_microusd) / Decimal(1_000_000)
        ),
        "provider_cost_hard_cap_usd": str(max_total_cost_usd),
        "provider_cost_hard_cap_microusd": max_total_microusd,
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
    print("ILAIOS_DESKTOP_MANAGED_PROVIDER_VIDEO_FINISHED_PRODUCT_E2E=PASS")


def _managed_e2e_budget() -> Decimal:
    raw = os.environ.get("ILAIOS_VIDEO_MANAGED_E2E_MAX_TOTAL_USD", "").strip()
    if not raw:
        raise RuntimeError("ILAIOS_VIDEO_MANAGED_E2E_MAX_TOTAL_USD is required")
    try:
        value = Decimal(raw)
    except InvalidOperation as exc:
        raise RuntimeError("managed Desktop E2E budget is not a decimal") from exc
    if not value.is_finite() or value <= 0 or value > _MAX_CERTIFICATION_SPEND_USD:
        raise RuntimeError("managed Desktop E2E budget must be > 0 and <= 1.00 USD")
    return value


def _usd_to_microusd(value: Decimal) -> int:
    scaled = value * Decimal(1_000_000)
    if scaled != scaled.to_integral_value():
        raise RuntimeError("managed Desktop E2E budget must have microUSD precision")
    return int(scaled)


if __name__ == "__main__":
    raise SystemExit(main())
