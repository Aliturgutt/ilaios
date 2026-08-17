"""Zero-cost real-provider certification for ILAIOS Video Factory.

This harness reuses the canonical free-only OpenRouter adapter. It never submits
a model that lacks the explicit ``:free`` suffix, never invokes managed-credit
or paid-provider fallback paths, and requires provider-reported cost to be
exactly zero before issuing PASS.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import NoReturn

from .generation_job_polling import ProviderJobStatus
from .models import ProviderRequest
from .openrouter_video_provider import (
    SEEDANCE_FREE_MODEL_ID,
    OpenRouterGeneratedAssetRetriever,
    OpenRouterTransport,
    OpenRouterVideoGenerationJobPoller,
    OpenRouterVideoGenerationProvider,
    OpenRouterVideoProviderError,
    UrllibOpenRouterTransport,
)

DEFAULT_DURATION_SECONDS = 4
DEFAULT_RESOLUTION = "480p"
DEFAULT_ASPECT_RATIO = "16:9"
DEFAULT_POLL_TIMEOUT_SECONDS = 12 * 60
DEFAULT_POLL_INTERVAL_SECONDS = 5
FREE_PROVIDER_NAME = "openrouter-video-free"
FREE_MODEL_CANDIDATES = (
    SEEDANCE_FREE_MODEL_ID,
    "bytedance/seedance-2.0:free",
    "bytedance/seedance-1-5-pro:free",
)


class FreeProviderCertificationError(ValueError):
    """Raised when zero-cost production proof cannot be completed truthfully."""


def _text(name: str, value: str) -> None:
    if not value or value != value.strip():
        raise FreeProviderCertificationError(
            f"{name} must be normalized non-blank text"
        )


def free_model_candidates(raw: str | None) -> tuple[str, ...]:
    """Normalize an explicit free-only candidate list and reject paid IDs."""

    candidates: tuple[str, ...]
    if raw is None or not raw.strip():
        candidates = FREE_MODEL_CANDIDATES
    else:
        candidates = tuple(item.strip() for item in raw.split(",") if item.strip())
    if not candidates:
        raise FreeProviderCertificationError("at least one free model is required")
    for model_id in candidates:
        _text("model_id", model_id)
        if not model_id.endswith(":free"):
            raise FreeProviderCertificationError(
                "free certification forbids paid or unpriced model IDs"
            )
    return candidates


def build_free_certification_request(
    *,
    model_id: str,
    run_id: str,
    run_attempt: str,
    candidate_index: int,
) -> ProviderRequest:
    """Build one unique request bound to an explicitly-free model ID."""

    _text("model_id", model_id)
    if not model_id.endswith(":free"):
        raise FreeProviderCertificationError(
            "free certification forbids paid or unpriced model IDs"
        )
    _text("run_id", run_id)
    _text("run_attempt", run_attempt)
    request_id = f"video-free-provider-cert-{run_id}-{run_attempt}-{candidate_index}"
    item = {
        "sequence_number": 1,
        "request_id": request_id,
        "idempotency_key": hashlib.sha256(request_id.encode("utf-8")).hexdigest(),
        "shot_id": "free-provider-production-proof-shot-001",
        "prompt_text": (
            "An original cinematic abstract technology scene for ILAIOS "
            "production validation: matte graphite geometric forms assemble "
            "under restrained cyan accent light, subtle depth, slow controlled "
            "dolly motion, studio lighting, no text, no logos, no people, no "
            "copyrighted characters."
        ),
        "duration_seconds": DEFAULT_DURATION_SECONDS,
        "aspect_ratio": DEFAULT_ASPECT_RATIO,
        "frames_per_second": 24,
        "output_count": 1,
        "seed": None,
        "resolution": DEFAULT_RESOLUTION,
    }
    return ProviderRequest(
        request_id=request_id,
        job_id=f"{request_id}-job",
        provider_name=FREE_PROVIDER_NAME,
        operation="video.generate",
        payload={
            "model_id": model_id,
            "request_count": 1,
            "items_json": json.dumps(
                [item],
                sort_keys=True,
                separators=(",", ":"),
            ),
        },
    )


def provider_reported_cost(metadata: dict[str, str]) -> float | None:
    """Extract exact provider cost evidence from canonical polling metadata."""

    raw_usage = metadata.get("usage_json")
    if raw_usage is None:
        return None
    try:
        usage = json.loads(raw_usage)
    except json.JSONDecodeError as exc:
        raise FreeProviderCertificationError(
            "provider usage evidence is invalid JSON"
        ) from exc
    if not isinstance(usage, dict):
        raise FreeProviderCertificationError(
            "provider usage evidence must be an object"
        )
    raw_cost = usage.get("cost")
    if raw_cost is None:
        return None
    if isinstance(raw_cost, bool) or not isinstance(raw_cost, (int, float)):
        raise FreeProviderCertificationError(
            "provider-reported cost must be numeric"
        )
    cost = float(raw_cost)
    if cost < 0:
        raise FreeProviderCertificationError(
            "provider-reported cost must be non-negative"
        )
    return cost


def mp4_signature_ok(body: bytes) -> bool:
    """Require the ISO-BMFF ftyp signature near the start of the artifact."""

    return len(body) >= 12 and b"ftyp" in body[:32]


def run_free_certification(
    *,
    api_key: str,
    proof_dir: Path,
    revision_sha: str,
    run_id: str,
    run_attempt: str,
    candidate_models: tuple[str, ...] = FREE_MODEL_CANDIDATES,
    transport: OpenRouterTransport | None = None,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    poll_timeout_seconds: int = DEFAULT_POLL_TIMEOUT_SECONDS,
    poll_interval_seconds: int = DEFAULT_POLL_INTERVAL_SECONDS,
) -> dict[str, object]:
    """Run one real zero-cost provider proof with no paid fallback."""

    proof_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = proof_dir / "free-provider-receipt.json"
    video_path = proof_dir / "free-provider-proof.mp4"

    receipt: dict[str, object] = {
        "schema": "ilaios.video.free-provider-proof.v1",
        "status": "STARTED",
        "revision_sha": revision_sha,
        "workflow_run_id": run_id,
        "workflow_run_attempt": run_attempt,
        "provider": FREE_PROVIDER_NAME,
        "free_only": True,
        "paid_fallback_allowed": False,
        "credential_reference": (
            "github-environment-secret://Production/OPENROUTER_API_KEY"
        ),
        "candidate_models": list(candidate_models),
        "request_shape": {
            "duration_seconds": DEFAULT_DURATION_SECONDS,
            "resolution": DEFAULT_RESOLUTION,
            "aspect_ratio": DEFAULT_ASPECT_RATIO,
            "generate_audio": False,
        },
        "started_at": _utc_now(),
    }
    _persist(receipt_path, receipt)

    if not api_key or not api_key.strip():
        _fail(
            receipt_path,
            receipt,
            "BLOCKED_MISSING_SECRET",
            "OPENROUTER_API_KEY is unavailable; no provider request was submitted.",
        )

    candidates = free_model_candidates(",".join(candidate_models))
    active_transport = transport or UrllibOpenRouterTransport()
    provider = OpenRouterVideoGenerationProvider(
        api_key,
        transport=active_transport,
        default_resolution=DEFAULT_RESOLUTION,
        generate_audio=False,
    )

    attempts: list[dict[str, object]] = []
    selected_model: str | None = None
    provider_job_id: str | None = None

    for index, model_id in enumerate(candidates, start=1):
        request = build_free_certification_request(
            model_id=model_id,
            run_id=run_id,
            run_attempt=run_attempt,
            candidate_index=index,
        )
        result = provider.execute(request)
        attempt = {
            "model_id": model_id,
            "request_id": request.request_id,
            "success": result.success,
            "external_id": result.external_id,
            "error_code": result.error_code,
            "error_message": result.error_message,
            "metadata": dict(result.metadata),
        }
        attempts.append(attempt)
        receipt["submission_attempts"] = attempts
        _persist(receipt_path, receipt)
        if result.success and result.external_id is not None:
            selected_model = model_id
            provider_job_id = result.external_id
            receipt["selected_model"] = selected_model
            receipt["request_id"] = request.request_id
            receipt["external_job_id"] = provider_job_id
            receipt["submitted_at"] = _utc_now()
            _persist(receipt_path, receipt)
            break

    if selected_model is None or provider_job_id is None:
        _fail(
            receipt_path,
            receipt,
            "BLOCKED_FREE_PROVIDER_UNAVAILABLE",
            "all explicitly-free video model candidates were unavailable; paid fallback was not attempted",
        )

    poller = OpenRouterVideoGenerationJobPoller(
        api_key,
        provider_id=FREE_PROVIDER_NAME,
        transport=active_transport,
    )
    deadline = monotonic() + poll_timeout_seconds
    poll_observations: list[dict[str, object]] = []
    final_asset_id: str | None = None
    provider_cost: float | None = None

    while monotonic() < deadline:
        try:
            observation = poller.poll(provider_job_id)
        except OpenRouterVideoProviderError as exc:
            diagnostic = str(exc)
            receipt["provider_terminal_error"] = diagnostic
            if diagnostic.startswith("PROVIDER_COST_NONZERO:"):
                _fail(
                    receipt_path,
                    receipt,
                    "COST_POLICY_VIOLATION",
                    "provider reported non-zero cost for an explicitly-free model",
                )
            if diagnostic.startswith(
                (
                    "ZERO_COST_EVIDENCE_MISSING:",
                    "ZERO_COST_EVIDENCE_UNKNOWN:",
                    "PROVIDER_USAGE_UNAVAILABLE:",
                )
            ):
                _fail(
                    receipt_path,
                    receipt,
                    "BLOCKED_COST_EVIDENCE_MISSING",
                    diagnostic,
                )
            _fail(
                receipt_path,
                receipt,
                "FAILED_PROVIDER_POLL",
                diagnostic,
            )
        metadata = dict(observation.metadata)
        poll_observations.append(
            {
                "status": observation.status.value,
                "output_asset_ids": list(observation.output_asset_ids),
                "error_code": observation.error_code,
                "error_message": observation.error_message,
                "metadata": metadata,
            }
        )
        receipt["poll_observations"] = poll_observations
        _persist(receipt_path, receipt)

        if observation.status is ProviderJobStatus.SUCCEEDED:
            provider_cost = provider_reported_cost(metadata)
            if provider_cost is None:
                _fail(
                    receipt_path,
                    receipt,
                    "BLOCKED_COST_EVIDENCE_MISSING",
                    "free variant completed but provider did not report exact cost evidence",
                )
            if provider_cost != 0.0:
                _fail(
                    receipt_path,
                    receipt,
                    "COST_POLICY_VIOLATION",
                    "provider reported non-zero cost for an explicitly-free model",
                )
            if not observation.output_asset_ids:
                _fail(
                    receipt_path,
                    receipt,
                    "FAILED_PROVIDER_RECEIPT",
                    "successful provider observation omitted output asset evidence",
                )
            final_asset_id = observation.output_asset_ids[0]
            break

        if observation.status in {
            ProviderJobStatus.FAILED,
            ProviderJobStatus.CANCELLED,
        }:
            _fail(
                receipt_path,
                receipt,
                "FAILED_FREE_PROVIDER_GENERATION",
                observation.error_message or observation.status.value,
            )
        sleep(float(poll_interval_seconds))
    else:
        _fail(
            receipt_path,
            receipt,
            "FAILED_FREE_PROVIDER_TIMEOUT",
            "free provider job did not become terminal within the bounded polling window",
        )

    if final_asset_id is None:
        _fail(
            receipt_path,
            receipt,
            "FAILED_PROVIDER_RECEIPT",
            "provider completed without an exact output asset reference",
        )

    retriever = OpenRouterGeneratedAssetRetriever(
        api_key,
        provider_id=FREE_PROVIDER_NAME,
        transport=active_transport,
    )
    asset = retriever.retrieve(final_asset_id)
    if not mp4_signature_ok(asset.body):
        _fail(
            receipt_path,
            receipt,
            "FAILED_MP4_SIGNATURE",
            "retrieved provider artifact does not contain a valid MP4 ftyp signature",
        )

    artifact_sha256 = hashlib.sha256(asset.body).hexdigest()
    video_path.write_bytes(asset.body)

    receipt["status"] = "PASS"
    receipt["provider_reported_cost_usd"] = provider_cost
    receipt["generation_receipt_ref"] = f"openrouter-free://videos/{provider_job_id}"
    receipt["artifact"] = {
        "path": video_path.name,
        "source_asset_id": asset.source_asset_id,
        "sha256": artifact_sha256,
        "bytes": len(asset.body),
        "content_type": asset.content_type,
        "metadata": dict(asset.metadata),
    }
    receipt["artifact_receipt_ref"] = f"sha256:{artifact_sha256}"
    receipt["finished_at"] = _utc_now()
    _persist(receipt_path, receipt)
    return receipt


def certification_from_environment() -> dict[str, object]:
    """Run the free-only certification from the GitHub Production environment."""

    proof_dir = Path(
        os.environ.get(
            "VIDEO_FREE_PROVIDER_PROOF_DIR",
            "artifacts/video-free-provider-proof",
        )
    )
    return run_free_certification(
        api_key=os.environ.get("OPENROUTER_API_KEY", ""),
        proof_dir=proof_dir,
        revision_sha=os.environ.get("GITHUB_SHA", "unknown"),
        run_id=os.environ.get("GITHUB_RUN_ID", "local"),
        run_attempt=os.environ.get("GITHUB_RUN_ATTEMPT", "1"),
        candidate_models=free_model_candidates(
            os.environ.get("VIDEO_FREE_PROVIDER_MODELS")
        ),
    )


def _persist(path: Path, receipt: dict[str, object]) -> None:
    path.write_text(
        json.dumps(receipt, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _fail(
    path: Path,
    receipt: dict[str, object],
    status: str,
    message: str,
) -> NoReturn:
    receipt["status"] = status
    receipt["error"] = message
    receipt["finished_at"] = _utc_now()
    _persist(path, receipt)
    raise FreeProviderCertificationError(message)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    proof = certification_from_environment()
    artifact = proof.get("artifact")
    artifact_sha = artifact.get("sha256") if isinstance(artifact, dict) else None
    print("FREE_PROVIDER_PROOF_STATUS=PASS")
    print(f"FREE_PROVIDER_MODEL={proof.get('selected_model')}")
    print(f"FREE_PROVIDER_JOB_ID={proof.get('external_job_id')}")
    print(f"FREE_PROVIDER_COST_USD={proof.get('provider_reported_cost_usd')}")
    print(f"FREE_PROVIDER_ARTIFACT_SHA256={artifact_sha}")
