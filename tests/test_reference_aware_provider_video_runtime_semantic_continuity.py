from src.video_automation.reference_image_analysis import ReferenceVisualBrief

from services.integrations.reference_aware_provider_video_runtime import _conditioned_objective


def test_conditioned_objective_locks_reference_identity_across_shots() -> None:
    brief = ReferenceVisualBrief(
        text="Matte dark product with cyan illuminated feature and orange emblem.",
        reference_sha256s=("a" * 64, "b" * 64),
        analyzer_id="test-analyzer",
    )

    objective = _conditioned_objective(
        "Create an eight-second premium cinematic product film.",
        brief,
    )

    assert "immutable visual identities across the entire film" in objective
    assert "same product geometry" in objective
    assert "logo styling" in objective
    assert "Do not substitute a related product variant" in objective
    assert "smooth, motivated camera motion" in objective
    assert "avoid abrupt cuts to extreme close-ups" in objective


def test_conditioned_objective_without_reference_brief_is_unchanged() -> None:
    objective = "Create a clean cinematic video."

    assert _conditioned_objective(objective, None) == objective
