from __future__ import annotations

import pytest

from src.video_automation.openrouter_input_references import (
    NativeReferenceRoutingError,
    build_openrouter_input_references,
)

_SHA = "a" * 64


def test_builds_ordered_native_image_references() -> None:
    item = {
        "native_reference_images": [
            {"url": "https://relay.example/ref/product", "role": "product", "sha256": _SHA},
            {"url": "https://relay.example/ref/logo", "role": "logo", "sha256": "b" * 64},
        ]
    }

    assert build_openrouter_input_references(item) == [
        {"type": "image_url", "image_url": {"url": "https://relay.example/ref/product"}},
        {"type": "image_url", "image_url": {"url": "https://relay.example/ref/logo"}},
    ]


def test_native_references_require_https_and_known_roles() -> None:
    with pytest.raises(NativeReferenceRoutingError, match="HTTPS"):
        build_openrouter_input_references(
            {"native_reference_images": [{"url": "http://relay/ref", "role": "product", "sha256": _SHA}]}
        )

    with pytest.raises(NativeReferenceRoutingError, match="role"):
        build_openrouter_input_references(
            {"native_reference_images": [{"url": "https://relay/ref", "role": "first_frame", "sha256": _SHA}]}
        )


def test_native_references_reject_duplicates_invalid_digests_and_overflow() -> None:
    duplicate = {"url": "https://relay/ref", "role": "product", "sha256": _SHA}
    with pytest.raises(NativeReferenceRoutingError, match="duplicate"):
        build_openrouter_input_references({"native_reference_images": [duplicate, duplicate]})

    with pytest.raises(NativeReferenceRoutingError, match="sha256"):
        build_openrouter_input_references(
            {"native_reference_images": [{"url": "https://relay/ref", "role": "product", "sha256": "bad"}]}
        )

    with pytest.raises(NativeReferenceRoutingError, match="exceeds 20"):
        build_openrouter_input_references(
            {
                "native_reference_images": [
                    {"url": f"https://relay/ref/{index}", "role": "other", "sha256": f"{index:064x}"}
                    for index in range(21)
                ]
            }
        )
