"""Secret-bearing OIDC client-auth transport for ILAIOS Desktop.

Provider registration remains non-secret JSON. Providers that require confidential
client authentication may name an environment variable with ``client_secret_env``;
the referenced value is held only in process memory and injected only into the
matching token endpoint/client-id request. The secret is never returned to Flutter
or embedded in provider registration.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from typing import Any, cast

import requests

from services.desktop_oidc import DesktopIdentityError, DesktopOIDCService

_SECRET_ENV_NAME = re.compile(r"^[A-Z_][A-Z0-9_]{2,127}$")


class _ClientSecretSession:
    def __init__(
        self,
        secrets_by_token_client: Mapping[tuple[str, str], str],
        *,
        delegate: Any | None = None,
    ) -> None:
        self._secrets = dict(secrets_by_token_client)
        self._delegate = delegate or requests.Session()

    def post(self, url: str, **kwargs: Any) -> Any:
        data = kwargs.get("data")
        if isinstance(data, Mapping):
            client_id = data.get("client_id")
            if isinstance(client_id, str):
                secret = self._secrets.get((url, client_id))
                if secret is not None:
                    body = dict(data)
                    body["client_secret"] = secret
                    kwargs["data"] = body
        return self._delegate.post(url, **kwargs)


def desktop_oidc_service_from_environment(
    environment: Mapping[str, str] | None = None,
    *,
    request_session: Any | None = None,
) -> DesktopOIDCService | None:
    """Build the canonical Desktop OIDC service with optional env-backed secrets."""

    env = environment or os.environ
    raw = env.get("ILAIOS_DESKTOP_OIDC_PROVIDERS_JSON", "").strip()
    if not raw:
        return None

    try:
        document = json.loads(raw)
    except json.JSONDecodeError as error:
        raise DesktopIdentityError("Desktop OIDC provider JSON is invalid") from error
    if not isinstance(document, list):
        raise DesktopIdentityError(
            "Desktop OIDC provider configuration must be a list"
        )

    secrets_by_token_client: dict[tuple[str, str], str] = {}
    for item in document:
        if not isinstance(item, dict):
            raise DesktopIdentityError("Desktop OIDC provider must be an object")
        provider = cast(dict[str, Any], item)
        if "client_secret" in provider:
            raise DesktopIdentityError(
                "Desktop OIDC client_secret must not be embedded; use client_secret_env"
            )
        secret_env = provider.get("client_secret_env")
        if secret_env is None:
            continue
        if not isinstance(secret_env, str) or _SECRET_ENV_NAME.fullmatch(secret_env) is None:
            raise DesktopIdentityError(
                "Desktop OIDC client_secret_env must be an environment-variable name"
            )
        secret = env.get(secret_env, "").strip()
        if not secret:
            raise DesktopIdentityError(
                "Desktop OIDC client secret environment variable is missing"
            )
        token_endpoint = provider.get("token_endpoint")
        client_id = provider.get("client_id")
        if not isinstance(token_endpoint, str) or not token_endpoint.strip():
            raise DesktopIdentityError("Desktop OIDC token_endpoint is required")
        if not isinstance(client_id, str) or not client_id.strip():
            raise DesktopIdentityError("Desktop OIDC client_id is required")
        secrets_by_token_client[(token_endpoint.strip(), client_id.strip())] = secret

    service = DesktopOIDCService.from_environment(env)
    if service is None:
        return None
    if secrets_by_token_client:
        setattr(
            service,
            "_http",
            _ClientSecretSession(
                secrets_by_token_client,
                delegate=request_session,
            ),
        )
    return service
