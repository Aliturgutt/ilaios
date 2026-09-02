"""Windows composition for Desktop OIDC provider-specific loopback behavior."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import requests

from services.desktop_oidc import (
    DesktopAuthStart,
    DesktopIdentityError,
    OIDCProviderConfig,
)
from services.desktop_oidc_microsoft import DesktopOIDCService as _MicrosoftDesktopOIDCService
from services.identity import Principal


_CANONICAL_IDENTITY_ENDPOINT = "https://app.ilaios.com/auth/desktop/canonicalize"
_LI_MEMORY_LIST_ENDPOINT = "https://app.ilaios.com/api/desktop/li/memories/list"
_LI_MEMORY_REMEMBER_ENDPOINT = (
    "https://app.ilaios.com/api/desktop/li/memories/remember"
)
_LI_FOUNDER_ATTRIBUTE = ("ilaios_li_founder", "true")


class DesktopOIDCService(_MicrosoftDesktopOIDCService):
    """Use Microsoft's supported system-browser localhost redirect on Windows.

    The local identity server itself remains bound to IPv4 loopback. For the
    Microsoft public-client request, only the redirect URI presented to the
    provider is normalized from 127.0.0.1 to localhost while preserving the
    ephemeral port and callback path. Microsoft Entra ignores the localhost port
    for native-app redirect matching, which lets the app registration use the
    stable `http://localhost/oauth/callback` URI without fixing a process port.

    Google keeps its already proven 127.0.0.1 loopback behavior unchanged.
    """

    def __init__(
        self,
        providers: tuple[OIDCProviderConfig, ...],
        *,
        canonical_request_session: requests.Session | None = None,
        canonical_identity_endpoint: str = _CANONICAL_IDENTITY_ENDPOINT,
        **kwargs: Any,
    ) -> None:
        endpoint = urlsplit(canonical_identity_endpoint.strip())
        if (
            endpoint.scheme != "https"
            or endpoint.hostname != "app.ilaios.com"
            or endpoint.port not in {None, 443}
            or endpoint.path != "/auth/desktop/canonicalize"
            or endpoint.query
            or endpoint.fragment
            or endpoint.username is not None
            or endpoint.password is not None
        ):
            raise DesktopIdentityError(
                "Desktop canonical identity endpoint is invalid"
            )
        self._canonical_identity_endpoint = canonical_identity_endpoint.strip()
        self._canonical_http = canonical_request_session or requests.Session()
        super().__init__(providers, **kwargs)

    def _canonicalize_principal(
        self,
        provider_id: str,
        encoded_token: str,
        principal: Principal,
        now: datetime,
    ) -> Principal:
        if provider_id != "google":
            raise DesktopIdentityError(
                "Desktop provider is not enabled for canonical account resolution"
            )
        try:
            response = self._canonical_http.post(
                self._canonical_identity_endpoint,
                json={
                    "provider_id": provider_id,
                    "id_token": encoded_token,
                },
                headers={"Accept": "application/json"},
                timeout=10,
            )
        except requests.RequestException as error:
            raise DesktopIdentityError(
                "Desktop canonical identity resolution failed"
            ) from error
        try:
            payload = response.json()
        except ValueError as error:
            raise DesktopIdentityError(
                "Desktop canonical identity response is malformed"
            ) from error
        if response.status_code != 200 or not isinstance(payload, dict):
            raise DesktopIdentityError(
                "Desktop canonical identity resolution was denied"
            )
        user_id = payload.get("user_id")
        tenant_id = payload.get("tenant_id")
        li_founder = payload.get("li_founder", False)
        if (
            not isinstance(user_id, str)
            or not user_id.startswith("usr_")
            or not isinstance(tenant_id, str)
            or not tenant_id.startswith("tnt_")
            or not isinstance(li_founder, bool)
        ):
            raise DesktopIdentityError(
                "Desktop canonical identity response is malformed"
            )
        attributes = set(principal.attributes)
        if li_founder:
            attributes.add(_LI_FOUNDER_ATTRIBUTE)
        else:
            attributes.discard(_LI_FOUNDER_ATTRIBUTE)
        return Principal(
            principal_id=user_id,
            tenant_id=tenant_id,
            kind=principal.kind,
            roles=principal.roles,
            attributes=frozenset(attributes),
            authentication_methods=principal.authentication_methods,
        )

    def list_li_memories(
        self,
        session_id: str,
        now: datetime | None = None,
    ) -> tuple[dict[str, object], ...]:
        if not self.is_li_founder_session(session_id, now):
            raise DesktopIdentityError("Desktop Li access denied")
        provider_id, encoded_token = self._session_identity_credential(
            session_id,
            now,
        )
        payload = self._li_request(
            _LI_MEMORY_LIST_ENDPOINT,
            {
                "provider_id": provider_id,
                "id_token": encoded_token,
            },
            expected_status=200,
        )
        memories = payload.get("memories")
        if not isinstance(memories, list):
            raise DesktopIdentityError("Desktop Li memory response is malformed")
        return tuple(_validated_memory(item) for item in memories)

    def remember_li_memory(
        self,
        session_id: str,
        *,
        kind: str,
        content: str,
        now: datetime | None = None,
    ) -> dict[str, object]:
        if not self.is_li_founder_session(session_id, now):
            raise DesktopIdentityError("Desktop Li access denied")
        provider_id, encoded_token = self._session_identity_credential(
            session_id,
            now,
        )
        payload = self._li_request(
            _LI_MEMORY_REMEMBER_ENDPOINT,
            {
                "provider_id": provider_id,
                "id_token": encoded_token,
                "kind": kind,
                "content": content,
            },
            expected_status=201,
        )
        return _validated_memory(payload)

    def _li_request(
        self,
        endpoint: str,
        document: dict[str, object],
        *,
        expected_status: int,
    ) -> dict[str, object]:
        try:
            response = self._canonical_http.post(
                endpoint,
                json=document,
                headers={"Accept": "application/json"},
                timeout=10,
            )
        except requests.RequestException as error:
            raise DesktopIdentityError(
                "Desktop Li memory service is unavailable"
            ) from error
        try:
            payload = response.json()
        except ValueError as error:
            raise DesktopIdentityError(
                "Desktop Li memory response is malformed"
            ) from error
        if response.status_code in {401, 403}:
            raise DesktopIdentityError("Desktop Li memory access was denied")
        if response.status_code == 400:
            raise DesktopIdentityError("Desktop Li memory request was rejected")
        if response.status_code != expected_status or not isinstance(payload, dict):
            raise DesktopIdentityError(
                "Desktop Li memory service returned an invalid response"
            )
        return payload

    def start(
        self,
        provider_id: str,
        redirect_uri: str,
        now: datetime | None = None,
    ) -> DesktopAuthStart:
        if provider_id == "microsoft":
            redirect_uri = _microsoft_system_browser_redirect(redirect_uri)
        return super().start(provider_id, redirect_uri, now=now)


def _validated_memory(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise DesktopIdentityError("Desktop Li memory response is malformed")
    memory_id = value.get("memory_id")
    kind = value.get("kind")
    content = value.get("content")
    source = value.get("source")
    confidence = value.get("confidence")
    sensitivity = value.get("sensitivity")
    created_at = value.get("created_at")
    if (
        not isinstance(memory_id, str)
        or not memory_id.startswith("li_mem_")
        or kind not in {"working", "episodic", "semantic"}
        or not isinstance(content, str)
        or not content
        or not isinstance(source, str)
        or not source
        or isinstance(confidence, bool)
        or not isinstance(confidence, (int, float))
        or not 0.0 <= float(confidence) <= 1.0
        or sensitivity not in {"internal", "private"}
        or not isinstance(created_at, str)
        or not created_at
    ):
        raise DesktopIdentityError("Desktop Li memory response is malformed")
    return {
        "memory_id": memory_id,
        "kind": kind,
        "content": content,
        "source": source,
        "confidence": float(confidence),
        "sensitivity": sensitivity,
        "created_at": created_at,
    }


def _microsoft_system_browser_redirect(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise DesktopIdentityError(
            "Microsoft Desktop OIDC redirect must use local HTTP loopback"
        )
    if parsed.port is None or parsed.path != "/oauth/callback":
        raise DesktopIdentityError(
            "Microsoft Desktop OIDC redirect must use the Desktop callback path"
        )
    return urlunsplit(
        (
            "http",
            f"localhost:{parsed.port}",
            parsed.path,
            "",
            "",
        )
    )


__all__ = ["DesktopIdentityError", "DesktopOIDCService"]
