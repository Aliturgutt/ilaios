"""Thread-safe Desktop OIDC adapter with secure Windows session restoration.

The Desktop identity HTTP boundary uses ``ThreadingHTTPServer``. During an OIDC
callback the base broker performs a network token exchange and JWKS verification.
The base broker consumes the one-time state before those network operations
finish. A concurrent Desktop status poll can therefore observe neither an active
flow nor a completed result and incorrectly fail the first sign-in attempt.

This adapter keeps an in-flight provider marker around that completion window so
status polling remains ``pending`` until the callback either publishes the
verified session or actually fails. Callback completion itself is serialized so
a duplicate browser callback cannot consume the same one-time state concurrently
or clear another callback's in-flight marker.

For the packaged Windows Desktop runtime, the adapter also requests an offline
Google refresh credential, protects it with Windows DPAPI under the current user,
and restores a fresh verified local session on later Desktop launches. Provider
refresh credentials never leave this adapter and are never exposed to Flutter,
logs, ready files, or Desktop session responses.
"""

from __future__ import annotations

import base64
import ctypes
import hashlib
import json
import os
import secrets
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import jwt
import requests

from services.desktop_oidc import (
    _ALLOWED_ALGORITHMS,
    _claim_text,
    _claim_time,
    _verified_email,
    DesktopAuthStart,
    DesktopAuthStatus,
    DesktopIdentityError,
    DesktopOIDCService as _BaseDesktopOIDCService,
    OIDCProviderConfig,
    VerifierFactory,
)
from services.identity import (
    AuthenticationBoundary,
    IdentityError,
    IdentityKind,
    IdentityPolicy,
    VerifiedOIDCClaims,
)

_RESTORE_STATE = "__ilaios_restore__"
_SESSION_LIFETIME = timedelta(hours=8)
_CRYPTPROTECT_UI_FORBIDDEN = 0x1


@dataclass(frozen=True, slots=True)
class _StoredRefreshCredential:
    provider_id: str
    refresh_token: str


class _CredentialStore(Protocol):
    def load(self) -> _StoredRefreshCredential | None: ...

    def save(self, provider_id: str, refresh_token: str) -> None: ...

    def clear(self) -> None: ...


class _DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", ctypes.c_uint32),
        ("pbData", ctypes.POINTER(ctypes.c_ubyte)),
    ]


def _windows_dpapi_libraries() -> tuple[Any, Any]:
    if os.name != "nt":
        raise DesktopIdentityError("Desktop persistent identity requires Windows DPAPI")
    windll = getattr(ctypes, "windll", None)
    if windll is None:
        raise DesktopIdentityError("Windows DPAPI is unavailable")
    return windll.crypt32, windll.kernel32


def _dpapi_protect(value: bytes) -> bytes:
    crypt32, kernel32 = _windows_dpapi_libraries()
    source_buffer = ctypes.create_string_buffer(value)
    source = _DATA_BLOB(
        len(value),
        ctypes.cast(source_buffer, ctypes.POINTER(ctypes.c_ubyte)),
    )
    result = _DATA_BLOB()
    if not crypt32.CryptProtectData(
        ctypes.byref(source),
        "ILAIOS Desktop identity",
        None,
        None,
        None,
        _CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(result),
    ):
        raise DesktopIdentityError("Windows DPAPI protection failed")
    try:
        return ctypes.string_at(result.pbData, result.cbData)
    finally:
        kernel32.LocalFree(result.pbData)


def _dpapi_unprotect(value: bytes) -> bytes:
    crypt32, kernel32 = _windows_dpapi_libraries()
    source_buffer = ctypes.create_string_buffer(value)
    source = _DATA_BLOB(
        len(value),
        ctypes.cast(source_buffer, ctypes.POINTER(ctypes.c_ubyte)),
    )
    result = _DATA_BLOB()
    if not crypt32.CryptUnprotectData(
        ctypes.byref(source),
        None,
        None,
        None,
        None,
        _CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(result),
    ):
        raise DesktopIdentityError("Windows DPAPI unprotection failed")
    try:
        return ctypes.string_at(result.pbData, result.cbData)
    finally:
        kernel32.LocalFree(result.pbData)


