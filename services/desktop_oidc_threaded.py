"""Threaded loopback-safe Desktop OIDC adapter.

The Desktop identity HTTP boundary uses ``ThreadingHTTPServer``. During an OIDC
callback the base broker performs a network token exchange and JWKS verification.
The base broker consumes the one-time state before those network operations
finish. A concurrent Desktop status poll can therefore observe neither an active
flow nor a completed result and incorrectly fail the first sign-in attempt.

This adapter keeps an in-flight provider marker around that completion window so
status polling remains ``pending`` until the callback either publishes the
verified session or actually fails. Callback completion itself is serialized so
a duplicate browser callback cannot consume the same one-time state concurrently
or clear another callback's in-flight marker. If the first callback fails after
consuming the one-time state, the original safe Desktop identity error is retained
for duplicate callbacks and status polling instead of being masked as
``state invalid or expired``. Raw tokens, authorization codes, and PKCE material
remain owned by the base broker and are never exposed here.
"""

from __future__ import annotations

import threading
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
    """Make OIDC completion safe for concurrent loopback callbacks and polling."""

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
        self._completion_errors: dict[str, str] = {}
        self._completion_lock = threading.Lock()

    def complete(
        self,
        state: str,
        code: str,
        now: datetime | None = None,
    ) -> DesktopAuthStatus:
        # Loopback callbacks can be delivered more than once. Serialize callback
        # completion so a duplicate request cannot enter the base broker after
        # the first request has consumed the state but before it has published
        # the authenticated result.
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
            try:
                return super().complete(state, code, now=now)
            except DesktopIdentityError as error:
                # The base broker consumes state before token/JWKS work. If that
                # work fails, a repeated callback would otherwise surface only
                # "state invalid or expired" and hide the actual first failure.
                # Persist only the already-sanitized boundary message.
                if owns_marker:
                    self._completion_errors[state] = str(error)
                    if len(self._completion_errors) > 100:
                        oldest = next(iter(self._completion_errors))
                        if oldest != state:
                            self._completion_errors.pop(oldest, None)
                raise
            finally:
                # Only the callback that installed the marker may remove it.
                # Otherwise a duplicate callback can erase the first callback's
                # marker and make concurrent polling fail as unknown/expired.
                if owns_marker:
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
            completion_error = self._completion_errors.get(state)
            if completion_error is not None:
                raise DesktopIdentityError(completion_error)
            # Completion can publish the verified result and clear the in-flight
            # marker in the tiny interval between the base status lookup and this
            # exception handler. Re-read exactly once before preserving the
            # original fail-closed unknown/expired behavior.
            return super().status(state, now=now)


__all__ = ["DesktopIdentityError", "DesktopOIDCService"]
