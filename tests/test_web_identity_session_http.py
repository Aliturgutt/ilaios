from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from services.identity import (
    AuthenticationBoundary,
    IdentityError,
    IdentityKind,
    IdentityPolicy,
    Principal,
    SessionRegistry,
    VerifiedOIDCClaims,
)
from services.web_identity_session_http import (
    WebIdentitySessionBoundary,
    WebIdentitySessionError,
    WebIdentitySessionRequest,
)

_NOW = datetime(2026, 8, 28, 17, 23, tzinfo=timezone.utc)
_AUTH = "a" * 48
_SESSION = "s" * 48
_CSRF = "c" * 48
_ORIGIN = "https://app.ilaios.com"


class _Verifier:
    def __init__(self, *, subject: str = "user-1", tenant: str = "tenant-1") -> None:
        self.subject = subject
        self.tenant = tenant
        self.seen_token: str | None = None

    def verify(self, encoded_token: str) -> VerifiedOIDCClaims:
        self.seen_token = encoded_token
        return VerifiedOIDCClaims(
            issuer="https://identity.ilaios.com",
            audience="ilaios-web",
            subject=self.subject,
            tenant_id=self.tenant,
            expires_at=_NOW + timedelta(minutes=30),
            issued_at=_NOW - timedelta(minutes=1),
            kind=IdentityKind.HUMAN,
            roles=frozenset({"Owner"}),
        )


def _boundary() -> WebIdentitySessionBoundary:
    return WebIdentitySessionBoundary(production_origins=(_ORIGIN,))


def _request(
    *,
    method: str = "GET",
    origin: str | None = None,
    csrf_header: str | None = None,
    authorization: str | None = None,
    include_csrf_cookie: bool = True,
) -> WebIdentitySessionRequest:
    headers: dict[str, str] = {}
    if origin is not None:
        headers["Origin"] = origin
    if csrf_header is not None:
        headers["X-CSRF-Token"] = csrf_header
    if authorization is not None:
        headers["Authorization"] = authorization
    cookies = {
        "__Host-ilaios_auth": _AUTH,
        "__Host-ilaios_session": _SESSION,
    }
    if include_csrf_cookie:
        cookies["__Host-ilaios_csrf"] = _CSRF
    return WebIdentitySessionRequest(
        method=method,
        headers=headers,
        cookies=cookies,
    )


def test_cookie_contract_is_host_only_secure_and_http_only_for_credentials() -> None:
    headers = _boundary().issue_cookie_headers(
        encoded_token=_AUTH,
        session_id=_SESSION,
        csrf_token=_CSRF,
        max_age_seconds=1800,
    )

    auth_cookie, session_cookie, csrf_cookie = headers
    assert auth_cookie.startswith("__Host-ilaios_auth=")
    assert session_cookie.startswith("__Host-ilaios_session=")
    assert csrf_cookie.startswith("__Host-ilaios_csrf=")
    assert "Path=/" in auth_cookie and "Secure" in auth_cookie
    assert "HttpOnly" in auth_cookie and "SameSite=Lax" in auth_cookie
    assert "HttpOnly" in session_cookie and "SameSite=Lax" in session_cookie
    assert "Secure" in csrf_cookie and "SameSite=Strict" in csrf_cookie
    assert "HttpOnly" not in csrf_cookie
    assert all("Domain=" not in value for value in headers)


def test_mutating_request_requires_exact_origin_and_double_submit_csrf() -> None:
    boundary = _boundary()

    credentials = boundary.credentials(
        _request(method="POST", origin=_ORIGIN, csrf_header=_CSRF)
    )
    assert credentials.encoded_token == _AUTH
    assert credentials.session_id == _SESSION

    with pytest.raises(WebIdentitySessionError, match="origin"):
        boundary.credentials(_request(method="POST", csrf_header=_CSRF))
    with pytest.raises(WebIdentitySessionError, match="origin"):
        boundary.credentials(
            _request(
                method="POST",
                origin="https://evil.example",
                csrf_header=_CSRF,
            )
        )
    with pytest.raises(WebIdentitySessionError, match="CSRF"):
        boundary.credentials(_request(method="POST", origin=_ORIGIN))
    with pytest.raises(WebIdentitySessionError, match="csrf cookie"):
        boundary.credentials(
            _request(
                method="POST",
                origin=_ORIGIN,
                csrf_header=_CSRF,
                include_csrf_cookie=False,
            )
        )
    with pytest.raises(WebIdentitySessionError, match="CSRF"):
        boundary.credentials(
            _request(method="POST", origin=_ORIGIN, csrf_header="x" * 48)
        )


