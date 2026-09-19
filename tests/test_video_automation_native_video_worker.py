from __future__ import annotations

from dataclasses import dataclass

import pytest

from src.media_model_governance import (
    MediaModelManifest,
    NativeWorkerHardware,
    NativeWorkloadRequirements,
    promote_to_approved_native,
    wan22_ti2v_5b_candidate,
)
from src.video_automation.models import ProviderRequest
from src.video_automation.native_video_worker import (
    NATIVE_VIDEO_OPERATION,
    NATIVE_VIDEO_PROVIDER_NAME,
    NativeGenerationReceipt,
    NativeOutOfMemoryError,
    NativeVideoWorker,
)


@dataclass
class FakeBackend:
    receipt: NativeGenerationReceipt | None = None
    error: Exception | None = None
    call_count: int = 0

    def generate(
        self,
        request: ProviderRequest,
        *,
        manifest: MediaModelManifest,
        hardware: NativeWorkerHardware,
    ) -> NativeGenerationReceipt:
        del request, manifest, hardware
        self.call_count += 1
        if self.error is not None:
            raise self.error
        assert self.receipt is not None
        return self.receipt


def _approved_manifest() -> MediaModelManifest:
    return promote_to_approved_native(
        wan22_ti2v_5b_candidate(),
        checkpoint_revision="checkpoint-rev-001",
        checkpoint_digest_sha256="b" * 64,
        security_review_ref="evidence://security/wan22-001",
    )


def _hardware(
    *, vram_gb: int = 24, free_vram_gb: int = 24
) -> NativeWorkerHardware:
    return NativeWorkerHardware(
        worker_id="native-worker-001",
        gpu_name="test-gpu",
        vram_gb=vram_gb,
        ram_gb=64,
        cuda_available=True,
        healthy=True,
        free_vram_gb=free_vram_gb,
    )


def _requirements() -> NativeWorkloadRequirements:
    return NativeWorkloadRequirements(required_vram_gb=12, required_ram_gb=32)


def _request(
    *,
    routing_decision_id: str | None = "route-001",
    model_id: str | None = None,
) -> ProviderRequest:
    payload = {"model_id": model_id or _approved_manifest().model_id}
    if routing_decision_id is not None:
        payload["routing_decision_id"] = routing_decision_id
    return ProviderRequest(
        request_id="request-001",
        job_id="job-001",
        provider_name=NATIVE_VIDEO_PROVIDER_NAME,
        operation=NATIVE_VIDEO_OPERATION,
        payload=payload,
    )


def _receipt(
    *,
    revision: str = "checkpoint-rev-001",
    digest: str = "b" * 64,
) -> NativeGenerationReceipt:
    return NativeGenerationReceipt(
        artifact_reference="artifact://native/final-001.mp4",
        artifact_sha256="c" * 64,
        checkpoint_revision=revision,
        checkpoint_digest_sha256=digest,
        generation_evidence_ref="evidence://native/generation-001",
    )


def test_review_required_model_cannot_construct_native_worker() -> None:
    backend = FakeBackend(receipt=_receipt())

    with pytest.raises(ValueError, match="APPROVED_NATIVE"):
        NativeVideoWorker(
            manifest=wan22_ti2v_5b_candidate(),
            hardware=_hardware(),
            requirements=_requirements(),
            backend=backend,
        )

    assert backend.call_count == 0


def test_approved_worker_returns_artifact_and_checkpoint_evidence() -> None:
    manifest = _approved_manifest()
    backend = FakeBackend(receipt=_receipt())
    worker = NativeVideoWorker(
        manifest=manifest,
        hardware=_hardware(),
        requirements=_requirements(),
        backend=backend,
    )

    result = worker.execute(_request(model_id=manifest.model_id))

    assert result.success
    assert result.external_id == "artifact://native/final-001.mp4"
    assert result.metadata["artifact_sha256"] == "c" * 64
    assert result.metadata["checkpoint_digest_sha256"] == "b" * 64
    assert result.metadata["routing_decision_id"] == "route-001"
    assert backend.call_count == 1


def test_missing_routing_decision_blocks_before_backend() -> None:
    manifest = _approved_manifest()
    backend = FakeBackend(receipt=_receipt())
    worker = NativeVideoWorker(
        manifest=manifest,
        hardware=_hardware(),
        requirements=_requirements(),
        backend=backend,
    )

    result = worker.execute(_request(routing_decision_id=None, model_id=manifest.model_id))

    assert not result.success
    assert result.error_code == "NATIVE_ROUTING_EVIDENCE_MISSING"
    assert backend.call_count == 0


def test_ineligible_worker_blocks_before_backend() -> None:
    manifest = _approved_manifest()
    backend = FakeBackend(receipt=_receipt())
    worker = NativeVideoWorker(
        manifest=manifest,
        hardware=_hardware(vram_gb=4, free_vram_gb=4),
        requirements=_requirements(),
        backend=backend,
    )

    result = worker.execute(_request(model_id=manifest.model_id))

    assert not result.success
    assert result.error_code == "NATIVE_WORKER_INELIGIBLE"
    assert backend.call_count == 0


def test_backend_checkpoint_digest_mismatch_fails_closed() -> None:
    manifest = _approved_manifest()
    backend = FakeBackend(receipt=_receipt(digest="d" * 64))
    worker = NativeVideoWorker(
        manifest=manifest,
        hardware=_hardware(),
        requirements=_requirements(),
        backend=backend,
    )

    result = worker.execute(_request(model_id=manifest.model_id))

    assert not result.success
    assert result.error_code == "NATIVE_CHECKPOINT_DIGEST_MISMATCH"
    assert backend.call_count == 1


def test_backend_checkpoint_revision_mismatch_fails_closed() -> None:
    manifest = _approved_manifest()
    backend = FakeBackend(receipt=_receipt(revision="different-checkpoint"))
    worker = NativeVideoWorker(
        manifest=manifest,
        hardware=_hardware(),
        requirements=_requirements(),
        backend=backend,
    )

    result = worker.execute(_request(model_id=manifest.model_id))

    assert not result.success
    assert result.error_code == "NATIVE_CHECKPOINT_REVISION_MISMATCH"
    assert backend.call_count == 1


def test_oom_is_reported_once_without_hidden_retry() -> None:
    manifest = _approved_manifest()
    backend = FakeBackend(error=NativeOutOfMemoryError("CUDA out of memory"))
    worker = NativeVideoWorker(
        manifest=manifest,
        hardware=_hardware(),
        requirements=_requirements(),
        backend=backend,
    )

    result = worker.execute(_request(model_id=manifest.model_id))

    assert not result.success
    assert result.error_code == "NATIVE_OOM"
    assert result.error_message == "CUDA out of memory"
    assert backend.call_count == 1
