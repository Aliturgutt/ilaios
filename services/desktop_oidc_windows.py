"""Windows composition for Desktop OIDC provider-specific loopback behavior."""

from __future__ import annotations

from datetime import datetime
from urllib.parse import urlsplit, urlunsplit

from services.desktop_oidc import DesktopAuthStart, DesktopIdentityError
from services.desktop_oidc_microsoft import DesktopOIDCService as _MicrosoftDesktopOIDCService


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
