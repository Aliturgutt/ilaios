"""Microsoft-ready Desktop OIDC extension for the packaged Windows client.

The canonical Desktop broker remains provider-neutral. This module adds only the
Microsoft identity-platform behavior that differs materially from ordinary OIDC:

* public-client Authorization Code + S256 PKCE with ``offline_access``;
* v2 tenant-independent issuer-template validation for ``common`` / multitenant
  registrations;
* binding of the token ``tid`` claim, token issuer, and Microsoft signing-key
  issuer as required by Microsoft identity-platform guidance; and
* DPAPI-protected refresh-token persistence/rotation through the existing
  threaded Desktop credential store.

No Microsoft client secret is accepted. Raw Microsoft tokens remain adapter-owned
and are never returned to Flutter or written to logs/readiness files.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlsplit, urlunsplit
from uuid import UUID

import jwt
import requests

from services.desktop_oidc import (
    _ALLOWED_ALGORITHMS,
    _claim_text,
    _claim_time,
    _safe_provider_error_code,
    DesktopAuthStart,
    DesktopAuthStatus,
    DesktopIdentityError,
    OIDCProviderConfig,
)
from services.desktop_oidc_threaded import DesktopOIDCService as _ThreadedDesktopOIDCService
from services.identity import (
    AuthenticationBoundary,
    IdentityError,
    IdentityKind,
    IdentityPolicy,
    VerifiedOIDCClaims,
)

_MICROSOFT_PROVIDER_ID = "microsoft"
_MICROSOFT_HOST = "login.microsoftonline.com"
_TENANT_TEMPLATE = "{tenantid}"
_SESSION_LIFETIME = timedelta(hours=8)


class _MicrosoftOIDCTokenVerifier:
    def __init__(
        self,
        provider: OIDCProviderConfig,
        *,
        expected_nonce: str | None,
    ) -> None:
        self._provider = provider
        self._expected_nonce = expected_nonce
        self.verified_expires_at: datetime | None = None
        self.display_identity: str | None = None

    def verify(self, encoded_token: str) -> VerifiedOIDCClaims:
        try:
            header = jwt.get_unverified_header(encoded_token)
            algorithm = header.get("alg")
            kid = header.get("kid")
            if not isinstance(algorithm, str) or algorithm not in _ALLOWED_ALGORITHMS:
                raise DesktopIdentityError("OIDC signing algorithm is not allowed")
            if not isinstance(kid, str) or not kid.strip():
                raise DesktopIdentityError("Microsoft OIDC signing key id is required")

            jwks_client = jwt.PyJWKClient(self._provider.jwks_uri)
            key = jwks_client.get_signing_key_from_jwt(encoded_token)
            required = ["exp", "iat", "iss", "aud", "sub", "tid"]
            if self._expected_nonce is not None:
                required.append("nonce")
            claims = jwt.decode(
                encoded_token,
                key.key,
                algorithms=[algorithm],
                audience=self._provider.client_id,
                options={"verify_iss": False, "require": required},
            )
        except DesktopIdentityError:
            raise
        except Exception as error:
            raise DesktopIdentityError("Microsoft OIDC ID token verification failed") from error

        if self._expected_nonce is not None and claims.get("nonce") != self._expected_nonce:
            raise DesktopIdentityError("OIDC nonce validation failed")

        issuer = _validated_microsoft_issuer(self._provider, claims)
        _validate_microsoft_signing_key_issuer(
            jwks_client,
            kid.strip(),
            claims,
            issuer,
        )

        subject = _claim_text(claims, "sub")
        issued_at = _claim_time(claims, "iat")
        expires_at = _claim_time(claims, "exp")
        self.verified_expires_at = expires_at
        self.display_identity = _display_identity(claims)
        tenant_id = "desktop-" + hashlib.sha256(
            f"{issuer}\0{subject}".encode("utf-8")
        ).hexdigest()[:24]
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
            # Microsoft documents email/preferred_username as mutable display
            # values. They are therefore never elevated into authorization
            # attributes here.
            attributes=frozenset(),
            authentication_methods=authentication_methods,
        )


class DesktopOIDCService(_ThreadedDesktopOIDCService):
    """Thread-safe Desktop broker with Google and Microsoft persistence."""

    def __init__(
        self,
        providers: tuple[OIDCProviderConfig, ...],
        **kwargs: Any,
    ) -> None:
        for provider in providers:
            if provider.provider_id == _MICROSOFT_PROVIDER_ID:
                _validate_microsoft_provider(provider)
        super().__init__(providers, **kwargs)

    def start(
        self,
        provider_id: str,
        redirect_uri: str,
        now: datetime | None = None,
    ) -> DesktopAuthStart:
        started = super().start(provider_id, redirect_uri, now=now)
        if provider_id != _MICROSOFT_PROVIDER_ID:
            return started
        parsed = urlsplit(started.authorization_url)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        scopes = [value for value in query.get("scope", "").split() if value]
        if "offline_access" not in scopes:
            scopes.append("offline_access")
        query["scope"] = " ".join(scopes)
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
        flow = self._flows.get(state)
        if flow is None or flow.provider_id != _MICROSOFT_PROVIDER_ID:
            return super().complete(state, code, now=now)

        with self._completion_lock:
            existing = self._results.get(state)
            if existing is not None:
                return existing
            previous_error = self._completion_errors.get(state)
            if previous_error is not None:
                raise DesktopIdentityError(previous_error)

            callback_time = _utc(now)
            self._purge(callback_time)
            flow = self._flows.pop(state, None)
            if flow is None or flow.expires_at <= callback_time:
                raise DesktopIdentityError("Desktop OIDC state is invalid or expired")
            self._completing_states[state] = flow.provider_id
            self._refresh_http.clear()
            try:
                result = self._complete_microsoft_flow(flow, code, now=now)
                refresh_token = self._refresh_http.take()
                if self._credential_store is not None and refresh_token is not None:
                    self._credential_store.save(result.provider_id, refresh_token)
                self._results[state] = result
                return result
            except DesktopIdentityError as error:
                self._remember_completion_error(state, str(error))
                raise
            except IdentityError as error:
                message = f"OIDC identity validation failed: {error}"
                self._remember_completion_error(state, message)
                raise DesktopIdentityError(message) from error
            finally:
                self._refresh_http.take()
                self._completing_states.pop(state, None)

    def _complete_microsoft_flow(
        self,
        flow: Any,
        code: str,
        *,
        now: datetime | None,
    ) -> DesktopAuthStatus:
        if not code or not code.strip():
            raise DesktopIdentityError("OIDC authorization code is required")
        provider = self._providers[flow.provider_id]
        token_data = {
            "grant_type": "authorization_code",
            "client_id": provider.client_id,
            "code": code.strip(),
            "redirect_uri": flow.redirect_uri,
            "code_verifier": flow.code_verifier,
        }
        try:
            response = self._http.post(
                provider.token_endpoint,
                data=token_data,
                headers={"Accept": "application/json"},
                timeout=10,
            )
        except requests.RequestException as error:
            raise DesktopIdentityError("OIDC token exchange failed") from error
        try:
            payload = response.json()
        except ValueError as error:
            try:
                response.raise_for_status()
            except requests.RequestException as status_error:
                raise DesktopIdentityError("OIDC token exchange failed") from status_error
            raise DesktopIdentityError("OIDC token response is malformed") from error
        try:
            response.raise_for_status()
        except requests.RequestException as error:
            provider_error = _safe_provider_error_code(payload)
            detail = f": {provider_error}" if provider_error is not None else ""
            raise DesktopIdentityError(f"OIDC token exchange failed{detail}") from error
        if not isinstance(payload, dict):
            raise DesktopIdentityError("OIDC token response is malformed")
        encoded_token = payload.get("id_token")
        if not isinstance(encoded_token, str) or not encoded_token:
            raise DesktopIdentityError("OIDC token response did not contain an ID token")

        actual_issuer = _trusted_microsoft_issuer_for_token(provider, encoded_token)
        current = _utc(now)
        verifier = _MicrosoftOIDCTokenVerifier(
            provider,
            expected_nonce=flow.nonce,
        )
        principal = AuthenticationBoundary(
            verifier,
            IdentityPolicy(
                trusted_issuers=frozenset({actual_issuer}),
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
            raise DesktopIdentityError("verified OIDC token is already expired")

        session_id = secrets.token_urlsafe(32)
        session = self._session_registry.issue(
            session_id,
            principal,
            current,
            lifetime,
        )
        self._session_tenants[session.session_id] = session.tenant_id
        return DesktopAuthStatus(
            state=flow.state,
            status="authenticated",
            provider_id=provider.provider_id,
            session_id=session.session_id,
            principal_id=session.principal_id,
            tenant_id=session.tenant_id,
            display_identity=verifier.display_identity,
        )

    def _restore(self, now: datetime | None = None) -> DesktopAuthStatus | None:
        store = self._credential_store
        if store is None:
            return None
        credential = store.load()
        if credential is None:
            return None
        if credential.provider_id != _MICROSOFT_PROVIDER_ID:
            return super()._restore(now=now)

        with self._restore_lock:
            provider = self._providers.get(credential.provider_id)
            if provider is None:
                store.clear()
                return None
            token_data = {
                "grant_type": "refresh_token",
                "refresh_token": credential.refresh_token,
                "client_id": provider.client_id,
            }
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
                raise DesktopIdentityError("OIDC refresh response is malformed") from error
            if not isinstance(payload, dict):
                raise DesktopIdentityError("OIDC refresh response is malformed")
            encoded_token = payload.get("id_token")
            if not isinstance(encoded_token, str) or not encoded_token:
                store.clear()
                return None

            actual_issuer = _trusted_microsoft_issuer_for_token(provider, encoded_token)
            current = _utc(now)
            verifier = _MicrosoftOIDCTokenVerifier(provider, expected_nonce=None)
            principal = AuthenticationBoundary(
                verifier,
                IdentityPolicy(
                    trusted_issuers=frozenset({actual_issuer}),
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
            rotated = payload.get("refresh_token")
            if isinstance(rotated, str) and rotated.strip():
                store.save(provider.provider_id, rotated)
            return DesktopAuthStatus(
                state="__ilaios_restore__",
                status="authenticated",
                provider_id=provider.provider_id,
                session_id=session.session_id,
                principal_id=session.principal_id,
                tenant_id=session.tenant_id,
                display_identity=verifier.display_identity,
            )


def _validate_microsoft_provider(provider: OIDCProviderConfig) -> None:
    if provider.client_secret is not None:
        raise DesktopIdentityError(
            "Microsoft Desktop OIDC must be configured as a public client without a secret"
        )
    for name, value in (
        ("issuer", provider.issuer),
        ("authorization_endpoint", provider.authorization_endpoint),
        ("token_endpoint", provider.token_endpoint),
        ("jwks_uri", provider.jwks_uri),
    ):
        candidate = value.replace(
            _TENANT_TEMPLATE,
            "00000000-0000-0000-0000-000000000000",
        )
        parsed = urlparse(candidate)
        if parsed.scheme != "https" or parsed.hostname != _MICROSOFT_HOST:
            raise DesktopIdentityError(
                f"Microsoft Desktop OIDC {name} must use login.microsoftonline.com over HTTPS"
            )
    if provider.issuer.count(_TENANT_TEMPLATE) > 1:
        raise DesktopIdentityError("Microsoft Desktop OIDC issuer template is invalid")
    if _TENANT_TEMPLATE in provider.issuer and provider.issuer != (
        "https://login.microsoftonline.com/{tenantid}/v2.0"
    ):
        raise DesktopIdentityError("Microsoft Desktop OIDC issuer template is invalid")
    if "openid" not in provider.scopes or "profile" not in provider.scopes:
        raise DesktopIdentityError(
            "Microsoft Desktop OIDC must request openid and profile scopes"
        )


def _trusted_microsoft_issuer_for_token(
    provider: OIDCProviderConfig,
    encoded_token: str,
) -> str:
    try:
        claims = jwt.decode(
            encoded_token,
            options={
                "verify_signature": False,
                "verify_aud": False,
                "verify_exp": False,
                "verify_iat": False,
                "verify_iss": False,
            },
        )
    except Exception as error:
        raise DesktopIdentityError("Microsoft OIDC ID token is malformed") from error
    if not isinstance(claims, dict):
        raise DesktopIdentityError("Microsoft OIDC ID token is malformed")
    return _validated_microsoft_issuer(provider, claims)


def _validated_microsoft_issuer(
    provider: OIDCProviderConfig,
    claims: dict[str, Any],
) -> str:
    issuer = _claim_text(claims, "iss")
    tid = _normalized_tenant_id(claims)
    expected = provider.issuer.replace(_TENANT_TEMPLATE, tid)
    if issuer != expected:
        raise DesktopIdentityError("Microsoft OIDC tenant/issuer binding failed")
    return issuer


def _normalized_tenant_id(claims: dict[str, Any]) -> str:
    tid = _claim_text(claims, "tid")
    try:
        parsed = UUID(tid)
    except (ValueError, AttributeError) as error:
        raise DesktopIdentityError("Microsoft OIDC tid claim must be a GUID") from error
    normalized = str(parsed)
    if normalized.casefold() != tid.casefold():
        raise DesktopIdentityError("Microsoft OIDC tid claim is not canonical")
    return normalized


def _validate_microsoft_signing_key_issuer(
    client: jwt.PyJWKClient,
    kid: str,
    claims: dict[str, Any],
    token_issuer: str,
) -> None:
    try:
        document = client.fetch_data()
    except Exception as error:
        raise DesktopIdentityError("Microsoft OIDC signing-key metadata unavailable") from error
    if not isinstance(document, dict):
        raise DesktopIdentityError("Microsoft OIDC signing-key metadata is malformed")
    keys = document.get("keys")
    if not isinstance(keys, list):
        raise DesktopIdentityError("Microsoft OIDC signing-key metadata is malformed")
    matching = [
        item
        for item in keys
        if isinstance(item, dict) and item.get("kid") == kid
    ]
    if len(matching) != 1:
        raise DesktopIdentityError("Microsoft OIDC signing-key metadata is ambiguous")
    key_issuer = matching[0].get("issuer")
    if not isinstance(key_issuer, str) or not key_issuer.strip():
        raise DesktopIdentityError("Microsoft OIDC signing-key issuer is missing")
    tid = _normalized_tenant_id(claims)
    expected_key_issuer = key_issuer.strip().replace(_TENANT_TEMPLATE, tid)
    if expected_key_issuer != token_issuer:
        raise DesktopIdentityError("Microsoft OIDC signing-key issuer binding failed")


def _display_identity(claims: dict[str, Any]) -> str | None:
    for name in ("preferred_username", "name"):
        value = claims.get(name)
        if isinstance(value, str) and value.strip():
            return value.strip()[:160]
    return None


def _utc(value: datetime | None) -> datetime:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        raise DesktopIdentityError("Desktop identity timestamps must be timezone-aware")
    return current.astimezone(timezone.utc)


__all__ = ["DesktopIdentityError", "DesktopOIDCService"]
