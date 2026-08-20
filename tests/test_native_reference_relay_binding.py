from __future__ import annotations

from datetime import datetime, timezone
from typing import cast

import pytest

from services.integrations.native_reference_relay import NativeReferenceRelayBinder
from services.integrations.video_runtime import VideoRuntimeError
from services.reference_assets import (
    ReferenceAssetRecord,
    ReferenceAssetRole,
    ReferenceAssetStore,
)
from services.reference_relay import ReferenceRelayTicket
from src.video_automation.openrouter_video_catalog import OpenRouterVideoModel


class _ReferenceStore(ReferenceAssetStore):
    def __init__(self, records: tuple[ReferenceAssetRecord, ...]) -> None:
        self.records = records

    def for_request(self, request_id: str) -> tuple[ReferenceAssetRecord, ...]:
        assert request_id == "request-1"
        return self.records

    def read_bytes(self, record: ReferenceAssetRecord) -> bytes:
        return f"bytes:{record.sha256}".encode()


class _Relay:
    def __init__(self) -> None:
        self.published: list[str] = []
        self.released: list[str] = []

    def publish(
        self,
        *,
        content: bytes,
        mime_type: str,
        sha256_hex: str,
        tenant_id: str,
        principal_id: str,
    ) -> ReferenceRelayTicket:
        assert content
        assert mime_type == "image/png"
        assert tenant_id == "tenant-1"
        assert principal_id == "user-1"
        relay_id = f"relay-{len(self.published) + 1}"
        self.published.append(sha256_hex)
        return ReferenceRelayTicket(
            relay_id=relay_id,
            url=f"https://relay.example/v1/reference-relay/{relay_id}?signed=1",
            sha256=sha256_hex,
            mime_type=mime_type,
            expires_at_epoch_s=9_999_999_999,
        )

    def release(self, ticket: ReferenceRelayTicket) -> None:
        self.released.append(ticket.relay_id)


def _record(role: ReferenceAssetRole, sha_character: str) -> ReferenceAssetRecord:
    return ReferenceAssetRecord(
        asset_id=f"ref-{role.value}",
        principal_id="user-1",
        tenant_id="tenant-1",
        sha256=sha_character * 64,
        mime_type="image/png",
        original_filename=f"{role.value}.png",
        width=10,
        height=10,
        size_bytes=10,
        role=role,
        instruction=None,
        created_at=datetime.now(timezone.utc),
    )


def _model(
    model_id: str = "bytedance/seedance-2.0-fast",
    *,
    frame_roles: tuple[str, ...] = (),
) -> OpenRouterVideoModel:
    return OpenRouterVideoModel(
        model_id=model_id,
        canonical_slug=model_id,
        name=model_id,
        generate_audio=True,
        supported_aspect_ratios=("16:9",),
        supported_durations=(8,),
        supported_frame_images=frame_roles,
        supported_resolutions=("480p",),
        supported_sizes=(),
        allowed_passthrough_parameters=(),
        pricing_skus={"video": "0.01"},
        family=None,
    )


def test_general_product_and_logo_references_use_native_input_references() -> None:
    relay = _Relay()
    binder = NativeReferenceRelayBinder(
        reference_assets=_ReferenceStore(
            (_record(ReferenceAssetRole.PRODUCT, "a"), _record(ReferenceAssetRole.LOGO, "b"))
        ),
        relay=relay,
    )

    prepared = binder.prepare(request_id="request-1", model=_model())
    native_images = cast(
        list[dict[str, str]], prepared.item_fields["native_reference_images"]
    )

    assert prepared.mode == "input-references"
    assert prepared.provider_native_reference_url_used
    assert [item["role"] for item in native_images] == ["product", "logo"]
    assert relay.published == ["a" * 64, "b" * 64]
    binder.release(prepared)
    assert relay.released == ["relay-1", "relay-2"]


def test_unproven_model_keeps_private_visual_brief_fallback_without_relay() -> None:
    relay = _Relay()
    binder = NativeReferenceRelayBinder(
        reference_assets=_ReferenceStore((_record(ReferenceAssetRole.SUBJECT, "a"),)),
        relay=relay,
    )

    prepared = binder.prepare(request_id="request-1", model=_model("other/model"))

    assert prepared.mode == "private-multimodal-brief-fallback"
    assert prepared.item_fields == {}
    assert not prepared.provider_native_reference_url_used
    assert relay.published == []


def test_first_frame_uses_only_frame_images_when_live_model_proves_support() -> None:
    relay = _Relay()
    binder = NativeReferenceRelayBinder(
        reference_assets=_ReferenceStore(
            (
                _record(ReferenceAssetRole.PRODUCT, "a"),
                _record(ReferenceAssetRole.FIRST_FRAME, "b"),
            )
        ),
        relay=relay,
    )

    prepared = binder.prepare(
        request_id="request-1",
        model=_model(frame_roles=("first_frame",)),
    )

    assert prepared.mode == "frame-images"
    assert "first_frame_url" in prepared.item_fields
    assert "native_reference_images" not in prepared.item_fields
    assert relay.published == ["b" * 64]


def test_required_frame_fails_closed_and_releases_ticket_when_model_lacks_support() -> None:
    relay = _Relay()
    binder = NativeReferenceRelayBinder(
        reference_assets=_ReferenceStore((_record(ReferenceAssetRole.FIRST_FRAME, "a"),)),
        relay=relay,
    )

    with pytest.raises(VideoRuntimeError, match="required native frame reference"):
        binder.prepare(request_id="request-1", model=_model(frame_roles=()))

    assert relay.published == ["a" * 64]
    assert relay.released == ["relay-1"]