def test_browser_boundary_rejects_script_selected_authorization_header() -> None:
    with pytest.raises(WebIdentitySessionError, match="Authorization"):
        _boundary().credentials(
            _request(method="GET", authorization="Bearer attacker-selected")
        )


def test_safe_read_uses_host_only_cookies_without_requiring_csrf() -> None:
    credentials = _boundary().credentials(_request(include_csrf_cookie=False))
    assert credentials.encoded_token == _AUTH
    assert credentials.session_id == _SESSION


def test_cross_site_oauth_callback_safe_read_allows_strict_csrf_cookie_to_be_absent() -> None:
    credentials = _boundary().credentials(
        WebIdentitySessionRequest(
            method="GET",
            headers={},
            cookies={
                "__Host-ilaios_auth": _AUTH,
                "__Host-ilaios_session": _SESSION,
            },
        )
    )
    assert credentials.encoded_token == _AUTH
    assert credentials.session_id == _SESSION


def test_mutating_request_still_requires_strict_csrf_cookie() -> None:
    with pytest.raises(WebIdentitySessionError, match="csrf cookie"):
        _boundary().credentials(
            WebIdentitySessionRequest(
                method="POST",
                headers={"Origin": _ORIGIN, "X-CSRF-Token": _CSRF},
                cookies={
                    "__Host-ilaios_auth": _AUTH,
                    "__Host-ilaios_session": _SESSION,
                },
            )
        )


def test_authentication_and_session_binding_stay_canonical() -> None:
    verifier = _Verifier()
    authentication = AuthenticationBoundary(
        verifier,
        IdentityPolicy(
            trusted_issuers=frozenset({"https://identity.ilaios.com"}),
            audience="ilaios-web",
            maximum_session=timedelta(hours=1),
        ),
    )
    sessions = SessionRegistry(maximum_lifetime=timedelta(hours=1))
    principal = Principal(
        principal_id="user-1",
        tenant_id="tenant-1",
        kind=IdentityKind.HUMAN,
        roles=frozenset({"Owner"}),
        attributes=frozenset(),
        authentication_methods=frozenset(),
    )
    sessions.issue(_SESSION, principal, _NOW, timedelta(minutes=30))

    bound_principal, bound_session = _boundary().authenticate_and_bind(
        authentication=authentication,
        sessions=sessions,
        request=_request(method="POST", origin=_ORIGIN, csrf_header=_CSRF),
        now=_NOW,
    )

    assert verifier.seen_token == _AUTH
    assert bound_principal.principal_id == "user-1"
    assert bound_principal.tenant_id == "tenant-1"
    assert bound_session.session_id == _SESSION


def test_cross_principal_session_substitution_fails_closed() -> None:
    verifier = _Verifier(subject="user-1", tenant="tenant-1")
    authentication = AuthenticationBoundary(
        verifier,
        IdentityPolicy(
            trusted_issuers=frozenset({"https://identity.ilaios.com"}),
            audience="ilaios-web",
            maximum_session=timedelta(hours=1),
        ),
    )
    sessions = SessionRegistry(maximum_lifetime=timedelta(hours=1))
    attacker = Principal(
        principal_id="user-2",
        tenant_id="tenant-1",
        kind=IdentityKind.HUMAN,
        roles=frozenset({"Owner"}),
        attributes=frozenset(),
        authentication_methods=frozenset(),
    )
    sessions.issue(_SESSION, attacker, _NOW, timedelta(minutes=30))

    with pytest.raises(IdentityError, match="session principal"):
        _boundary().authenticate_and_bind(
            authentication=authentication,
            sessions=sessions,
            request=_request(),
            now=_NOW,
        )


def test_production_origin_and_cookie_inputs_fail_closed() -> None:
    for unsafe_origin in (
        "http://app.ilaios.com",
        "https://localhost",
        "https://127.0.0.1",
        "https://[::1]",
    ):
        with pytest.raises(WebIdentitySessionError):
            WebIdentitySessionBoundary(production_origins=(unsafe_origin,))
    with pytest.raises(WebIdentitySessionError):
        WebIdentitySessionBoundary(
            production_origins=("https://app.ilaios.com", "https://APP.ilaios.com")
        )
    with pytest.raises(WebIdentitySessionError, match="lifetime"):
        _boundary().issue_cookie_headers(
            encoded_token=_AUTH,
            session_id=_SESSION,
            csrf_token=_CSRF,
            max_age_seconds=86_401,
        )


def test_logout_cookie_clear_contract_expires_all_credentials() -> None:
    headers = _boundary().clear_cookie_headers()
    assert len(headers) == 3
    assert all("Max-Age=0" in value for value in headers)
    assert all("Secure" in value and "Path=/" in value for value in headers)
