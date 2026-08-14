from __future__ import annotations

import pytest

from src.media_model_governance import (
    CommercialCompatibility,
    MediaModelManifest,
    ModelEligibility,
)
from src.video_automation.native_video_runtime import (
    GovernedNativeVideoRuntime,
    HardwareProfile,
    NativeBackendResult,
    NativeVideoRequest,
    NativeVideoRuntimeError,
    assess_native_video_eligibility,
)


class _Backend:
    def __init__(self, *, oom: bool = False) -> None:
        self.calls = 0
        self.oom = oom

    def generate(self, *, request, manifest, hardware) -> NativeBackendResult:
        self.calls += 1
        if self.oom:
            raise MemoryError("simulated OOM")
        return NativeBackendResult(
            body=b"deterministic-native-video-artifact",
            runtime_evidence_ref="evidence://runtime/native-video/test-001",
        )


def _approved_manifest(*, minimum_vram_gb: int = 24) -> MediaModelManifest:
    return MediaModelManifest(
        publisher="Example Publisher",
        model_id="example/native-video-v1",
        official_source="https://example.invalid/official-model",
        source_revision="source-revision-001",
        checkpoint_revision="checkpoint-revision-001",
        checkpoint_digest_sha256="a" * 64,
        model_card_url="https://example.invalid/model-card",
        license_identifier="Apache-2.0",
        license_evidence_url="https://example.invalid/license",
        commercial_compatibility=CommercialCompatibility.VERIFIED_COMPATIBLE,
        notice_obligations=("retain license notice",),
        runtime_requirements=("CUDA-compatible accelerator",),
        minimum_vram_gb=minimum_vram_gb,
        minimum_ram_gb=64,
        security_review_ref="evidence://security/native-video-v1",
        eligibility=ModelEligibility.APPROVED_NATIVE,
    )


def _hardware(*, vram_gb: int = 48, production_authorized: bool = True) -> HardwareProfile:
    return HardwareProfile(
        worker_id="gpu-worker-001",
        gpu_name="test-gpu",
        vram_gb=vram_gb,
        ram_gb=128,
        accelerator="cuda",
        production_authorized=production_authorized,
        evidence_ref="evidence://hardware/gpu-worker-001",
    )


def _request(*, production: bool = False) -> NativeVideoRequest:
    return NativeVideoRequest(
        tenant_id="tenant-001",
        user_id="user-001",
        routing_decision_id="route-001",
        model_id="example/native-video-v1",
        prompt="A controlled cinematic tracking shot",
        duration_seconds=5,
        aspect_ratio="16:9",
        resolution="1280x720",
        production=production,
    )


def test_low_vram_worker_is_not_native_eligible() -> None:
    decision = assess_native_video_eligibility(
        _approved_manifest(minimum_vram_gb=24),
        _hardware(vram_gb=4),
        production=False,
    )
    assert not decision.eligible
    assert "VRAM" in decision.reason


def test_non_approved_model_cannot_dispatch() -> None:
    manifest = MediaModelManifest(
        publisher="Example Publisher",
        model_id="example/native-video-v1",
        official_source="https://example.invalid/official-model",
        source_revision="source-revision-001",
        checkpoint_revision=None,
        checkpoint_digest_sha256=None,
        model_card_url="https://example.invalid/model-card",
        license_identifier="Apache-2.0",
        license_evidence_url="https://example.invalid/license",
        commercial_compatibility=CommercialCompatibility.VERIFIED_COMPATIBLE,
        notice_obligations=(),
        runtime_requirements=(),
        minimum_vram_gb=None,
        minimum_ram_gb=None,
        security_review_ref=None,
        eligibility=ModelEligibility.REVIEW_REQUIRED,
    )
    backend = _Backend()
    runtime = GovernedNativeVideoRuntime(backend)

    with pytest.raises(NativeVideoRuntimeError, match="not APPROVED_NATIVE"):
        runtime.execute(request=_request(), manifest=manifest, hardware=_hardware())
    assert backend.calls == 0


def test_production_requires_authorized_worker() -> None:
    backend = _Backend()
    runtime = GovernedNativeVideoRuntime(backend)
    with pytest.raises(NativeVideoRuntimeError, match="not authorized for production"):
        runtime.execute(
            request=_request(production=True),
            manifest=_approved_manifest(),
            hardware=_hardware(production_authorized=False),
        )
    assert backend.calls == 0


def test_successful_native_execution_is_bound_to_checkpoint_hardware_and_route() -> None:
    backend = _Backend()
    evidence = GovernedNativeVideoRuntime(backend).execute(
        request=_request(),
        manifest=_approved_manifest(),
        hardware=_hardware(),
    )
    assert backend.calls == 1
    assert len(evidence.sha256_hex) == 64
    assert evidence.checkpoint_digest_sha256 == "a" * 64
    assert evidence.hardware_evidence_ref == "evidence://hardware/gpu-worker-001"
    assert evidence.routing_decision_id == "route-001"


def test_oom_fails_closed_and_requires_new_governed_reroute() -> None:
    backend = _Backend(oom=True)
    with pytest.raises(NativeVideoRuntimeError, match="new governed decision"):
        GovernedNativeVideoRuntime(backend).execute(
            request=_request(),
            manifest=_approved_manifest(),
            hardware=_hardware(),
        )
    assert backend.calls == 1
