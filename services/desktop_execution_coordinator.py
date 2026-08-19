"""Desktop execution semantics layered over the canonical coordinator.

The canonical coordinator deliberately treats positive external side-effect verbs
such as ``publish`` as high-risk scope. Natural-language negative constraints
must not be mistaken for a request to perform that side effect. This Desktop
adapter preserves the user's local-only intent while removing only narrowly
recognized negative side-effect clauses before canonical classification.

It also maps explicit Web-App/dashboard terminology into the existing canonical
Web route vocabulary without adding a second router. Generic mobile/desktop app
requests are not rewritten and remain under their existing fail-closed route.

Positive publish/upload/deploy requests are never rewritten and therefore
continue to fail closed at the canonical coordinator boundary.
"""

from __future__ import annotations

import re
from datetime import datetime

from services.execution_coordinator import ExecutionCoordinator

_NEGATED_EXTERNAL_SIDE_EFFECTS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(?:do\s+not|don't|don’t|never)\s+publish"
        r"(?:\s+(?:this|the|any)\s+(?:video|result|output|file))?"
        r"(?:\s+anywhere)?\b",
        flags=re.IGNORECASE | re.UNICODE,
    ),
    re.compile(
        r"\b(?:do\s+not|don't|don’t|never)\s+upload\s+"
        r"(?:(?:this|the|any)\s+)?(?:video|result|output|file)?"
        r"\s*(?:to\s+)?youtube\b",
        flags=re.IGNORECASE | re.UNICODE,
    ),
    re.compile(
        r"\b(?:do\s+not|don't|don’t|never)\s+post\s+"
        r"(?:(?:this|the|any)\s+)?(?:video|result|output|file)?"
        r"\s*(?:to\s+)?tiktok\b",
        flags=re.IGNORECASE | re.UNICODE,
    ),
    re.compile(
        r"\b(?:do\s+not|don't|don’t|never)\s+"
        r"(?:deploy\s+to\s+production|production\s+deploy)\b",
        flags=re.IGNORECASE | re.UNICODE,
    ),
)

_WEB_APP_ROUTE_TERMS = (
    "web app",
    "web application",
    "web uygulaması",
    "web uygulamasi",
    "dashboard",
    "admin panel",
    "management dashboard",
    "yönetim paneli",
    "yonetim paneli",
    "customer portal",
    "client portal",
    "müşteri portalı",
    "musteri portali",
)
_CANONICAL_WEB_ROUTE_TERMS = (
    "website",
    "web site",
    "web sitesi",
    "landing page",
    "internet sitesi",
)
_NON_WEB_PLATFORM_TERMS = (
    "mobile app",
    "android app",
    "ios app",
    "iphone app",
    "desktop app",
    "windows app",
    "mac app",
    "macos app",
    "mobil uygulama",
    "masaüstü uygulama",
    "masaustu uygulama",
)

_LOCAL_ONLY_REPLACEMENT = " keep the finished result local only "
_CANONICAL_WEB_ROUTE_PREFIX = "website "


def normalize_desktop_execution_objective(objective: str) -> str:
    """Normalize bounded Desktop aliases before canonical route classification.

    Negative external-side-effect clauses are rewritten narrowly. Explicit Web-App
    aliases are prefixed with the already-canonical ``website`` route term so the
    existing coordinator selects the Web Factory. No new route/authority is
    created. Mobile/desktop application objectives are never rewritten as Web.
    """

    normalized = objective
    for pattern in _NEGATED_EXTERNAL_SIDE_EFFECTS:
        normalized = pattern.sub(_LOCAL_ONLY_REPLACEMENT, normalized)
    normalized = " ".join(normalized.split())
    folded = normalized.casefold()
    has_canonical_web = any(term in folded for term in _CANONICAL_WEB_ROUTE_TERMS)
    has_web_app_alias = any(term in folded for term in _WEB_APP_ROUTE_TERMS)
    has_non_web_platform = any(term in folded for term in _NON_WEB_PLATFORM_TERMS)
    if has_web_app_alias and not has_canonical_web and not has_non_web_platform:
        normalized = _CANONICAL_WEB_ROUTE_PREFIX + normalized
    return normalized


class DesktopExecutionCoordinator(ExecutionCoordinator):
    """Canonical coordinator with Desktop-specific bounded normalization."""

    def prepare(
        self,
        request_id: str,
        objective: str,
        *,
        token: str,
        principal_id: str,
        tenant_id: str,
        now: datetime,
    ) -> dict[str, object]:
        return super().prepare(
            request_id,
            normalize_desktop_execution_objective(objective),
            token=token,
            principal_id=principal_id,
            tenant_id=tenant_id,
            now=now,
        )
