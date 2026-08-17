from __future__ import annotations

from services.desktop_execution_coordinator import normalize_desktop_execution_objective


def test_do_not_publish_is_preserved_as_local_only_constraint() -> None:
    objective = "Create a 30 second cinematic video. Do not publish anywhere."

    normalized = normalize_desktop_execution_objective(objective)

    assert "publish" not in normalized.casefold()
    assert "keep the finished result local only" in normalized.casefold()
    assert "Create a 30 second cinematic video." in normalized


def test_do_not_publish_named_video_is_not_positive_publish_intent() -> None:
    normalized = normalize_desktop_execution_objective(
        "Create the film. Don't publish the video anywhere."
    )

    assert "publish" not in normalized.casefold()
    assert "keep the finished result local only" in normalized.casefold()


def test_negative_youtube_upload_is_not_positive_upload_intent() -> None:
    normalized = normalize_desktop_execution_objective(
        "Create an MP4. Never upload the video to YouTube."
    )

    assert "upload" not in normalized.casefold()
    assert "youtube" not in normalized.casefold()
    assert "keep the finished result local only" in normalized.casefold()


def test_positive_publish_remains_untouched_and_fail_closed() -> None:
    objective = "Create a 30 second video and publish the video."

    assert normalize_desktop_execution_objective(objective) == objective


def test_positive_production_deploy_remains_untouched_and_fail_closed() -> None:
    objective = "Create the result and deploy to production."

    assert normalize_desktop_execution_objective(objective) == objective
