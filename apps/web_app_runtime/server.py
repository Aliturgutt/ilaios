"""Minimal production HTTP composition boundary for app.ilaios.com.

This runtime is intentionally small. It exposes only the authenticated Web App
identity/session entrypoints and composes existing canonical ILAIOS services.
It is separate from the loopback-only apps/web/server.py control center and from
the public apps/website marketing runtime.
"""

from __future__ import annotations

import json
import logging
import os
import secrets
import sqlite3
from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from typing import Final
from urllib.parse import parse_qs, urlsplit

from services.canonical_browser_session import (
    CanonicalBrowserSessionAuthority,
    CanonicalBrowserSessionError,
)
from services.central_identity import (
    CanonicalAccount,
    CentralIdentityError,
    CentralIdentityService,
)
from services.control_plane.migrations import migrate_database
from services.email_auth import SQLiteEmailChallengeStore
from services.google_oidc import GoogleOIDCEnvironment
from services.google_web_canonical_identity import (
    GoogleWebCanonicalIdentityError,
    GoogleWebCanonicalIdentityFlow,
)
from services.google_web_oauth import (
    GoogleWebOAuthCredentials,
    GoogleWebOAuthError,
    GoogleWebOAuthIssuerAudienceError,
    GoogleWebOAuthIDTokenVerificationError,
    GoogleWebOAuthExpiredTokenError,
    GoogleWebOAuthIssuedAtFutureError,
    GoogleWebOAuthLifetimeExceededError,
    GoogleWebOAuthJwksResolutionError,
    GoogleWebOAuthJWTDecodeError,
    GoogleWebOAuthMalformedClaimsError,
    GoogleWebOAuthNonceError,
    GoogleWebOAuthService,
    GoogleWebOAuthStateError,
    GoogleWebOAuthTemporalClaimsError,
    GoogleWebOAuthTokenExchangeError,
    IdentityChallengeGoogleWebOAuthReplayStore,
)
from services.sqlite_central_identity import SQLiteCentralIdentityStore
from services.web_identity_session_http import (
    WebIdentitySessionBoundary,
    WebIdentitySessionError,
    WebIdentitySessionRequest,
)

_ORIGIN: Final = "https://app.ilaios.com"
_CALLBACK: Final = "https://app.ilaios.com/auth/google/callback"
_DEFAULT_HOST: Final = "0.0.0.0"
_DEFAULT_PORT: Final = 8080
_DEFAULT_SESSION_SECONDS: Final = 3600
_MAX_SESSION_SECONDS: Final = 86_400
_RATE_LIMITS: Final = {
    "/auth/google/start": (120, 60),
    "/auth/google/callback": (240, 60),
    "/auth/logout": (120, 60),
    "/auth/session": (600, 60),
}
_ALLOWED_CALLBACK_QUERY_KEYS: Final = frozenset(
    {"state", "code", "scope", "authuser", "prompt", "hd", "iss"}
)
_AUTH_FAILURE_STAGES: Final = frozenset(
    {
        "oauth_state_rejected",
        "token_exchange_rejected",
        "id_token_verification_rejected",
        "jwks_fetch_or_key_resolution_failed",
        "jwt_signature_or_decode_failed",
        "issuer_or_audience_rejected",
        "nonce_rejected",
        "temporal_claims_rejected",
        "issued_at_future_rejected",
        "expired_token_rejected",
        "token_lifetime_exceeded",
        "malformed_claims_rejected",
        "canonical_identity_rejected",
        "session_issue_rejected",
    }
)
_LOGGER = logging.getLogger(__name__)


class AppRuntimeConfigurationError(ValueError):
    """Production Web App runtime configuration is missing or unsafe."""


