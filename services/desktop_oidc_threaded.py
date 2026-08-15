"""Threaded loopback-safe Desktop OIDC adapter.

The Desktop identity HTTP boundary uses ``ThreadingHTTPServer``. During an OIDC
callback the base broker performs a network token exchange and JWKS verification.
The base broker consumes the one-time state before those network operations
finish. A concurrent Desktop status poll can therefore observe neither an active
flow nor a completed result and incorrectly fail the first sign-in attempt.

This adapter keeps an in-flight provider marker around that completion window so
status polling remains ``pending`` until the callback either publishes the
verified session or actually fails. Raw tokens, authorization codes, and PKCE
material remain owned by the base broker and are never exposed here.
"""

from __future__ import annotations

from datetime import datetime

import requests

from services.desktop_oidc import (
    DesktopAuthStatus,
    DesktopIdentityError,
    DesktopOIDCService as _BaseDesktopOIDCService,
    OIDCProviderConfig,
    VerifierFactory,
)


class DesktopOIDCService(_BaseDesktopOIDCService):
    """Make OIDC completion safe for concurrent loopback status polling."""

    def __init__(
        self,
        providers: tuple[OIDCProviderConfig, ...],
        *,
        request_session: requests.Session | None = None,
        verifier_factory: VerifierFactory | None = None,
    ) -> None:
        super().__init__(
            providers,
            request_session=request_session,
            verifier_factory=verifier_factory,
        )
        self._completing_states: dict[str, str] = {}

    def complete(
        self,
        state: str,
        code: str,
        now: datetime | None = None,
    ) -> DesktopAuthStatus:
        flow = self._flows.get(state)
        if flow is not None:
            self._completing_states[state] = flow.provider_id
        try:
            return super().complete(state, code, now=now)
        finally:
            self._completing_states.pop(state, None)

    def status(
        self,
        state: str,
        now: datetime | None = None,
    ) -> DesktopAuthStatus:
        try:
            return super().status(state, now=now)
        except DesktopIdentityError:
            provider_id = self._completing_states.get(state)
            if provider_id is not None:
                return DesktopAuthStatus(
                    state=state,
                    status="pending",
                    provider_id=provider_id,
                )
            # Completion can publish the verified result and clear the in-flight
            # marker in the tiny interval between the base status lookup and this
            # exception handler. Re-read exactly once before preserving the
            # original fail-closed unknown/expired behavior.
            return super().status(state, now=now)


__all__ = ["DesktopIdentityError", "DesktopOIDCService"]