class _RefreshCredentialStore:
    def __init__(
        self,
        path: Path,
        *,
        protect: Any = _dpapi_protect,
        unprotect: Any = _dpapi_unprotect,
    ) -> None:
        self._path = path
        self._protect = protect
        self._unprotect = unprotect

    def load(self) -> _StoredRefreshCredential | None:
        if not self._path.exists():
            return None
        try:
            document = json.loads(self._path.read_text(encoding="utf-8"))
            if not isinstance(document, dict) or document.get("version") != 1:
                raise ValueError("unsupported persistent identity record")
            provider_id = document.get("provider_id")
            protected = document.get("protected_refresh_token")
            if not isinstance(provider_id, str) or not provider_id.strip():
                raise ValueError("persistent identity provider is invalid")
            if not isinstance(protected, str) or not protected:
                raise ValueError("persistent identity credential is invalid")
            decoded = base64.b64decode(protected, validate=True)
            token = self._unprotect(decoded).decode("utf-8")
            if not token:
                raise ValueError("persistent identity credential is empty")
            return _StoredRefreshCredential(provider_id.strip(), token)
        except Exception as error:
            self.clear()
            raise DesktopIdentityError(
                "Desktop persistent identity could not be restored"
            ) from error

    def save(self, provider_id: str, refresh_token: str) -> None:
        normalized_provider = provider_id.strip()
        normalized_token = refresh_token.strip()
        if not normalized_provider or not normalized_token:
            raise DesktopIdentityError(
                "Desktop persistent identity credential is invalid"
            )
        self._path.parent.mkdir(parents=True, exist_ok=True)
        protected = base64.b64encode(
            self._protect(normalized_token.encode("utf-8"))
        ).decode("ascii")
        document = json.dumps(
            {
                "version": 1,
                "provider_id": normalized_provider,
                "protected_refresh_token": protected,
            },
            sort_keys=True,
        )
        temporary = self._path.with_suffix(self._path.suffix + ".tmp")
        temporary.write_text(document, encoding="utf-8")
        os.replace(temporary, self._path)

    def clear(self) -> None:
        self._path.unlink(missing_ok=True)


class _RefreshCaptureHTTP:
    def __init__(self, inner: requests.Session) -> None:
        self._inner = inner
        self._captured_refresh_token: str | None = None

    def clear(self) -> None:
        self._captured_refresh_token = None

    def take(self) -> str | None:
        value = self._captured_refresh_token
        self._captured_refresh_token = None
        return value

    def post(self, url: str, **kwargs: Any) -> requests.Response:
        response = self._inner.post(url, **kwargs)
        data = kwargs.get("data")
        if isinstance(data, dict) and data.get("grant_type") == "authorization_code":
            try:
                payload = response.json()
            except ValueError:
                payload = None
            if isinstance(payload, dict):
                refresh_token = payload.get("refresh_token")
                if isinstance(refresh_token, str) and refresh_token.strip():
                    self._captured_refresh_token = refresh_token.strip()
        return response


class _RefreshOIDCTokenVerifier:
    def __init__(self, provider: OIDCProviderConfig) -> None:
        self._provider = provider
        self.verified_expires_at: datetime | None = None

    def verify(self, encoded_token: str) -> VerifiedOIDCClaims:
        try:
            header = jwt.get_unverified_header(encoded_token)
            algorithm = header.get("alg")
            if not isinstance(algorithm, str) or algorithm not in _ALLOWED_ALGORITHMS:
                raise DesktopIdentityError("OIDC signing algorithm is not allowed")
            key = jwt.PyJWKClient(self._provider.jwks_uri).get_signing_key_from_jwt(
                encoded_token
            )
            claims = jwt.decode(
                encoded_token,
                key.key,
                algorithms=[algorithm],
                audience=self._provider.client_id,
                issuer=self._provider.issuer,
                options={"require": ["exp", "iat", "iss", "aud", "sub"]},
            )
        except DesktopIdentityError:
            raise
        except Exception as error:
            raise DesktopIdentityError("OIDC ID token verification failed") from error

        subject = _claim_text(claims, "sub")
        issuer = _claim_text(claims, "iss")
        issued_at = _claim_time(claims, "iat")
        expires_at = _claim_time(claims, "exp")
        self.verified_expires_at = expires_at
        tenant_id = "desktop-" + hashlib.sha256(
            f"{issuer}\0{subject}".encode("utf-8")
        ).hexdigest()[:24]
        attributes: set[tuple[str, str]] = set()
        email = claims.get("email")
        if isinstance(email, str) and claims.get("email_verified") is True:
            attributes.add(("verified_email", email.strip().casefold()))
        methods = claims.get("amr", [])
        authentication_methods = (
            frozenset(
                value for value in methods if isinstance(value, str) and value.strip()
            )
            if isinstance(methods, list)
            else frozenset()
        )
        return VerifiedOIDCClaims(
            issuer=issuer,
            audience=self._provider.client_id,
            subject=subject,
            tenant_id=tenant_id,
            expires_at=expires_at,
            issued_at=issued_at,
            kind=IdentityKind.HUMAN,
            roles=frozenset({"user"}),
            attributes=frozenset(attributes),
            authentication_methods=authentication_methods,
        )


