from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pytest

from src.video_automation.generated_asset_retrieval import (
    AssetHttpResponse,
    GeneratedAssetPayload,
    GeneratedAssetRetrievalCoordinator,
    GeneratedAssetRetrievalError,
    GeneratedAssetRetrieverRegistry,
    HttpUrlGeneratedAssetRetriever,
)
from src.video_automation.generation_dispatch_planning import (
    EpisodeGenerationDispatchPlan,
    GenerationBatchDispatch,
    GenerationDispatchItem,
)
from src.video_automation.generation_result_ingestion import (
    EpisodeGenerationResultManifest,
    GenerationResultAsset,
)


class _Retriever:
    def __init__(self, provider_id: str = "provider-alpha") -> None:
        self._provider_id = provider_id
        self.calls: list[str] = []

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def retrieve(self, asset_id: str) -> GeneratedAssetPayload:
        self.calls.append(asset_id)
        return GeneratedAssetPayload(
            source_asset_id=asset_id,
            body=f"video:{asset_id}".encode(),
            content_type="video/mp4",
            file_extension=".mp4",
            metadata={"adapter": "fake"},
        )


class _Transport:
    def __init__(self, response: AssetHttpResponse) -> None:
        self.response = response
        self.calls: list[tuple[str, Mapping[str, str], float]] = []

    def get_bytes(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> AssetHttpResponse:
        self.calls.append((url, headers, timeout_seconds))
        return self.response


def _dispatch_plan(provider_id: str = "provider-alpha") -> EpisodeGenerationDispatchPlan:
    item = GenerationDispatchItem(
        sequence_number=1,
        request_id="request-01",
        idempotency_key="a" * 64,
        shot_id="shot-01",
        prompt_text="approved prompt",
        duration_seconds=5.0,
        aspect_ratio="9:16",
        frames_per_second=24,
        output_count=1,
        seed=None,
    )
    dispatch = GenerationBatchDispatch(
        dispatch_id="dispatch-001",
        batch_id="batch-001",
        batch_number=1,
        provider_id=provider_id,
        model_id="model-001",
        operation="video.generate",
        max_parallel_requests=1,
        items=(item,),
        metadata={"episode_id": "episode-001"},
    )
    return EpisodeGenerationDispatchPlan(
        dispatch_plan_id="dispatch-plan-001",
        generation_plan_id="generation-plan-001",
        manifest_id="request-manifest-001",
        episode_id="episode-001",
        dispatches=(dispatch,),
        dispatch_count=1,
        request_count=1,
        metadata={},
    )


def _result_manifest(asset_id: str = "https://assets.test/video.mp4") -> EpisodeGenerationResultManifest:
    asset = GenerationResultAsset(
        asset_id=asset_id,
        dispatch_id="dispatch-001",
        provider_job_id="job-001",
        batch_number=1,
        output_index=1,
        metadata={"source_status": "succeeded"},
    )
    return EpisodeGenerationResultManifest(
        result_manifest_id="result-manifest-001",
        execution_state_id="execution-state-001",
        dispatch_plan_id="dispatch-plan-001",
        generation_plan_id="generation-plan-001",
        request_manifest_id="request-manifest-001",
        episode_id="episode-001",
        assets=(asset,),
        dispatch_count=1,
        succeeded_count=1,
        failed_count=0,
        cancelled_count=0,
        metadata={"asset_count": "1"},
    )


def test_payload_rejects_empty_body() -> None:
    with pytest.raises(GeneratedAssetRetrievalError, match="body"):
        GeneratedAssetPayload("asset-1", b"", "video/mp4", ".mp4")


def test_payload_metadata_is_immutable() -> None:
    payload = GeneratedAssetPayload(
        "asset-1", b"video", "video/mp4", ".mp4", {"a": "b"}
    )
    with pytest.raises(TypeError):
        payload.metadata["x"] = "y"  # type: ignore[index]


def test_registry_lists_provider_ids_in_sorted_order() -> None:
    registry = GeneratedAssetRetrieverRegistry((_Retriever("zeta"), _Retriever("alpha")))
    assert registry.list_provider_ids() == ("alpha", "zeta")


def test_registry_rejects_duplicate_provider() -> None:
    with pytest.raises(GeneratedAssetRetrievalError, match="already registered"):
        GeneratedAssetRetrieverRegistry((_Retriever(), _Retriever()))


def test_registry_rejects_missing_provider() -> None:
    with pytest.raises(GeneratedAssetRetrievalError, match="not registered"):
        GeneratedAssetRetrieverRegistry().get("provider-alpha")


def test_http_retriever_requires_https_url() -> None:
    retriever = HttpUrlGeneratedAssetRetriever(
        "provider-alpha",
        transport=_Transport(AssetHttpResponse(200, b"video", "video/mp4", "https://x/a")),
    )
    with pytest.raises(GeneratedAssetRetrievalError, match="HTTPS"):
        retriever.retrieve("http://assets.test/video.mp4")


def test_http_retriever_maps_mp4_response() -> None:
    transport = _Transport(
        AssetHttpResponse(200, b"video", "video/mp4", "https://cdn.test/video.mp4")
    )
    payload = HttpUrlGeneratedAssetRetriever(
        "provider-alpha", transport=transport, headers={"X-Test": "1"}
    ).retrieve("https://assets.test/video.mp4")
    assert payload.file_extension == ".mp4"
    assert payload.body == b"video"
    assert transport.calls[0][1]["X-Test"] == "1"


def test_http_retriever_rejects_non_success_status() -> None:
    transport = _Transport(
        AssetHttpResponse(403, b"denied", "application/octet-stream", "https://x/a")
    )
    with pytest.raises(GeneratedAssetRetrievalError, match="403"):
        HttpUrlGeneratedAssetRetriever("provider-alpha", transport=transport).retrieve(
            "https://assets.test/video.mp4"
        )


def test_http_retriever_rejects_unsupported_content_type() -> None:
    transport = _Transport(
        AssetHttpResponse(200, b"text", "text/plain", "https://x/a")
    )
    with pytest.raises(GeneratedAssetRetrievalError, match="content_type"):
        HttpUrlGeneratedAssetRetriever("provider-alpha", transport=transport).retrieve(
            "https://assets.test/video.mp4"
        )


def test_coordinator_retrieves_and_persists_asset(tmp_path: Path) -> None:
    retriever = _Retriever()
    manifest = GeneratedAssetRetrievalCoordinator(
        GeneratedAssetRetrieverRegistry((retriever,)), tmp_path
    ).retrieve(_result_manifest(), _dispatch_plan())
    assert manifest.asset_count == 1
    assert retriever.calls == ["https://assets.test/video.mp4"]
    retrieved = manifest.assets[0]
    assert Path(retrieved.local_path).read_bytes() == b"video:https://assets.test/video.mp4"
    assert retrieved.content_type == "video/mp4"


def test_coordinator_is_deterministic_for_same_bytes(tmp_path: Path) -> None:
    coordinator = GeneratedAssetRetrievalCoordinator(
        GeneratedAssetRetrieverRegistry((_Retriever(),)), tmp_path
    )
    first = coordinator.retrieve(_result_manifest(), _dispatch_plan())
    second = coordinator.retrieve(_result_manifest(), _dispatch_plan())
    assert first.retrieval_manifest_id == second.retrieval_manifest_id
    assert first.assets[0].local_path == second.assets[0].local_path


def test_coordinator_routes_by_dispatch_provider(tmp_path: Path) -> None:
    retriever = _Retriever("provider-beta")
    GeneratedAssetRetrievalCoordinator(
        GeneratedAssetRetrieverRegistry((retriever,)), tmp_path
    ).retrieve(_result_manifest(), _dispatch_plan("provider-beta"))
    assert retriever.calls == ["https://assets.test/video.mp4"]


def test_coordinator_rejects_manifest_from_other_dispatch_plan(tmp_path: Path) -> None:
    result = _result_manifest()
    other = EpisodeGenerationDispatchPlan(
        dispatch_plan_id="dispatch-plan-other",
        generation_plan_id="generation-plan-001",
        manifest_id="request-manifest-001",
        episode_id="episode-001",
        dispatches=_dispatch_plan().dispatches,
        dispatch_count=1,
        request_count=1,
        metadata={},
    )
    with pytest.raises(GeneratedAssetRetrievalError, match="does not belong"):
        GeneratedAssetRetrievalCoordinator(
            GeneratedAssetRetrieverRegistry((_Retriever(),)), tmp_path
        ).retrieve(result, other)


def test_coordinator_rejects_unknown_dispatch_id(tmp_path: Path) -> None:
    asset = GenerationResultAsset(
        asset_id="https://assets.test/video.mp4",
        dispatch_id="missing-dispatch",
        provider_job_id="job-001",
        batch_number=1,
        output_index=1,
        metadata={},
    )
    result = EpisodeGenerationResultManifest(
        result_manifest_id="result-manifest-001",
        execution_state_id="execution-state-001",
        dispatch_plan_id="dispatch-plan-001",
        generation_plan_id="generation-plan-001",
        request_manifest_id="request-manifest-001",
        episode_id="episode-001",
        assets=(asset,),
        dispatch_count=1,
        succeeded_count=1,
        failed_count=0,
        cancelled_count=0,
        metadata={},
    )
    with pytest.raises(GeneratedAssetRetrievalError, match="unknown dispatch_id"):
        GeneratedAssetRetrievalCoordinator(
            GeneratedAssetRetrieverRegistry((_Retriever(),)), tmp_path
        ).retrieve(result, _dispatch_plan())


def test_coordinator_rejects_payload_identity_mismatch(tmp_path: Path) -> None:
    class _BadRetriever(_Retriever):
        def retrieve(self, asset_id: str) -> GeneratedAssetPayload:
            return GeneratedAssetPayload("other-asset", b"video", "video/mp4", ".mp4")

    with pytest.raises(GeneratedAssetRetrievalError, match="source_asset_id"):
        GeneratedAssetRetrievalCoordinator(
            GeneratedAssetRetrieverRegistry((_BadRetriever(),)), tmp_path
        ).retrieve(_result_manifest(), _dispatch_plan())


def test_existing_file_with_different_content_is_rejected(tmp_path: Path) -> None:
    coordinator = GeneratedAssetRetrievalCoordinator(
        GeneratedAssetRetrieverRegistry((_Retriever(),)), tmp_path
    )
    first = coordinator.retrieve(_result_manifest(), _dispatch_plan())
    path = Path(first.assets[0].local_path)
    path.write_bytes(b"tampered")
    with pytest.raises(GeneratedAssetRetrievalError, match="different content"):
        coordinator.retrieve(_result_manifest(), _dispatch_plan())


def test_retrieval_manifest_metadata_is_immutable(tmp_path: Path) -> None:
    manifest = GeneratedAssetRetrievalCoordinator(
        GeneratedAssetRetrieverRegistry((_Retriever(),)), tmp_path
    ).retrieve(_result_manifest(), _dispatch_plan())
    with pytest.raises(TypeError):
        manifest.metadata["x"] = "y"  # type: ignore[index]
