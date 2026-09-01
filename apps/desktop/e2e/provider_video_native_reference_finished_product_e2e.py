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
import urllib.error
import urllib.request
import zlib
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse, urlunparse

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.control_plane.api import ControlPlane, ControlPlaneConfig
from services.control_plane.workflows import WorkflowStore, WorkflowStoreConfig
from services.desktop_execution_coordinator import DesktopExecutionCoordinator
from services.evidence import EvidenceStore
from services.governance import GovernedRuntimeGateway
from services.integrations.desktop_video_composition import compose_desktop_video_runtime
from services.integrations.native_reference_receipt_runtime import (
    ReceiptBoundNativeReferenceManagedDesktopVideoRuntime,
)
from services.integrations.product_runtime import DurableVideoProductRuntime
from services.reference_asset_admission import ReferenceAssetAdmissionStore
from services.reference_assets import ReferenceAssetRole
from services.runtime import DurableGrantPolicy, DurableWorkerScheduler, GovernedRuntime
from services.source_media import SourceMediaStore
from src.video_automation.ffmpeg_media_engine import FfmpegMediaEngine

_MAX_CERTIFICATION_SPEND_USD = Decimal("1.00")


def main() -> int:
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    relay_upload_url = os.environ.get("ILAIOS_REFERENCE_RELAY_UPLOAD_URL", "").strip()
    relay_token = os.environ.get("ILAIOS_REFERENCE_RELAY_UPLOAD_TOKEN", "").strip()
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required for native-reference E2E")
    if not relay_upload_url.startswith("https://") or not relay_token:
        raise RuntimeError("native-reference E2E requires configured HTTPS relay credentials")
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise RuntimeError("native-reference E2E requires ffmpeg and ffprobe")
    max_total_cost_usd = _managed_budget()

    proof_root = Path(
        os.environ.get(
            "VIDEO_DESKTOP_NATIVE_REFERENCE_PROOF_DIR",
            "artifacts/video-desktop-native-reference-proof",
        )
    ).resolve()
    proof_root.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix="ilaios-native-reference-e2e-"))
    try:
        _run_acceptance(
            root=temporary,
            proof_root=proof_root,
            api_key=api_key,
            relay_upload_url=relay_upload_url,
            relay_token=relay_token,
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


def _run_acceptance(
    *,
    root: Path,
    proof_root: Path,
    api_key: str,
    relay_upload_url: str,
    relay_token: str,
    max_total_cost_usd: Decimal,
) -> None:
    token = "test"
    principal_id = "ci-native-reference-video-user"
    tenant_id = "ci-native-reference-video-tenant"
    request_id = "desktop-native-reference-video-real-e2e"
    database = root / "control-plane.sqlite3"
    product_database = root / "product-proof.sqlite3"
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
    source_media = SourceMediaStore(
        root / "source-media.sqlite3",
        root / "source-media" / "blobs",
    )

    def resolve_objective(job_id: str) -> str:
        job = control_plane.get_job(token, job_id)
        return control_plane.get_goal(token, job.goal_id).objective

    composition = compose_desktop_video_runtime(
        root=root / "video",
        grants=grants,
        governance=governance,
        evidence=evidence,
        objective_resolver=resolve_objective,
        api_key=api_key,
        reference_assets=references,
        source_media=source_media,
        product_identity_database=product_database,
    )
    video = composition.runtime
    if not isinstance(video, ReceiptBoundNativeReferenceManagedDesktopVideoRuntime):
        raise RuntimeError("Desktop did not select receipt-bound native reference runtime")
    if composition.provider_mode != "managed-bounded":
        raise RuntimeError("native reference production proof is not managed-bounded")
    if not composition.native_reference_relay_configured:
        raise RuntimeError("native reference relay was not selected by Desktop composition")

    product = DurableVideoProductRuntime(
        product_database,
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
        "Use the admitted product image and admitted logo as visual sources of truth. Preserve the "
        "matte dark product geometry, cyan illuminated vertical feature, orange emblem, and clean "
        "studio lighting. Preserve the admitted logo visibly and faithfully at the bottom-right. "
        "Show the same premium product in continuous realistic footage with controlled camera "
        "motion and clean audio. Do not render instruction text and do not publish anywhere."
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
        raise RuntimeError(f"native reference request was not admitted: {prepared}")

    product_asset = references.put(
        content=_product_png_bytes(),
        claimed_mime_type="image/png",
        original_filename="native-product.png",
        role=ReferenceAssetRole.PRODUCT,
        instruction="Preserve exact visible product geometry, colors, materials, and markings.",
        principal_id=principal_id,
        tenant_id=tenant_id,
    )
    logo_asset = references.put(
        content=_logo_png_bytes(),
        claimed_mime_type="image/png",
        original_filename="native-logo.png",
        role=ReferenceAssetRole.LOGO,
        instruction="Preserve exact logo pixels; asset-lock:bottom-right if deterministic repair is needed.",
        principal_id=principal_id,
        tenant_id=tenant_id,
    )
    references.bind_request(
        request_id,
        (product_asset.asset_id, logo_asset.asset_id),
        principal_id=principal_id,
        tenant_id=tenant_id,
    )
    raw_blobs = tuple(
        root / "reference-assets" / "blobs" / asset.sha256
        for asset in (product_asset, logo_asset)
    )
    if not all(path.is_file() for path in raw_blobs):
        raise RuntimeError("native reference raw blobs are missing before execution")

    try:
        manifest = coordinator.resume(
            request_id,
            token=token,
            now=now + timedelta(seconds=1),
        )
    except Exception as exc:
        _write_failure(proof_root, exc, max_total_cost_usd)
        raise
    if manifest.get("accepted") is not True:
        raise RuntimeError(f"native reference AcceptanceManifest did not pass: {manifest}")
    coordinator_state = coordinator.get(request_id)
    if coordinator_state.get("execution_status") != "ACCEPTED":
        raise RuntimeError("native reference execution did not reach ACCEPTED")
    if any(path.exists() for path in raw_blobs):
        raise RuntimeError("native reference local raw blobs were not released")

    qa = manifest.get("qa")
    if not isinstance(qa, dict) or qa.get("passed") is not True:
        raise RuntimeError("native reference canonical QA is not proven")
    _verify_native_qa(qa, product_asset.sha256, logo_asset.sha256)
    _verify_relay_fetch(relay_upload_url, relay_token, product_asset.sha256)
    _verify_relay_fetch(relay_upload_url, relay_token, logo_asset.sha256)

    delivery_id = manifest.get("delivery_id")
    if not isinstance(delivery_id, str) or not delivery_id:
        raise RuntimeError("native reference manifest is missing delivery_id")
    delivery = video.get_delivery(delivery_id)
    rendered = Path(str(delivery["path"]))
    if not rendered.is_file() or rendered.stat().st_size <= 100_000:
        raise RuntimeError("native reference MP4 is missing or unexpectedly small")
    artifact_digest = manifest.get("artifact_digest")
    if not isinstance(artifact_digest, str) or delivery.get("sha256") != artifact_digest:
        raise RuntimeError("native reference delivery SHA does not match manifest")
    if hashlib.sha256(rendered.read_bytes()).hexdigest() != artifact_digest:
        raise RuntimeError("native reference persisted video digest mismatch")

    probe = FfmpegMediaEngine(timeout_seconds=60).probe(rendered)
    video_stream = next(
        (stream for stream in probe.streams if stream.get("codec_type") == "video"), None
    )
    audio_stream = next(
        (stream for stream in probe.streams if stream.get("codec_type") == "audio"), None
    )
    if video_stream is None or audio_stream is None:
        raise RuntimeError("native reference output lacks required audio/video streams")
    if video_stream.get("codec_name") != "h264" or audio_stream.get("codec_name") != "aac":
        raise RuntimeError("native reference output codecs are outside delivery contract")
    if int(str(video_stream.get("width"))) != 1920 or int(str(video_stream.get("height"))) != 1080:
        raise RuntimeError("native reference finished product is not 1920x1080")
    if not 7.0 <= float(probe.duration_seconds) <= 9.0:
        raise RuntimeError("native reference duration is outside tolerance")

    copied_video = proof_root / "desktop-native-reference-finished-product.mp4"
    shutil.copy2(rendered, copied_video)
    receipt = {
        "schema": "ilaios.desktop.native-reference-provider-video-e2e.v1",
        "status": "PASS",
        "revision_sha": os.environ.get("GITHUB_SHA", "local"),
        "request_id": request_id,
        "execution_status": coordinator_state["execution_status"],
        "provider_model": os.environ.get("ILAIOS_VIDEO_MANAGED_MODEL_ID", ""),
        "provider_cost_mode": qa.get("provider_cost_mode"),
        "provider_cost_proven": qa.get("provider_cost_proven"),
        "provider_cost_microusd": qa.get("provider_cost_microusd"),
        "provider_cost_hard_cap_usd": str(max_total_cost_usd),
        "provider_native_reference_url_used": qa.get("provider_native_reference_url_used"),
        "native_reference_mode": qa.get("native_reference_mode"),
        "native_reference_count": qa.get("native_reference_count"),
        "native_reference_dispatch_count": qa.get("native_reference_dispatch_count"),
        "native_reference_sha256s": qa.get("native_reference_sha256s"),
        "native_reference_relay_released": qa.get("native_reference_relay_released"),
        "reference_consistency_passed": qa.get("reference_consistency_passed"),
        "reference_consistency_score": qa.get("reference_consistency_score"),
        "reference_consistency_threshold": qa.get("reference_consistency_threshold"),
        "reference_consistency_product_score": qa.get("reference_consistency_product_score"),
        "reference_consistency_logo_score": qa.get("reference_consistency_logo_score"),
        "reference_consistency_evidence_digest": qa.get("reference_consistency_evidence_digest"),
        "reference_consistency_provenance_hash": qa.get("reference_consistency_provenance_hash"),
        "logo_asset_lock_applied": qa.get("logo_asset_lock_applied"),
        "logo_asset_lock_source_sha256": qa.get("logo_asset_lock_source_sha256"),
        "logo_asset_lock_repaired_artifact_sha256": qa.get("logo_asset_lock_repaired_artifact_sha256"),
        "logo_asset_lock_evidence_digest": qa.get("logo_asset_lock_evidence_digest"),
        "logo_asset_lock_provenance_hash": qa.get("logo_asset_lock_provenance_hash"),
        "product_reference_sha256": product_asset.sha256,
        "logo_reference_sha256": logo_asset.sha256,
        "artifact_sha256": artifact_digest,
        "artifact_bytes": copied_video.stat().st_size,
        "duration_seconds": probe.duration_seconds,
        "width": 1920,
        "height": 1080,
        "video_codec": "h264",
        "audio_codec": "aac",
    }
    (proof_root / "receipt.json").write_text(
        json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, sort_keys=True))
    print("ILAIOS_DESKTOP_NATIVE_REFERENCE_PROVIDER_VIDEO_E2E=PASS")


def _verify_native_qa(qa: dict[str, object], product_sha: str, logo_sha: str) -> None:
    if qa.get("provider_cost_mode") != "managed-bounded" or qa.get("provider_cost_proven") is not True:
        raise RuntimeError("native reference provider cost evidence is incomplete")
    cost = qa.get("provider_cost_microusd")
    if isinstance(cost, bool) or not isinstance(cost, int) or not 0 <= cost <= 1_000_000:
        raise RuntimeError("native reference provider cost exceeds authorized cap")
    if qa.get("provider_native_reference_url_used") is not True:
        raise RuntimeError("native reference provider URL use is not proven")
    if qa.get("native_reference_mode") != "input-references":
        raise RuntimeError("native reference certification did not use input_references")
    if qa.get("native_reference_relay_released") is not True:
        raise RuntimeError("native reference relay release is not proven")
    refs = qa.get("native_reference_sha256s")
    if not isinstance(refs, (list, tuple)) or tuple(refs) != (product_sha, logo_sha):
        raise RuntimeError("native reference SHA binding is incomplete")
    if qa.get("reference_consistency_passed") is not True:
        raise RuntimeError("native reference final consistency QA did not pass")
    threshold = qa.get("reference_consistency_threshold")
    product_score = qa.get("reference_consistency_product_score")
    logo_score = qa.get("reference_consistency_logo_score")
    if not isinstance(threshold, (int, float)) or not isinstance(product_score, (int, float)):
        raise RuntimeError("native reference product consistency evidence is incomplete")
    if float(product_score) < float(threshold):
        raise RuntimeError("native reference product consistency is below threshold")
    lock_applied = qa.get("logo_asset_lock_applied")
    if lock_applied is True:
        if qa.get("logo_asset_lock_source_sha256") != logo_sha:
            raise RuntimeError("logo asset-lock source digest does not match admitted logo")
        repaired = qa.get("logo_asset_lock_repaired_artifact_sha256")
        if not _is_sha256(repaired):
            raise RuntimeError("logo asset-lock repaired artifact digest is missing")
        for key in ("logo_asset_lock_evidence_digest", "logo_asset_lock_provenance_hash"):
            if not _is_sha256(qa.get(key)):
                raise RuntimeError("logo asset-lock provenance evidence is incomplete")
    else:
        if not isinstance(logo_score, (int, float)) or float(logo_score) < float(threshold):
            raise RuntimeError("native logo consistency neither passed directly nor via asset-lock")


def _verify_relay_fetch(upload_url: str, token: str, sha256_hex: str) -> None:
    parsed = urlparse(upload_url)
    url = urlunparse((parsed.scheme, parsed.netloc, f"/v1/reference-relay-access/{sha256_hex}", "", "", ""))
    request = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as error:
        raise RuntimeError("native reference relay fetch evidence is unavailable") from error
    if response.status != 200 or payload.get("sha256") != sha256_hex:
        raise RuntimeError("native reference relay fetch evidence is invalid")
    count = payload.get("fetch_count")
    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        raise RuntimeError("provider did not fetch one admitted native reference")


def _write_failure(proof_root: Path, error: Exception, cap: Decimal) -> None:
    document = {
        "schema": "ilaios.desktop.native-reference-provider-video-e2e.failure.v1",
        "status": "FAIL",
        "revision_sha": os.environ.get("GITHUB_SHA", "local"),
        "provider_cost_mode": "managed-bounded",
        "provider_cost_hard_cap_usd": str(cap),
        "error_type": error.__class__.__name__,
        "error": str(error),
    }
    (proof_root / "failure.json").write_text(
        json.dumps(document, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )


def _managed_budget() -> Decimal:
    raw = os.environ.get("ILAIOS_VIDEO_MANAGED_MAX_TOTAL_USD", "").strip()
    if not raw:
        raise RuntimeError("ILAIOS_VIDEO_MANAGED_MAX_TOTAL_USD is required")
    try:
        value = Decimal(raw)
    except InvalidOperation as error:
        raise RuntimeError("native reference managed budget is not a decimal") from error
    if not value.is_finite() or value <= 0 or value > _MAX_CERTIFICATION_SPEND_USD:
        raise RuntimeError("native reference managed budget must be > 0 and <= 1.00 USD")
    return value


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _product_png_bytes() -> bytes:
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
            rows.extend(color)
    return _rgb_png(width, height, bytes(rows))


def _logo_png_bytes() -> bytes:
    width, height = 160, 64
    rows = bytearray()
    for y in range(height):
        rows.append(0)
        for x in range(width):
            color = (17, 24, 39)
            if 16 <= x < 38 and 12 <= y < 52:
                color = (0, 194, 209)
            if 46 <= x < 144 and (18 <= y < 24 or 40 <= y < 46):
                color = (255, 255, 255)
            rows.extend(color)
    return _rgb_png(width, height, bytes(rows))


def _rgb_png(width: int, height: int, rows: bytes) -> bytes:
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", zlib.compress(rows, level=9))
        + _png_chunk(b"IEND", b"")
    )


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    body = kind + payload
    return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


if __name__ == "__main__":
    raise SystemExit(main())
