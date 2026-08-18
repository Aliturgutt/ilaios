from __future__ import annotations

from services.desktop_identity_server import _reference_factory_count


def test_reference_intent_targets_exactly_one_factory() -> None:
    assert _reference_factory_count("Build a premium website for a furniture company") == 1
    assert _reference_factory_count("Video creation task: Create a product reveal") == 1
    assert _reference_factory_count("Create a product image") == 0
    assert (
        _reference_factory_count(
            "Video creation task: Create a launch video and a website landing page"
        )
        == 2
    )
