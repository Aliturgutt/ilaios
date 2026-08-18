"""Backward-compatible Desktop identity boundary with shared Web/Video references.

The canonical HTTP/auth/session implementation remains in
``desktop_identity_server_core``. This wrapper only broadens the existing
reference-bearing intent admission from Video-only to Web-or-Video while keeping
all other capabilities fail-closed.
"""

from __future__ import annotations

import secrets
import time as _time
from datetime import datetime, timezone
from http import HTTPStatus

from services.desktop_oidc import DesktopOIDCService
from services.execution_coordinator import ExecutionCoordinator
from services.reference_assets import ReferenceAssetStore

from . import desktop_identity_server_core as _core

# Preserve the public module clock used by recovery tests and operators without
# relying on an implicit re-export from the canonical core module.
time = _time


class DesktopIdentityHTTPServer(_core.DesktopIdentityHTTPServer):
    """Canonical Desktop server with the shared reference-capable handler."""

    def __init__(
        self,
        server_address: tuple[str, int],
        *,
        bearer_token: str,
        identity: DesktopOIDCService | None,
        coordinator: ExecutionCoordinator,
        reference_assets: ReferenceAssetStore | None = None,
    ) -> None:
        super().__init__(
            server_address,
            bearer_token=bearer_token,
            identity=identity,
            coordinator=coordinator,
            reference_assets=reference_assets,
        )
        self.RequestHandlerClass = DesktopIdentityRequestHandler


class DesktopIdentityRequestHandler(_core.DesktopIdentityRequestHandler):
    """Allow governed reference assets only for one Web or Video Factory intent."""

    def _submit_authenticated_intent(self, body: dict[str, object]) -> None:
        session = self._authenticated_session()
        objective = _core._required_string(body, "objective")
        if len(objective) > 20_000:
            raise ValueError("objective exceeds Desktop input limit")
        asset_ids = _core._reference_asset_ids(body.get("reference_asset_ids", []))
        if asset_ids:
            factory_count = _reference_factory_count(objective)
            if factory_count == 0:
                raise ValueError(
                    "reference images may only be attached to Web Factory or Video Factory requests"
                )
            if factory_count != 1:
                raise ValueError(
                    "reference-image requests must target exactly one of Web Factory or Video Factory"
                )

        store = (
            _core._require_reference_store(self.server.reference_assets)
            if asset_ids
            else None
        )
        owned_records = (
            tuple(
                store.get_owned(
                    asset_id,
                    principal_id=session.principal_id,
                    tenant_id=session.tenant_id,
                )
                for asset_id in asset_ids
            )
            if store is not None
            else ()
        )
        digests = tuple(record.sha256 for record in owned_records)
        if len(set(digests)) != len(digests):
            raise ValueError("duplicate reference image content is not allowed")

        request_id = f"exec-{secrets.token_hex(16)}"
        execution = self.server.coordinator.prepare(
            request_id,
            objective,
            token=self.server.bearer_token,
            principal_id=session.principal_id,
            tenant_id=session.tenant_id,
            now=datetime.now(timezone.utc),
        )
        if store is not None:
            store.bind_request(
                request_id,
                asset_ids,
                principal_id=session.principal_id,
                tenant_id=session.tenant_id,
            )
        if execution.get("execution_status") == "ADMITTED":
            self._start_execution(request_id)
        response = dict(execution)
        response["reference_asset_count"] = len(asset_ids)
        self._send_json(HTTPStatus.CREATED, response)


def _reference_factory_count(objective: str) -> int:
    video = _core._is_video_objective(objective)
    normalized = " ".join(objective.casefold().split())
    web = any(
        term in normalized
        for term in (
            "website",
            "web site",
            "web sitesi",
            "landing page",
            "internet sitesi",
        )
    )
    return int(video) + int(web)


__all__ = [
    "DesktopIdentityHTTPServer",
    "DesktopIdentityRequestHandler",
]
