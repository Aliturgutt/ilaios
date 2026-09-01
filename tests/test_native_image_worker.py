from __future__ import annotations

from dataclasses import dataclass

import pytest

from src.image_automation.model_candidates import flux1_schnell_candidate
from src.image_automation.native_image_worker import (
    NATIVE_IMAGE_OPERATION,
    NATIVE_IMAGE_PROVIDER_NAME,
    NativeImageOutOfMemoryError,
    NativeImageReceipt,
    NativeImageWorker,
)
from src.media_model_governance import (
    MediaModelManifest,
    NativeWorkerHardware,
    NativeWorkloadRequirements,
    promote_to_approved_native,
)
from src.video_automation.models import ProviderRequest


@dataclass
class _Backend:
    receipt: NativeImageReceipt | None = None
    error: Exception | None = None
    calls: int = 0

    def generate(
        self,
        request: ProviderRequest,
        *,
        manifest: MediaModelManifest,
        hardware: NativeWorkerHardware,
    ) -> NativeImageReceipt:
        del request, manifest, hardware
        self.calls += 1
        if self.error is not None:
            raise self.error
        assert self.receipt is not None
        return self.receipt


def _manifest() -> MediaModelManifest:
    return promote_to_approved_native(
        flux1_schnell_candidate(),
        checkpoint_revision="flux-checkpoint-001",
        checkpoint_digest_sha256="a" * 64,
        security_review_ref="evidence://security/flux-001",
    )


def _hardware() -> NativeWorkerHardware:
    return NativeWorkerHardware(
        worker_id="image-worker-001",
        gpu_name="test-gpu",
        vram_gb=24,
        ram_gb=64,
        cuda_available=True,
        healthy=True,
        free_vram_gb=20,
    )


def _requirements() -> NativeWorkloadRequirements:
    return NativeWorkloadRequirements(required_vram_gb=12, required_ram_gb=32)


def _receipt(*, digest: str = "a" * 64) -> NativeImageReceipt:
    return NativeImageReceipt(
        artifact_reference="artifact://image/final-001.png",
        artifact_sha256="b" * 64,
        checkpoint_revision="flux-checkpoint-001",
        checkpoint_digest_sha256=digest,
        generation_evidence_ref="evidence://image/generation-001",
        width=1024,
        height=1024,
        mime_type="image/png",
    )


def _request() -> ProviderRequest:
    return ProviderRequest(
        request_id="image-native-request-001",
        job_id="image-job-001",
        provider_name=NATIVE_IMAGE_PROVIDER_NAME,
        operation=NATIVE_IMAGE_OPERATION,
        payload={
            "model_id": _manifest().model_id,
            "routing_decision_id": "route-image-001",
        },
    )


def test_review_required_flux_candidate_cannot_execute_natively() -> None:
    with pytest.raises(ValueError, match="APPROVED_NATIVE"):
        NativeImageWorker(
            manifest=flux1_schnell_candidate(),
            hardware=_hardware(),
            requirements=_requirements(),
            backend=_Backend(receipt=_receipt()),
        )


def test_native_image_success_binds_artifact_and_checkpoint_evidence() -> None:
    backend = _Backend(receipt=_receipt())
    worker = NativeImageWorker(
        manifest=_manifest(),
        hardware=_hardware(),
        requirements=_requirements(),
        backend=backend,
    )

    result = worker.execute(_request())

    assert result.success
    assert result.metadata["artifact_sha256"] == "b" * 64
    assert result.metadata["checkpoint_digest_sha256"] == "a" * 64
    assert result.metadata["routing_decision_id"] == "route-image-001"
    assert backend.calls == 1


def test_native_image_checkpoint_mismatch_fails_closed() -> None:
    backend = _Backend(receipt=_receipt(digest="c" * 64))
    worker = NativeImageWorker(
        manifest=_manifest(),
        hardware=_hardware(),
        requirements=_requirements(),
        backend=backend,
    )

    result = worker.execute(_request())

    assert not result.success
    assert result.error_code == "NATIVE_IMAGE_CHECKPOINT_DIGEST_MISMATCH"
    assert backend.calls == 1


def test_native_image_oom_is_not_hiddenly_retried() -> None:
    backend = _Backend(error=NativeImageOutOfMemoryError("CUDA out of memory"))
    worker = NativeImageWorker(
        manifest=_manifest(),
        hardware=_hardware(),
        requirements=_requirements(),
        backend=backend,
    )

    result = worker.execute(_request())

    assert not result.success
    assert result.error_code == "NATIVE_IMAGE_OOM"
    assert backend.calls == 1
