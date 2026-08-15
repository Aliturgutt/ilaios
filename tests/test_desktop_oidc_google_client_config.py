from __future__ import annotations

from services.desktop_oidc import DesktopOIDCService


def test_google_desktop_provider_environment_uses_public_client_configuration() -> None:
    service = DesktopOIDCService.from_environment(
        {
            "ILAIOS_DESKTOP_OIDC_PROVIDERS_JSON": """
            [
              {
                "provider_id": "google",
                "display_name": "Google",
                "issuer": "https://accounts.google.com",
                "authorization_endpoint": "https://accounts.google.com/o/oauth2/v2/auth",
                "token_endpoint": "https://oauth2.googleapis.com/token",
                "jwks_uri": "https://www.googleapis.com/oauth2/v3/certs",
                "client_id": "desktop-client.apps.googleusercontent.com",
                "scopes": ["openid", "profile", "email"]
              }
            ]
            """
        }
    )

    assert service is not None
    assert service.providers() == (
        {"provider_id": "google", "display_name": "Google"},
    )