@dataclass(frozen=True, slots=True)
class AppRuntimeEnvironment:
    identity_database: Path
    host: str
    port: int
    session_lifetime: timedelta

    @classmethod
    def from_environment(cls, env: Mapping[str, str]) -> AppRuntimeEnvironment:
        raw_database = env.get("ILAIOS_IDENTITY_DATABASE_PATH", "").strip()
        if not raw_database:
            raise AppRuntimeConfigurationError(
                "ILAIOS_IDENTITY_DATABASE_PATH is required"
            )
        identity_database = Path(raw_database).expanduser()

        host = env.get("ILAIOS_APP_HTTP_HOST", _DEFAULT_HOST).strip()
        if not host:
            raise AppRuntimeConfigurationError("ILAIOS_APP_HTTP_HOST is invalid")

        raw_port = env.get("ILAIOS_APP_HTTP_PORT", env.get("PORT", str(_DEFAULT_PORT))).strip()
        raw_session = env.get(
            "ILAIOS_WEB_SESSION_LIFETIME_SECONDS",
            str(_DEFAULT_SESSION_SECONDS),
        ).strip()
        try:
            port = int(raw_port)
            session_seconds = int(raw_session)
        except ValueError as error:
            raise AppRuntimeConfigurationError(
                "runtime port/session configuration is invalid"
            ) from error
        if not 1 <= port <= 65_535:
            raise AppRuntimeConfigurationError("ILAIOS_APP_HTTP_PORT is invalid")
        if not 1 <= session_seconds <= _MAX_SESSION_SECONDS:
            raise AppRuntimeConfigurationError(
                "ILAIOS_WEB_SESSION_LIFETIME_SECONDS is invalid"
            )
        return cls(
            identity_database=identity_database,
            host=host,
            port=port,
            session_lifetime=timedelta(seconds=session_seconds),
        )


@dataclass(frozen=True, slots=True)
class RuntimeRequest:
    method: str
    target: str
    headers: Mapping[str, str]
    source: str = "unknown"


class AppRateLimiter:
    """Small process-local fixed-window limiter for public auth endpoints."""

    def __init__(
        self,
        rules: Mapping[str, tuple[int, int]] = _RATE_LIMITS,
    ) -> None:
        self._rules = dict(rules)
        self._events: dict[tuple[str, str], deque[datetime]] = {}
        self._lock = Lock()

    def check(
        self,
        *,
        source: str,
        path: str,
        now: datetime,
    ) -> int | None:
        rule = self._rules.get(path)
        if rule is None:
            return None
        limit, window_seconds = rule
        if limit < 1 or window_seconds < 1:
            raise ValueError("rate limit rule is invalid")
        normalized_source = source.strip() or "unknown"
        cutoff = now - timedelta(seconds=window_seconds)
        key = (normalized_source, path)
        with self._lock:
            events = self._events.setdefault(key, deque())
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= limit:
                retry_after = int(
                    max(1.0, (events[0] + timedelta(seconds=window_seconds) - now).total_seconds())
                )
                return retry_after
            events.append(now)
        return None


@dataclass(frozen=True, slots=True)
class RuntimeResponse:
    status: HTTPStatus
    body: bytes = b""
    headers: tuple[tuple[str, str], ...] = ()


