"""Browser-session transport security subordinate to canonical ILAIOS Identity.

This module owns no identity, session, token-minting, or authorization authority. It
only binds browser transport to the existing ``AuthenticationBoundary`` and
``SessionRegistry`` while enforcing production cookie, origin, and CSRF rules.
"""

from __future__ import annotations

import hmac
import ipaddress
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlparse

from services.identity import (
    AuthenticationBoundary,
    IdentityError,
    Principal,
    Session,
    SessionRegistry,
)
from services.web_app_auth_contract import (
    authenticate_with_canonical_boundary,
    validate_bound_session,
)

_AUTH_COOKIE = "__Host-ilaios_auth"
_SESSION_COOKIE = "__Host-ilaios_session"
_CSRF_COOKIE = "__Host-ilaios_csrf"
_CSRF_HEADER = "X-CSRF-Token"
_MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_MAX_COOKIE_AGE_SECONDS = 86_400


class WebIdentitySessionError(IdentityError):
    """Browser-session transport evidence is missing, ambiguous, or unsafe."""


@dataclass(frozen=True, slots=True)
class WebIdentitySessionRequest:
    method: str
    headers: Mapping[str, str]
    cookies: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class WebIdentitySessionCredentials:
    encoded_token: str
    session_id: str


class WebIdentitySessionBoundary:
    """Enforce browser transport controls before canonical auth/session checks."""

    def __init__(self, *, production_origins: tuple[str, ...]) -> None:
        if not production_origins:
            raise WebIdentitySessionError("production origin allowlist is empty")
        normalized = tuple(_production_origin(value) for value in production_origins)
        if len(set(normalized)) != len(normalized):
            raise WebIdentitySessionError("production origin allowlist has duplicates")
        self._production_origins = frozenset(normalized)

    def issue_cookie_headers(
        self,
        *,
        encoded_token: str,
        session_id: str,
        csrf_token: str,
        max_age_seconds: int,
    ) -> tuple[str, str, str]:
        """Build host-only secure browser cookies without minting credentials."""
        token = _opaque(encoded_token, "encoded_token")
        session = _opaque(session_id, "session_id")
        csrf = _opaque(csrf_token, "csrf_token")
        if not 0 < max_age_seconds <= _MAX_COOKIE_AGE_SECONDS:
            raise WebIdentitySessionError("cookie lifetime violates browser policy")
        common = f"Path=/; Max-Age={max_age_seconds}; Secure"
        return (
            f"{_AUTH_COOKIE}={token}; {common}; HttpOnly; SameSite=Lax",
            f"{_SESSION_COOKIE}={session}; {common}; HttpOnly; SameSite=Lax",
            f"{_CSRF_COOKIE}={csrf}; {common}; SameSite=Strict",
        )

    def clear_cookie_headers(self) -> tuple[str, str, str]:
        """Expire all browser credentials on logout/revocation projection."""
        common = "Path=/; Max-Age=0; Secure"
        return (
            f"{_AUTH_COOKIE}=; {common}; HttpOnly; SameSite=Lax",
            f"{_SESSION_COOKIE}=; {common}; HttpOnly; SameSite=Lax",
            f"{_CSRF_COOKIE}=; {common}; SameSite=Strict",
        )

    def credentials(
        self, request: WebIdentitySessionRequest
    ) -> WebIdentitySessionCredentials:
        """Extract browser credentials after origin/CSRF checks, fail closed."""
        method = request.method.strip().upper()
        if not method:
            raise WebIdentitySessionError("HTTP method is required")
        if _header(request.headers, "Authorization") is not None:
            raise WebIdentitySessionError(
                "browser session must not accept script-selected Authorization authority"
            )

        encoded_token = _opaque(request.cookies.get(_AUTH_COOKIE, ""), "auth cookie")
        session_id = _opaque(
            request.cookies.get(_SESSION_COOKIE, ""), "session cookie"
        )

        if method in _MUTATING_METHODS:
            csrf_cookie = _opaque(request.cookies.get(_CSRF_COOKIE, ""), "csrf cookie")
            origin = _header(request.headers, "Origin")
            if origin is None or _production_origin(origin) not in self._production_origins:
                raise WebIdentitySessionError("request origin is not allowlisted")
            csrf_header = _header(request.headers, _CSRF_HEADER)
            if csrf_header is None:
                raise WebIdentitySessionError("CSRF header is required")
            csrf_value = _opaque(csrf_header, "csrf header")
            if not hmac.compare_digest(csrf_cookie, csrf_value):
                raise WebIdentitySessionError("CSRF token mismatch")

        return WebIdentitySessionCredentials(
            encoded_token=encoded_token,
            session_id=session_id,
        )

    def authenticate_and_bind(
        self,
        *,
        authentication: AuthenticationBoundary,
        sessions: SessionRegistry,
        request: WebIdentitySessionRequest,
        now: datetime,
    ) -> tuple[Principal, Session]:
        """Delegate identity and session decisions to the canonical authorities."""
        credentials = self.credentials(request)
        principal = authenticate_with_canonical_boundary(
            authentication,
            encoded_token=credentials.encoded_token,
            now=now,
        )
        session = validate_bound_session(
            sessions,
            session_id=credentials.session_id,
            principal=principal,
            now=now,
        )
        return principal, session


def _header(headers: Mapping[str, str], name: str) -> str | None:
    matches = [
        value for key, value in headers.items() if key.casefold() == name.casefold()
    ]
    if len(matches) > 1:
        raise WebIdentitySessionError(f"ambiguous {name} header")
    if not matches:
        return None
    value = matches[0].strip()
    if not value:
        raise WebIdentitySessionError(f"{name} header is empty")
    return value


def _opaque(value: str, field: str) -> str:
    if value != value.strip() or not 16 <= len(value) <= 4096:
        raise WebIdentitySessionError(f"{field} is invalid")
    if any(character.isspace() or ord(character) < 0x20 for character in value):
        raise WebIdentitySessionError(f"{field} is invalid")
    if ";" in value or "," in value:
        raise WebIdentitySessionError(f"{field} is invalid")
    return value


def _production_origin(value: str) -> str:
    candidate = value.strip()
    if not candidate:
        raise WebIdentitySessionError("production origin is required")
    parsed = urlparse(candidate)
    try:
        port = parsed.port
    except ValueError as error:
        raise WebIdentitySessionError("production origin has invalid port") from error
    host = parsed.hostname
    if (
        parsed.scheme.casefold() != "https"
        or host is None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.params
        or parsed.query
        or parsed.fragment
        or port not in {None, 443}
    ):
        raise WebIdentitySessionError("production origin must be an HTTPS origin")
    try:
        normalized_host = host.encode("ascii").decode("ascii").casefold()
    except UnicodeError as error:
        raise WebIdentitySessionError("production origin host must be ASCII") from error
    try:
        ipaddress.ip_address(normalized_host)
    except ValueError:
        pass
    else:
        raise WebIdentitySessionError("production origin must use public DNS")
    if (
        normalized_host == "localhost"
        or normalized_host.endswith(".localhost")
        or "." not in normalized_host
        or normalized_host.startswith(".")
        or normalized_host.endswith(".")
        or ".." in normalized_host
    ):
        raise WebIdentitySessionError("production origin host is not public DNS")
    return f"https://{normalized_host}"
