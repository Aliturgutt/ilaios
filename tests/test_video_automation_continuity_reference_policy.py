from __future__ import annotations

import pytest

from src.video_automation.continuity_reference_policy import (
    ContinuityReferencePolicyError,
    ExternalReferencePolicyDecision,
    authorize_external_continuity_references,
)
from src.video_automation.series_state import EpisodeContinuityPackage


def _package(*, privacy: str = "TENANT_PRIVATE") -> EpisodeContinuityPackage:
    return EpisodeContinuityPackage(
        series_id="series-001",
        episode_id="episode-001",
        previous_artifact_sha256="a" * 64,
        previous_final_frame="artifact://frame/final.png",
        character_references=("artifact://frame/character.png",),
        location_references=("artifact://frame/location.png",),
        visual_style_fingerprint="style-001",
        color_language="cyan and amber",
        voice_references=("artifact://voice/mira",),
        audio_references=("artifact://music/001",),
        previous_episode_summary="Mira found the first shard.",
        open_narrative_threads=("archive origin",),
        last_scene_reference="artifact://scene/last",
        next_scene_constraints=("continue from accepted final scene",),
        series_bible_revision=1,
        privacy_classification=privacy,
        provenance="accepted-episode-manifest",
    )


def _decision(**overrides: bool) -> ExternalReferencePolicyDecision:
    values = {
        "tenant_external_media_allowed": True,
        "security_policy_allowed": True,
        "data_residency_allowed": True,
        "provider_eligible": True,
        "provider_supports_required_references": True,
    }
    values.update(overrides)
    return ExternalReferencePolicyDecision(
        tenant_external_media_allowed=values["tenant_external_media_allowed"],
        security_policy_allowed=values["security_policy_allowed"],
        data_residency_allowed=values["data_residency_allowed"],
        provider_eligible=values["provider_eligible"],
        provider_supports_required_references=values[
            "provider_supports_required_references"
        ],
        routing_decision_id="route-001",
    )


def test_all_external_reference_gates_must_pass() -> None:
    package = _package()
    assert authorize_external_continuity_references(package, _decision()) == package

    fields = (
        "tenant_external_media_allowed",
        "security_policy_allowed",
        "data_residency_allowed",
        "provider_eligible",
        "provider_supports_required_references",
    )
    for field in fields:
        with pytest.raises(ContinuityReferencePolicyError):
            authorize_external_continuity_references(
                package,
                _decision(**{field: False}),
            )


def test_local_only_privacy_classification_fails_closed() -> None:
    with pytest.raises(ContinuityReferencePolicyError, match="privacy classification"):
        authorize_external_continuity_references(
            _package(privacy="LOCAL_ONLY"),
            _decision(),
        )