class AppRuntime:
    """Compose Google OAuth, canonical Identity, and durable browser sessions."""

    def __init__(
        self,
        *,
        environment: AppRuntimeEnvironment,
        oauth: GoogleWebOAuthService,
        sessions: CanonicalBrowserSessionAuthority,
        browser: WebIdentitySessionBoundary,
        rate_limiter: AppRateLimiter | None = None,
    ) -> None:
        self.environment = environment
        self.oauth = oauth
        self.sessions = sessions
        self.browser = browser
        self.rate_limiter = rate_limiter or AppRateLimiter()

    @classmethod
    def from_environment(cls, env: Mapping[str, str]) -> AppRuntime:
        runtime_environment = AppRuntimeEnvironment.from_environment(env)
        oidc = GoogleOIDCEnvironment.from_environment(env)
        oidc.require_production_web_redirect(_CALLBACK)
        credentials = GoogleWebOAuthCredentials.from_environment(env)

        migrate_database(runtime_environment.identity_database)
        replay = IdentityChallengeGoogleWebOAuthReplayStore(
            SQLiteEmailChallengeStore(runtime_environment.identity_database)
        )
        oauth = GoogleWebOAuthService(
            oidc=oidc,
            credentials=credentials,
            replay_store=replay,
        )
        sessions = CanonicalBrowserSessionAuthority(
            runtime_environment.identity_database,
            runtime_environment.session_lifetime,
        )
        browser = WebIdentitySessionBoundary(production_origins=(_ORIGIN,))
        return cls(
            environment=runtime_environment,
            oauth=oauth,
            sessions=sessions,
            browser=browser,
        )

    def dispatch(
        self,
        request: RuntimeRequest,
        *,
        now: datetime | None = None,
    ) -> RuntimeResponse:
        current = (now or datetime.now(UTC)).astimezone(UTC)
        split = urlsplit(request.target)
        method = request.method.strip().upper()
        path = split.path

        retry_after = self.rate_limiter.check(
            source=request.source,
            path=path,
            now=current,
        )
        if retry_after is not None:
            return self._json_error(
                HTTPStatus.TOO_MANY_REQUESTS,
                "rate limit exceeded",
                extra_headers=(("Retry-After", str(retry_after)),),
            )

        try:
            if path == "/health/ready":
                if method != "GET":
                    return self._method_not_allowed("GET")
                return self._ready()
            if path == "/auth/google/start":
                if method != "GET":
                    return self._method_not_allowed("GET")
                if split.query:
                    return self._json_error(
                        HTTPStatus.BAD_REQUEST, "unexpected query parameters"
                    )
                return self._google_start(current)
            if path == "/auth/google/callback":
                if method != "GET":
                    return self._method_not_allowed("GET")
                return self._google_callback(split.query, current)
            if path == "/auth/logout":
                if method != "POST":
                    return self._method_not_allowed("POST")
                if split.query:
                    return self._json_error(
                        HTTPStatus.BAD_REQUEST, "unexpected query parameters"
                    )
                return self._logout(request, current)
            if path == "/auth/session":
                if method != "GET":
                    return self._method_not_allowed("GET")
                if split.query:
                    return self._json_error(
                        HTTPStatus.BAD_REQUEST, "unexpected query parameters"
                    )
                return self._session(request, current)
            return self._json_error(HTTPStatus.NOT_FOUND, "not found")
        except WebIdentitySessionError:
            return self._json_error(HTTPStatus.FORBIDDEN, "request denied")
        except GoogleWebOAuthStateError:
            return self._authentication_denied("oauth_state_rejected")
        except GoogleWebOAuthTokenExchangeError:
            return self._authentication_denied("token_exchange_rejected")
        except GoogleWebOAuthJwksResolutionError:
            return self._authentication_denied("jwks_fetch_or_key_resolution_failed")
        except GoogleWebOAuthJWTDecodeError:
            return self._authentication_denied("jwt_signature_or_decode_failed")
        except GoogleWebOAuthIssuerAudienceError:
            return self._authentication_denied("issuer_or_audience_rejected")
        except GoogleWebOAuthNonceError:
            return self._authentication_denied("nonce_rejected")
        except GoogleWebOAuthIssuedAtFutureError:
            return self._authentication_denied("issued_at_future_rejected")
        except GoogleWebOAuthExpiredTokenError:
            return self._authentication_denied("expired_token_rejected")
        except GoogleWebOAuthLifetimeExceededError:
            return self._authentication_denied("token_lifetime_exceeded")
        except GoogleWebOAuthTemporalClaimsError:
            return self._authentication_denied("temporal_claims_rejected")
        except GoogleWebOAuthMalformedClaimsError:
            return self._authentication_denied("malformed_claims_rejected")
        except GoogleWebOAuthIDTokenVerificationError:
            return self._authentication_denied("id_token_verification_rejected")
        except GoogleWebOAuthError:
            return self._authentication_denied("id_token_verification_rejected")
        except (GoogleWebCanonicalIdentityError, CentralIdentityError):
            return self._authentication_denied("canonical_identity_rejected")
        except CanonicalBrowserSessionError:
            return self._authentication_denied("session_issue_rejected")
        except (sqlite3.Error, OSError):
            return self._json_error(HTTPStatus.SERVICE_UNAVAILABLE, "service unavailable")

    def _ready(self) -> RuntimeResponse:
        try:
            migrate_database(self.environment.identity_database)
            with sqlite3.connect(self.environment.identity_database) as connection:
                connection.execute("PRAGMA foreign_keys = ON")
                connection.execute("SELECT 1").fetchone()
            CanonicalBrowserSessionAuthority(
                self.environment.identity_database,
                self.environment.session_lifetime,
            )
        except (sqlite3.Error, OSError, ValueError):
            return self._json_error(
                HTTPStatus.SERVICE_UNAVAILABLE, "service unavailable"
            )
        return self._json(HTTPStatus.OK, {"status": "ready"})

    def _google_start(self, now: datetime) -> RuntimeResponse:
        started = self.oauth.start(redirect_uri=_CALLBACK, now=now)
        location = started.authorization_url
        parsed = urlsplit(location)
        if (
            parsed.scheme != "https"
            or parsed.hostname != "accounts.google.com"
            or parsed.path != "/o/oauth2/v2/auth"
        ):
            return self._json_error(HTTPStatus.SERVICE_UNAVAILABLE, "service unavailable")
        return RuntimeResponse(
            status=HTTPStatus.FOUND,
            headers=(
                ("Location", location),
                ("Cache-Control", "no-store"),
            ),
        )

    def _google_callback(self, query: str, now: datetime) -> RuntimeResponse:
        parsed = parse_qs(query, keep_blank_values=True, strict_parsing=True)
        if not set(parsed).issubset(_ALLOWED_CALLBACK_QUERY_KEYS):
            return self._json_error(
                HTTPStatus.BAD_REQUEST, "unexpected query parameters"
            )
        issuer = self._one(parsed, "iss")
        if issuer is not None and issuer != "https://accounts.google.com":
            return self._json_error(
                HTTPStatus.BAD_REQUEST, "unexpected issuer"
            )
        state = self._one(parsed, "state")
        code = self._one(parsed, "code")
        if state is None or code is None:
            return self._json_error(
                HTTPStatus.BAD_REQUEST, "state and code are required"
            )

        with sqlite3.connect(self.environment.identity_database) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            store = SQLiteCentralIdentityStore(connection)
            identity = CentralIdentityService(store)
            sign_in = GoogleWebCanonicalIdentityFlow(
                oauth=self.oauth,
                identity=identity,
            ).complete(state=state, code=code, now=now)
            account = store.get_account(sign_in.user_id)

        if (
            account is None
            or not account.enabled
            or account.tenant_id != sign_in.tenant_id
        ):
            raise CentralIdentityError("canonical account is unavailable")

        issued = self.sessions.issue(
            CanonicalAccount(
                user_id=account.user_id,
                tenant_id=account.tenant_id,
                enabled=account.enabled,
            ),
            now,
            self.environment.session_lifetime,
        )
        csrf_token = secrets.token_urlsafe(32)
        max_age = int(self.environment.session_lifetime.total_seconds())
        cookie_headers = self.browser.issue_cookie_headers(
            encoded_token=issued.credential,
            session_id=issued.session_id,
            csrf_token=csrf_token,
            max_age_seconds=max_age,
        )
        return RuntimeResponse(
            status=HTTPStatus.SEE_OTHER,
            headers=(
                ("Location", "/"),
                *(("Set-Cookie", value) for value in cookie_headers),
                ("Cache-Control", "no-store"),
            ),
        )

    def _logout(self, request: RuntimeRequest, now: datetime) -> RuntimeResponse:
        web_request = self._web_request(request)
        credentials = self.browser.credentials(web_request)
        self.sessions.verify(
            credentials.session_id,
            credentials.encoded_token,
            now,
        )
        self.sessions.revoke(credentials.session_id, now)
        return RuntimeResponse(
            status=HTTPStatus.NO_CONTENT,
            headers=tuple(
                ("Set-Cookie", value)
                for value in self.browser.clear_cookie_headers()
            )
            + (("Cache-Control", "no-store"),),
        )

    def _session(self, request: RuntimeRequest, now: datetime) -> RuntimeResponse:
        credentials = self.browser.credentials(self._web_request(request))
        principal = self.sessions.verify(
            credentials.session_id,
            credentials.encoded_token,
            now,
        )
        return self._json(
            HTTPStatus.OK,
            {
                "authenticated": True,
                "user_id": principal.principal_id,
                "tenant_id": principal.tenant_id,
                "roles": sorted(principal.roles),
            },
        )

    @staticmethod
    def _one(values: Mapping[str, list[str]], key: str) -> str | None:
        candidates = values.get(key)
        if candidates is None:
            return None
        if len(candidates) != 1:
            return None
        value = candidates[0]
        return value if value else None

    def _web_request(self, request: RuntimeRequest) -> WebIdentitySessionRequest:
        cookies = self._cookies(request.headers.get("Cookie", ""))
        return WebIdentitySessionRequest(
            method=request.method,
            headers=request.headers,
            cookies=cookies,
        )

    @staticmethod
    def _cookies(raw_cookie: str) -> dict[str, str]:
        if not raw_cookie.strip():
            return {}
        cookie = SimpleCookie()
        try:
            cookie.load(raw_cookie)
        except Exception as error:
            raise WebIdentitySessionError("Cookie header is invalid") from error
        return {key: morsel.value for key, morsel in cookie.items()}

    @staticmethod
    def _method_not_allowed(allowed: str) -> RuntimeResponse:
        return AppRuntime._json_error(
            HTTPStatus.METHOD_NOT_ALLOWED,
            "method not allowed",
            extra_headers=(("Allow", allowed),),
        )

    @staticmethod
    def _authentication_denied(stage: str) -> RuntimeResponse:
        if stage not in _AUTH_FAILURE_STAGES:
            raise ValueError("authentication failure stage is invalid")
        _LOGGER.warning("app_auth_failure stage=%s", stage)
        return AppRuntime._json_error(HTTPStatus.UNAUTHORIZED, "authentication denied")

    @staticmethod
    def _json(status: HTTPStatus, payload: Mapping[str, object]) -> RuntimeResponse:
        body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return RuntimeResponse(
            status=status,
            body=body,
            headers=(
                ("Content-Type", "application/json; charset=utf-8"),
                ("Cache-Control", "no-store"),
            ),
        )

    @staticmethod
    def _json_error(
        status: HTTPStatus,
        message: str,
        *,
        extra_headers: tuple[tuple[str, str], ...] = (),
    ) -> RuntimeResponse:
        response = AppRuntime._json(status, {"error": message})
        return RuntimeResponse(
            status=response.status,
            body=response.body,
            headers=response.headers + extra_headers,
        )


class AppHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], runtime: AppRuntime) -> None:
        super().__init__(address, AppHTTPRequestHandler)
        self.runtime = runtime


class AppHTTPRequestHandler(BaseHTTPRequestHandler):
    server: AppHTTPServer

    def do_GET(self) -> None:
        self._serve("GET")

    def do_POST(self) -> None:
        self._serve("POST")

    def do_PUT(self) -> None:
        self._serve("PUT")

    def do_PATCH(self) -> None:
        self._serve("PATCH")

    def do_DELETE(self) -> None:
        self._serve("DELETE")

    def do_OPTIONS(self) -> None:
        self._serve("OPTIONS")

    def _serve(self, method: str) -> None:
        headers = {key: value for key, value in self.headers.items()}
        try:
            response = self.server.runtime.dispatch(
                RuntimeRequest(
                    method=method,
                    target=self.path,
                    headers=headers,
                    source=str(self.client_address[0]),
                )
            )
        except Exception:
            response = AppRuntime._json_error(
                HTTPStatus.SERVICE_UNAVAILABLE, "service unavailable"
            )
        self.send_response(response.status)
        emitted_content_type = False
        for key, value in response.headers:
            self.send_header(key, value)
            if key.casefold() == "content-type":
                emitted_content_type = True
        if response.body and not emitted_content_type:
            self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(response.body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'none'")
        self.end_headers()
        if response.body:
            self.wfile.write(response.body)

    def log_message(self, message_format: str, *args: object) -> None:
        return


def build_runtime(env: Mapping[str, str] | None = None) -> AppRuntime:
    """Build the production runtime from process environment."""
    return AppRuntime.from_environment(os.environ if env is None else env)


def main(argv: Sequence[str] | None = None) -> int:
    if argv:
        raise AppRuntimeConfigurationError("runtime does not accept CLI arguments")
    runtime = build_runtime()
    server = AppHTTPServer(
        (runtime.environment.host, runtime.environment.port),
        runtime,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
