from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast

import pytest
import requests

import services.google_oidc as google_oidc
from services.desktop_oidc import DesktopIdentityError, OIDCProviderConfig
from services.desktop_oidc_windows import DesktopOIDCService
from services.identity import IdentityKind, Principal

_NOW = datetime(2026, 9, 2, 12, 0, tzinfo=UTC)


class _Response:
    def __init__(self, status_code: int, payload: dict[str, object]) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict[str, object]:
        return self._payload


class _MemoryHTTP:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def post(self, url: str, **kwargs: object) -> _Response:
        self.calls.append({"url": url, **kwargs})
        document = kwargs.get("json")
        if url.endswith("/memories/list"):
            return _Response(
                200,
                {
                    "memories": [
                        {
                            "memory_id": "li_mem_existing",
                            "kind": "semantic",
                            "content": "Founder memory",
                            "source": "desktop",
                            "confidence": 1.0,
                            "sensitivity": "private",
                            "created_at": "2026-09-02T12:00:00+00:00",
                        }
                    ]
                },
            )
        assert isinstance(document, dict)
        return _Response(
            201,
            {
                "memory_id": "li_mem_new",
                "kind": document["kind"],
                "content": document["content"],
                "source": "desktop",
                "confidence": 1.0,
                "sensitivity": "private",
                "created_at": "2026-09-02T12:01:00+00:00",
            },
        )


def _provider() -> OIDCProviderConfig:
    return OIDCProviderConfig(
        provider_id="google",
        display_name="Google",
        issuer=google_oidc.GOOGLE_ISSUER,
        authorization_endpoint=google_oidc.GOOGLE_AUTHORIZATION_ENDPOINT,
        token_endpoint=google_oidc.GOOGLE_TOKEN_ENDPOINT,
        jwks_uri=google_oidc.GOOGLE_JWKS_URI,
        client_id="desktop-client-id",
    )


def _founder_service(http: _MemoryHTTP) -> DesktopOIDCService:
    service = DesktopOIDCService(
        (_provider(),),
        canonical_request_session=cast(requests.Session, http),
    )
    principal = Principal(
        principal_id="usr_founder",
        tenant_id="tnt_founder",
        kind=IdentityKind.HUMAN,
        roles=frozenset({"user"}),
        attributes=frozenset({("ilaios_li_founder", "true")}),
        authentication_methods=frozenset(),
    )
    session = service._session_registry.issue(
        "desktop-session",
        principal,
        _NOW,
        timedelta(hours=1),
    )
    service._session_tenants[session.session_id] = session.tenant_id
    service._bind_session_entitlements(session.session_id, principal)
    service._bind_session_identity_credential(
        session.session_id,
        "google",
        "signed.desktop.token",
    )
    return service


def test_desktop_li_memory_transport_uses_session_bound_identity_token() -> None:
    http = _MemoryHTTP()
    service = _founder_service(http)

    memories = service.list_li_memories("desktop-session", _NOW)
    stored = service.remember_li_memory(
        "desktop-session",
        kind="working",
        content="Remember this",
        now=_NOW,
    )

    assert memories[0]["content"] == "Founder memory"
    assert stored["content"] == "Remember this"
    assert len(http.calls) == 2
    for call in http.calls:
        assert call["json"] is not None
        document = cast(dict[str, object], call["json"])
        assert document["provider_id"] == "google"
        assert document["id_token"] == "signed.desktop.token"


def test_desktop_li_memory_credential_is_destroyed_on_logout() -> None:
    http = _MemoryHTTP()
    service = _founder_service(http)

    service.logout("desktop-session")

    with pytest.raises(DesktopIdentityError):
        service.list_li_memories("desktop-session", _NOW)
    assert http.calls == []
