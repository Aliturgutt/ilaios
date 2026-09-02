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

    def start(
        self,
        provider_id: str,
        redirect_uri: str,
        now: datetime | None = None,
    ) -> DesktopAuthStart:
        if provider_id == "microsoft":
            redirect_uri = _microsoft_system_browser_redirect(redirect_uri)
        return super().start(provider_id, redirect_uri, now=now)


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
