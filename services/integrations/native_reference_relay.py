"""Provider-native reference preparation for the canonical Desktop Video Factory.

This layer does not choose a provider or replace visual-brief conditioning. It
turns already-admitted, tenant-bound reference assets into short-lived relay URLs
only when the selected live model proves the requested native mode is usable.
Unsupported general references fall back to the existing private visual brief;
required first/last-frame references fail closed.
"""

from __future__ import annotations

from dataclasses import dataclass

from services.reference_assets import (
    ReferenceAssetError,
    ReferenceAssetRecord,
    ReferenceAssetRole,
    ReferenceAssetStore,
)
from services.reference_relay import ReferenceRelay, ReferenceRelayError, ReferenceRelayTicket
from src.video_automation.openrouter_frame_references import (
    FrameReferenceRequest,
    FrameReferenceRoutingError,
    capability_bound_frame_fields,
)
from src.video_automation.openrouter_video_catalog import OpenRouterVideoModel

from .video_runtime import VideoRuntimeError

# OpenRouter's current reference-to-video guide explicitly demonstrates this
# model. Keep the set narrow and evidence-driven; unknown models retain the
# private visual-brief path instead of receiving unproven native fields.
_NATIVE_INPUT_REFERENCE_MODELS = frozenset({"bytedance/seedance-2.0-fast"})
_FRAME_ROLES = frozenset({ReferenceAssetRole.FIRST_FRAME, ReferenceAssetRole.LAST_FRAME})


@dataclass(frozen=True, slots=True)
class NativeReferencePreparation:
    mode: str
    item_fields: dict[str, object]
    tickets: tuple[ReferenceRelayTicket, ...]
    reference_sha256s: tuple[str, ...]

    @property
    def provider_native_reference_url_used(self) -> bool:
        return bool(self.tickets)


class NativeReferenceRelayBinder:
    """Publish exact request-bound assets for one provider dispatch lifecycle."""

    def __init__(
        self,
        *,
        reference_assets: ReferenceAssetStore,
        relay: ReferenceRelay,
    ) -> None:
        self._reference_assets = reference_assets
        self._relay = relay

    def prepare(
        self,
        *,
        request_id: str,
        model: OpenRouterVideoModel,
    ) -> NativeReferencePreparation:
        records = self._reference_assets.for_request(request_id)
        if not records:
            return NativeReferencePreparation("none", {}, (), ())

        identities = {(record.tenant_id, record.principal_id) for record in records}
        if len(identities) != 1:
            raise VideoRuntimeError("native reference binding spans multiple identities")
        tenant_id, principal_id = next(iter(identities))
        frame_records = tuple(record for record in records if record.role in _FRAME_ROLES)

        if frame_records:
            # frame_images wins over input_references at the provider boundary.
            # Publish only exact frame anchors; all other images remain available
            # to the existing private visual-brief conditioning path.
            return self._prepare_frames(
                frame_records=frame_records,
                tenant_id=tenant_id,
                principal_id=principal_id,
                model=model,
            )

        if model.model_id not in _NATIVE_INPUT_REFERENCE_MODELS:
            return NativeReferencePreparation(
                "private-multimodal-brief-fallback",
                {},
                (),
                tuple(record.sha256 for record in records),
            )

        tickets: list[ReferenceRelayTicket] = []
        native_images: list[dict[str, str]] = []
        try:
            for record in records:
                content = self._reference_assets.read_bytes(record)
                ticket = self._relay.publish(
                    content=content,
                    mime_type=record.mime_type,
                    sha256_hex=record.sha256,
                    tenant_id=record.tenant_id,
                    principal_id=record.principal_id,
                )
                tickets.append(ticket)
                native_images.append(
                    {
                        "url": ticket.url,
                        "role": record.role.value,
                        "sha256": record.sha256,
                    }
                )
        except (ReferenceAssetError, ReferenceRelayError) as error:
            self._release_quietly(tickets)
            raise VideoRuntimeError("native reference relay publication failed") from error
        return NativeReferencePreparation(
            "input-references",
            {"native_reference_images": native_images},
            tuple(tickets),
            tuple(record.sha256 for record in records),
        )

    def release(self, preparation: NativeReferencePreparation) -> None:
        errors = self._release_quietly(list(preparation.tickets))
        if errors:
            raise VideoRuntimeError("native reference relay cleanup failed")

    def _prepare_frames(
        self,
        *,
        frame_records: tuple[ReferenceAssetRecord, ...],
        tenant_id: str,
        principal_id: str,
        model: OpenRouterVideoModel,
    ) -> NativeReferencePreparation:
        tickets: list[ReferenceRelayTicket] = []
        first_url: str | None = None
        last_url: str | None = None
        digests: list[str] = []
        try:
            for record in frame_records:
                content = self._reference_assets.read_bytes(record)
                ticket = self._relay.publish(
                    content=content,
                    mime_type=record.mime_type,
                    sha256_hex=record.sha256,
                    tenant_id=tenant_id,
                    principal_id=principal_id,
                )
                tickets.append(ticket)
                digests.append(record.sha256)
                if record.role is ReferenceAssetRole.FIRST_FRAME:
                    first_url = ticket.url
                elif record.role is ReferenceAssetRole.LAST_FRAME:
                    last_url = ticket.url
            fields = capability_bound_frame_fields(
                model=model,
                references=FrameReferenceRequest(
                    first_frame_url=first_url,
                    last_frame_url=last_url,
                    require_first_frame=first_url is not None,
                    require_last_frame=last_url is not None,
                ),
            )
        except (ReferenceAssetError, ReferenceRelayError, FrameReferenceRoutingError) as error:
            self._release_quietly(tickets)
            raise VideoRuntimeError("required native frame reference is unavailable") from error
        return NativeReferencePreparation(
            "frame-images",
            dict(fields),
            tuple(tickets),
            tuple(digests),
        )

    def _release_quietly(self, tickets: list[ReferenceRelayTicket]) -> int:
        errors = 0
        for ticket in tickets:
            try:
                self._relay.release(ticket)
            except ReferenceRelayError:
                errors += 1
        return errors