class DesktopOIDCService(_BaseDesktopOIDCService):
    """Thread-safe OIDC completion plus Windows-protected session restoration."""

    def __init__(
        self,
        providers: tuple[OIDCProviderConfig, ...],
        *,
        request_session: requests.Session | None = None,
        verifier_factory: VerifierFactory | None = None,
        credential_store: _CredentialStore | None = None,
    ) -> None:
        inner_http = request_session or requests.Session()
        self._refresh_http = _RefreshCaptureHTTP(inner_http)
        super().__init__(
            providers,
            request_session=self._refresh_http,  # type: ignore[arg-type]
            verifier_factory=verifier_factory,
        )
        self._completing_states: dict[str, str] = {}
        self._completion_errors: dict[str, str] = {}
        self._completion_lock = threading.Lock()
        self._restore_lock = threading.Lock()
        self._credential_store: _CredentialStore | None = (
            credential_store if credential_store is not None else _default_credential_store()
        )

    def start(
        self,
        provider_id: str,
        redirect_uri: str,
        now: datetime | None = None,
    ) -> DesktopAuthStart:
        started = super().start(provider_id, redirect_uri, now=now)
        if provider_id != "google":
            return started
        parsed = urlsplit(started.authorization_url)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query["access_type"] = "offline"
        query["prompt"] = "consent"
        query["include_granted_scopes"] = "true"
        authorization_url = urlunsplit(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                urlencode(query),
                parsed.fragment,
            )
        )
        return DesktopAuthStart(
            provider_id=started.provider_id,
            state=started.state,
            authorization_url=authorization_url,
            expires_at=started.expires_at,
        )

    def complete(
        self,
        state: str,
        code: str,
        now: datetime | None = None,
    ) -> DesktopAuthStatus:
        with self._completion_lock:
            existing = self._results.get(state)
            if existing is not None:
                return existing

            previous_error = self._completion_errors.get(state)
            if previous_error is not None:
                raise DesktopIdentityError(previous_error)

            flow = self._flows.get(state)
            owns_marker = flow is not None
            if flow is not None:
                self._completing_states[state] = flow.provider_id
            self._refresh_http.clear()
            try:
                result = super().complete(state, code, now=now)
                refresh_token = self._refresh_http.take()
                if (
                    self._credential_store is not None
                    and result.provider_id == "google"
                    and refresh_token is not None
                ):
                    self._credential_store.save(result.provider_id, refresh_token)
                return result
            except DesktopIdentityError as error:
                if owns_marker:
                    self._remember_completion_error(state, str(error))
                raise
            except IdentityError as error:
                message = f"OIDC identity validation failed: {error}"
                if owns_marker:
                    self._remember_completion_error(state, message)
                raise DesktopIdentityError(message) from error
            finally:
                self._refresh_http.take()
                if owns_marker:
                    self._completing_states.pop(state, None)

    def status(
        self,
        state: str,
        now: datetime | None = None,
    ) -> DesktopAuthStatus:
        if state == _RESTORE_STATE:
            restored = self._restore(now=now)
            if restored is not None:
                return restored
            fallback_provider_id = next(iter(sorted(self._providers)), "google")
            return DesktopAuthStatus(
                state=_RESTORE_STATE,
                status="pending",
                provider_id=fallback_provider_id,
            )
        try:
            return super().status(state, now=now)
        except DesktopIdentityError:
            pending_provider_id = self._completing_states.get(state)
            if pending_provider_id is not None:
                return DesktopAuthStatus(
                    state=state,
                    status="pending",
                    provider_id=pending_provider_id,
                )
            completion_error = self._completion_errors.get(state)
            if completion_error is not None:
                raise DesktopIdentityError(completion_error)
            return super().status(state, now=now)

    def logout(self, session_id: str) -> None:
        super().logout(session_id)
        if self._credential_store is not None:
            self._credential_store.clear()

    def _restore(self, now: datetime | None = None) -> DesktopAuthStatus | None:
        store = self._credential_store
        if store is None:
            return None
        with self._restore_lock:
            credential = store.load()
            if credential is None:
                return None
            provider = self._providers.get(credential.provider_id)
            if provider is None:
                store.clear()
                return None
            token_data = {
                "grant_type": "refresh_token",
                "refresh_token": credential.refresh_token,
                "client_id": provider.client_id,
            }
            if provider.client_secret is not None:
                token_data["client_secret"] = provider.client_secret
            try:
                response = self._http.post(
                    provider.token_endpoint,
                    data=token_data,
                    headers={"Accept": "application/json"},
                    timeout=10,
                )
                payload = response.json()
                response.raise_for_status()
            except requests.RequestException as error:
                response_object = getattr(error, "response", None)
                status_code = getattr(response_object, "status_code", None)
                if status_code in {400, 401}:
                    store.clear()
                    return None
                raise DesktopIdentityError("OIDC refresh exchange failed") from error
            except ValueError as error:
                raise DesktopIdentityError(
                    "OIDC refresh response is malformed"
                ) from error
            if not isinstance(payload, dict):
                raise DesktopIdentityError("OIDC refresh response is malformed")
            encoded_token = payload.get("id_token")
            if not isinstance(encoded_token, str) or not encoded_token:
                store.clear()
                return None

            current = _utc_now(now)
            verifier = _RefreshOIDCTokenVerifier(provider)
            principal = AuthenticationBoundary(
                verifier,
                IdentityPolicy(
                    trusted_issuers=frozenset({provider.issuer}),
                    audience=provider.client_id,
                    maximum_session=_SESSION_LIFETIME,
                ),
            ).authenticate(encoded_token, current)
            principal = self._canonicalize_principal(
                provider.provider_id,
                encoded_token,
                principal,
                current,
            )
            verified_expiry = verifier.verified_expires_at
            if not isinstance(verified_expiry, datetime):
                raise DesktopIdentityError(
                    "OIDC verifier did not bind the local session to token expiry"
                )
            remaining = verified_expiry.astimezone(timezone.utc) - current
            lifetime = min(_SESSION_LIFETIME, remaining)
            if lifetime <= timedelta(0):
                store.clear()
                return None

            session_id = secrets.token_urlsafe(32)
            session = self._session_registry.issue(
                session_id,
                principal,
                current,
                lifetime,
            )
            self._session_tenants[session.session_id] = session.tenant_id
            self._bind_session_entitlements(session.session_id, principal)
            self._bind_session_identity_credential(
                session.session_id,
                provider.provider_id,
                encoded_token,
            )
            rotated = payload.get("refresh_token")
            if isinstance(rotated, str) and rotated.strip():
                store.save(provider.provider_id, rotated)
            return DesktopAuthStatus(
                state=_RESTORE_STATE,
                status="authenticated",
                provider_id=provider.provider_id,
                session_id=session.session_id,
                principal_id=session.principal_id,
                tenant_id=session.tenant_id,
                display_identity=_verified_email(principal),
                li_founder=self._session_li_founder.get(session.session_id, False),
            )

    def _remember_completion_error(self, state: str, message: str) -> None:
        self._completion_errors[state] = message
        if len(self._completion_errors) > 100:
            oldest = next(iter(self._completion_errors))
            if oldest != state:
                self._completion_errors.pop(oldest, None)


def _utc_now(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _default_credential_store() -> _RefreshCredentialStore | None:
    if os.name != "nt" or not os.environ.get(
        "ILAIOS_CONTROL_PLANE_TOKEN", ""
    ).strip():
        return None
    local_app_data = os.environ.get("LOCALAPPDATA", "").strip()
    if not local_app_data:
        return None
    path = Path(local_app_data) / "ILAIOS" / "identity" / "refresh-credential.json"
    return _RefreshCredentialStore(path)


__all__ = ["DesktopIdentityError", "DesktopOIDCService"]
