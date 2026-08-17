from __future__ import annotations

import pytest

from src.video_automation.presentation_policy import (
    CaptionDelivery,
    CaptionPolicy,
    infer_caption_policy,
)


def test_captions_are_off_by_default() -> None:
    policy = infer_caption_policy("Create a cinematic 60 second product film")

    assert policy == CaptionPolicy()
    assert not policy.burn_in
    assert not policy.deliver_sidecar


@pytest.mark.parametrize(
    "objective",
    [
        "Altyazı istemiyorum, sadece filmi üret",
        "Altyazısız sinematik bir film yap",
        "Altyazı olmasın",
        "No subtitles please",
        "Create the film without captions",
        "Captions off",
    ],
)
def test_explicit_negative_caption_intent_wins(objective: str) -> None:
    policy = infer_caption_policy(objective, default_enabled=True)

    assert not policy.enabled
    assert policy.delivery is CaptionDelivery.NONE


def test_generic_caption_request_defaults_to_selectable_sidecar() -> None:
    policy = infer_caption_policy("60 saniyelik film yap ve Türkçe altyazı ekle")

    assert policy.enabled
    assert policy.language == "tr"
    assert policy.delivery is CaptionDelivery.SIDECAR
    assert not policy.burn_in
    assert policy.deliver_sidecar


def test_burned_caption_request_is_honored() -> None:
    policy = infer_caption_policy("Türkçe altyazıyı videoya göm")

    assert policy.enabled
    assert policy.language == "tr"
    assert policy.delivery is CaptionDelivery.BURNED
    assert policy.burn_in
    assert not policy.deliver_sidecar


def test_both_caption_delivery_modes_are_supported() -> None:
    policy = infer_caption_policy("English subtitles: both burned-in and SRT sidecar")

    assert policy.enabled
    assert policy.language == "en"
    assert policy.delivery is CaptionDelivery.BOTH
    assert policy.burn_in
    assert policy.deliver_sidecar
