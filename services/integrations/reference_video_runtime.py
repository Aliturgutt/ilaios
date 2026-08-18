"""Reference-image aware provider boundary for Desktop Video Factory.

The adapter keeps the existing canonical Video runtime authoritative while adding
request-scoped multimodal intent. General visual references use OpenRouter
``input_references``; explicit first/last-frame intent uses ``frame_images`` only
on the corresponding boundary shot. Unsupported edit/localization/output-shape
requests fail before any provider generation POST. Deterministic media-signal QA
runs before the existing independent semantic reviewer for every clip and final.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import MappingProxyType

from services.evidence import EvidenceStore
from services.governance import GovernedRuntimeGateway
from services.reference_assets import (
    current_reference_request_id,
    get_reference_asset_store,
    reference_request_context,
)
from services.runtime import DurableGrantPolicy
from src.video_automation import openrouter_video_provider as _openrouter
from src.video_automation.generation_job_polling import GenerationJobPoller
from src.video_automation.models import MetadataValue, ProviderRequest, ProviderResult
from src.video_automation.openrouter_video_provider import (
    OpenRouterGeneratedAssetRetriever,
    OpenRouterVideoGenerationProvider,
    OpenRouterVideoProviderError,
)

from .desktop_video_runtime import requested_duration
from .provider_video_runtime import (
    ObjectiveResolver,
    ProviderBackedDesktopVideoRuntime,
    SemanticVideoReviewer,
    _partition_duration,
)
from .video_product_intelligence import (
    VideoProductIntentError,
    derive_video_product_spec,
    validate_video_product_inputs,
)
from .video_reference_intelligence import (
    VideoReferenceIntentError,
    VideoReferenceMode,
    VideoReferencePlan,
    derive_video_reference_plan,
)
from .video_signal_gate import SignalGatedSemanticVideoReviewer, VideoSignalGateError


@dataclass(slots=True)
class _ReferenceDispatchState:
    plan: VideoReferencePlan
    shot_count: int
    next_shot_index: int = 0

    def consume_shot_index(self) -> int:
        if self.next_shot_index >= self.shot_count:
            raise VideoReferenceIntentError(
                "reference dispatch count exceeded the canonical shot plan"
            )
        value = self.next_shot_index
        self.next_shot_index += 1
        return value


_reference_dispatch_state: ContextVar[_ReferenceDispatchState | None] = ContextVar(
    "ilaios_video_reference_dispatch_state", default=None
)


class ReferenceAwareOpenRouterVideoGenerationProvider(OpenRouterVideoGenerationProvider):
    """Submit governed references without silently changing their intended semantics."""

    def execute(self, request: ProviderRequest) -> ProviderResult:
        try:
            self._validate_request(request)
            model_id, item = _openrouter._parse_single_item_payload(request.payload)
            _openrouter._require_free_model_id(model_id)
        except OpenRouterVideoProviderError as exc:
            return _openrouter._failure_result(request, "invalid_request", str(exc))
        except Exception as exc:  # noqa: BLE001
            message = str(exc).strip() or exc.__class__.__name__
            return _openrouter._failure_result(request, "invalid_request", message)

        try:
            catalog_evidence = self._catalog_zero_cost_evidence(model_id)
        except OpenRouterVideoProviderError as exc:
            code, message = _openrouter._coded_error(
                str(exc), "FREE_VIDEO_CATALOG_UNAVAILABLE"
            )
            return _openrouter._failure_result(request, code, message)
        except Exception as exc:  # noqa: BLE001
            message = str(exc).strip() or exc.__class__.__name__
            return _openrouter._failure_result(
                request,
                "FREE_VIDEO_CATALOG_UNAVAILABLE",
                f"OpenRouter video catalog preflight failed: {message}",
            )

        try:
            body = _build_reference_request_body(
                model_id,
                item,
                default_resolution=self._default_resolution,
                generate_audio=self._generate_audio,
            )
            frame_images = body.get("frame_images")
            input_references = body.get("input_references")
            if isinstance(frame_images, list) and frame_images:
                self._prove_frame_support(
                    model_id,
                    tuple(str(value["frame_type"]) for value in frame_images),
                )
            elif isinstance(input_references, list) and input_references:
                self._prove_reference_support(model_id)
            response = self._transport.post_json(
                f"{self._base_url}/videos",
                headers=_openrouter._auth_headers(self._api_key, json_content=True),
                body=body,
                timeout_seconds=self._timeout_seconds,
            )
        except TimeoutError:
            return _openrouter._failure_result(
                request,
                "submission_timeout_uncertain",
                (
                    "OpenRouter video submission response timed out after "
                    f"{self._timeout_seconds:g}s; provider acceptance is unknown and "
                    "automatic resubmission is forbidden to avoid duplicate generation"
                ),
            )
        except (OpenRouterVideoProviderError, VideoReferenceIntentError) as exc:
            message = str(exc)
            if "timed out" in message.lower():
                return _openrouter._failure_result(
                    request,
                    "submission_timeout_uncertain",
                    (
                        "OpenRouter video submission response timed out after "
                        f"{self._timeout_seconds:g}s; provider acceptance is unknown and "
                        "automatic resubmission is forbidden to avoid duplicate generation"
                    ),
                )
            return _openrouter._failure_result(request, "invalid_request", message)
        except Exception as exc:  # noqa: BLE001
            message = str(exc).strip() or exc.__class__.__name__
            return _openrouter._failure_result(request, "transport_error", message)

        if not 200 <= response.status_code < 300:
            code, message = _openrouter._normalize_error(response)
            return _openrouter._failure_result(request, code, message)

        provider_job_id = response.payload.get("id")
        if not isinstance(provider_job_id, str) or not provider_job_id.strip():
            return _openrouter._failure_result(
                request,
                "invalid_provider_response",
                "OpenRouter response does not contain a non-empty video job id",
            )
        metadata: dict[str, MetadataValue] = {
            "backend": "openrouter",
            "cost_policy": "free_only",
            "model_id": model_id,
            "submission_status": _openrouter._string_or_default(
                response.payload.get("status"), "accepted"
            ),
            "catalog_zero_cost": True,
            "catalog_zero_cost_evidence_json": json.dumps(
                dict(catalog_evidence), sort_keys=True, separators=(",", ":")
            ),
            "catalog_zero_cost_evidence_source": "openrouter_videos_models",
        }
        references_value = body.get("input_references")
        frame_images_value = body.get("frame_images")
        reference_count = (
            len(references_value) if isinstance(references_value, list) else 0
        )
        frame_count = len(frame_images_value) if isinstance(frame_images_value, list) else 0
        if reference_count:
            metadata["reference_asset_count"] = reference_count
            metadata["reference_mode"] = "input_references"
        elif frame_count:
            metadata["reference_asset_count"] = frame_count
            metadata["reference_mode"] = "frame_images"
            metadata["frame_types_json"] = json.dumps(
                [str(value["frame_type"]) for value in frame_images_value],
                separators=(",", ":"),
            )
        generation_id = response.payload.get("generation_id")
        if isinstance(generation_id, str) and generation_id.strip():
            metadata["generation_id"] = generation_id
        return ProviderResult(
            request_id=request.request_id,
            provider_name=request.provider_name,
            success=True,
            external_id=provider_job_id,
            metadata=metadata,
        )

    def _prove_reference_support(self, model_id: str) -> None:
        response = self._transport.get_json(
            f"{self._base_url}/videos/models",
            headers=_openrouter._auth_headers(self._api_key),
            timeout_seconds=self._timeout_seconds,
        )
        if not 200 <= response.status_code < 300:
            raise OpenRouterVideoProviderError(
                "REFERENCE_VIDEO_CAPABILITY_UNAVAILABLE: video catalog lookup failed"
            )
        data = response.payload.get("data")
        if not isinstance(data, list):
            raise OpenRouterVideoProviderError(
                "REFERENCE_VIDEO_CAPABILITY_UNAVAILABLE: video catalog is malformed"
            )
        for candidate in data:
            if not isinstance(candidate, Mapping) or candidate.get("id") != model_id:
                continue
            description = candidate.get("description")
            if isinstance(description, str) and "reference" in description.lower():
                return
            raise OpenRouterVideoProviderError(
                "REFERENCE_VIDEO_CAPABILITY_UNPROVEN: selected model description does "
                "not prove reference-to-video support"
            )
        raise OpenRouterVideoProviderError(
            "REFERENCE_VIDEO_CAPABILITY_UNAVAILABLE: selected model is absent from "
            "the authoritative video catalog"
        )

    def _prove_frame_support(self, model_id: str, frame_types: tuple[str, ...]) -> None:
        response = self._transport.get_json(
            f"{self._base_url}/videos/models",
            headers=_openrouter._auth_headers(self._api_key),
            timeout_seconds=self._timeout_seconds,
        )
        if not 200 <= response.status_code < 300:
            raise OpenRouterVideoProviderError(
                "FRAME_VIDEO_CAPABILITY_UNAVAILABLE: video catalog lookup failed"
            )
        data = response.payload.get("data")
        if not isinstance(data, list):
            raise OpenRouterVideoProviderError(
                "FRAME_VIDEO_CAPABILITY_UNAVAILABLE: video catalog is malformed"
            )
        for candidate in data:
            if not isinstance(candidate, Mapping) or candidate.get("id") != model_id:
                continue
            supported = candidate.get("supported_frame_images")
            if not isinstance(supported, list):
                raise OpenRouterVideoProviderError(
                    "FRAME_VIDEO_CAPABILITY_UNPROVEN: selected model does not expose "
                    "supported_frame_images"
                )
            normalized = {str(value) for value in supported}
            missing = sorted(set(frame_types) - normalized)
            if missing:
                raise OpenRouterVideoProviderError(
                    "FRAME_VIDEO_CAPABILITY_UNPROVEN: selected model does not support "
                    + ", ".join(missing)
                )
            return
        raise OpenRouterVideoProviderError(
            "FRAME_VIDEO_CAPABILITY_UNAVAILABLE: selected model is absent from "
            "the authoritative video catalog"
        )


class ReferenceAwareProviderBackedDesktopVideoRuntime(ProviderBackedDesktopVideoRuntime):
    """Keep one governed multimodal intent across the canonical generated shot plan."""

    def __init__(
        self,
        root: Path,
        grants: DurableGrantPolicy,
        governance: GovernedRuntimeGateway,
        evidence: EvidenceStore,
        *,
        objective_resolver: ObjectiveResolver,
        api_key: str,
        model_id: str = _openrouter.SEEDANCE_FREE_MODEL_ID,
        qa_model_id: str = "openrouter/free",
        resolution: str = "720p",
        poll_interval_seconds: float = 5.0,
        max_poll_rounds: int = 144,
        provider: OpenRouterVideoGenerationProvider | None = None,
        poller: GenerationJobPoller | None = None,
        retriever: OpenRouterGeneratedAssetRetriever | None = None,
        reviewer: SemanticVideoReviewer | None = None,
    ) -> None:
        reference_provider = provider or ReferenceAwareOpenRouterVideoGenerationProvider(
            api_key,
            provider_name=self.PROVIDER_ID,
            default_resolution=resolution,
            generate_audio=True,
        )
        super().__init__(
            root,
            grants,
            governance,
            evidence,
            objective_resolver=objective_resolver,
            api_key=api_key,
            model_id=model_id,
            qa_model_id=qa_model_id,
            resolution=resolution,
            poll_interval_seconds=poll_interval_seconds,
            max_poll_rounds=max_poll_rounds,
            provider=reference_provider,
            poller=poller,
            retriever=retriever,
            reviewer=reviewer,
        )
        self._reviewer = SignalGatedSemanticVideoReviewer(self._reviewer)

    def execute(
        self,
        *,
        request_id: str,
        job_id: str,
        grant_id: str,
        now: datetime,
    ) -> dict[str, object]:
        store = get_reference_asset_store()
        references = store.for_request(request_id)
        objective = self._objective_resolver(job_id).strip()
        if not objective:
            raise VideoProductIntentError("provider-backed video objective is unavailable")
        product_spec = derive_video_product_spec(
            objective,
            reference_count=len(references),
        )
        validate_video_product_inputs(
            product_spec,
            source_video_present=False,
            supported_aspect_ratios=("16:9",),
        )
        reference_plan = (
            derive_video_reference_plan(objective, reference_count=len(references))
            if references
            else None
        )
        dispatch_state: _ReferenceDispatchState | None = None
        if reference_plan is not None:
            duration = requested_duration(objective)
            shot_count = len(_partition_duration(duration))
            dispatch_state = _ReferenceDispatchState(reference_plan, shot_count)

        dispatch_token = _reference_dispatch_state.set(dispatch_state)
        try:
            with reference_request_context(request_id):
                result = dict(
                    super().execute(
                        request_id=request_id,
                        job_id=job_id,
                        grant_id=grant_id,
                        now=now,
                    )
                )
        finally:
            _reference_dispatch_state.reset(dispatch_token)

        if dispatch_state is not None and dispatch_state.next_shot_index != dispatch_state.shot_count:
            raise VideoReferenceIntentError(
                "not every canonical shot reached the reference-aware provider boundary"
            )

        artifact_digest = result.get("artifact_digest")
        if not isinstance(artifact_digest, str):
            raise VideoSignalGateError("finished Video result is missing artifact identity")
        signal_evidence = self._reviewer.evidence_for(artifact_digest)
        if signal_evidence is None:
            raise VideoSignalGateError(
                "finished Video lacks deterministic final media-signal evidence"
            )
        result["video_product_spec"] = product_spec.to_dict()
        result["video_product_mode"] = product_spec.mode.value
        qa = result.get("qa")
        if not isinstance(qa, dict):
            raise VideoSignalGateError("finished Video result is missing QA evidence")
        qa_copy = dict(qa)
        qa_copy["signal_quality_passed"] = True
        qa_copy["signal_evidence_id"] = signal_evidence.evidence_id
        qa_copy["black_fraction"] = signal_evidence.black_fraction
        qa_copy["max_freeze_seconds"] = signal_evidence.max_freeze_seconds
        qa_copy["silence_fraction"] = signal_evidence.silence_fraction
        if references:
            result["reference_assets"] = [item.public_metadata() for item in references]
            result["reference_asset_usage"] = reference_plan.mode.value if reference_plan else "none"
            result["reference_plan"] = reference_plan.to_dict() if reference_plan else None
            qa_copy["reference_asset_count"] = len(references)
            qa_copy["reference_assets_consumed"] = True
            qa_copy["reference_mode"] = reference_plan.mode.value if reference_plan else "none"
        result["qa"] = qa_copy
        return result


def _build_reference_request_body(
    model_id: str,
    item: Mapping[str, object],
    *,
    default_resolution: str,
    generate_audio: bool,
) -> Mapping[str, object]:
    body = dict(
        _openrouter._build_openrouter_request_body(
            model_id,
            item,
            default_resolution=default_resolution,
            generate_audio=generate_audio,
        )
    )
    request_id = current_reference_request_id()
    if request_id is None:
        return MappingProxyType(body)
    references = get_reference_asset_store().for_request(request_id)
    if not references:
        return MappingProxyType(body)

    state = _reference_dispatch_state.get()
    if state is None:
        prompt_text = item.get("prompt_text")
        if not isinstance(prompt_text, str):
            raise VideoReferenceIntentError("generation item prompt is unavailable")
        plan = derive_video_reference_plan(prompt_text, reference_count=len(references))
        shot_index = 0
        shot_count = 1
    else:
        plan = state.plan
        shot_index = state.consume_shot_index()
        shot_count = state.shot_count

    store = get_reference_asset_store()
    if plan.mode is VideoReferenceMode.GUIDANCE:
        body["input_references"] = [
            {
                "type": "image_url",
                "image_url": {"url": store.data_url(record)},
            }
            for record in references
        ]
        return MappingProxyType(body)

    frame_images: list[dict[str, object]] = []
    for frame in plan.frame_references:
        applies = (frame.frame_type == "first_frame" and shot_index == 0) or (
            frame.frame_type == "last_frame" and shot_index == shot_count - 1
        )
        if not applies:
            continue
        record = references[frame.asset_index]
        frame_images.append(
            {
                "type": "image_url",
                "image_url": {"url": store.data_url(record)},
                "frame_type": frame.frame_type,
            }
        )
    if frame_images:
        body["frame_images"] = frame_images
    return MappingProxyType(body)
