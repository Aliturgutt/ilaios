from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from services.desktop_oidc_windows import DesktopOIDCService


def _metadata_path() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "apps"
        / "desktop"
        / "packaging"
        / "identity"
        / "oidc-providers.public.json"
    )


def test_packaged_identity_metadata_contains_only_public_registration_data() -> None:
    raw = _metadata_path().read_text(encoding="utf-8")
    document = json.loads(raw)

    assert isinstance(document, list)
    assert document
    providers = cast(list[dict[str, Any]], document)
    assert len({item.get("provider_id") for item in providers}) == len(providers)
    for provider in providers:
        assert "client_secret" not in provider
        client_id = provider.get("client_id")
        assert isinstance(client_id, str)
        assert client_id.strip()
        assert "<" not in client_id and ">" not in client_id

    google = next(item for item in providers if item.get("provider_id") == "google")
    assert google["client_id"].endswith(".apps.googleusercontent.com")

    service = DesktopOIDCService.from_environment(
        {"ILAIOS_DESKTOP_OIDC_PROVIDERS_JSON": raw}
    )
    assert service is not None
    assert service.providers() == (
        {"provider_id": "google", "display_name": "Google"},
    )
