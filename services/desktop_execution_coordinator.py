"""Desktop execution semantics layered over the canonical coordinator.

The canonical coordinator deliberately treats positive external side-effect verbs
such as ``publish`` as high-risk scope. Natural-language negative constraints
must not be mistaken for a request to perform that side effect. This Desktop
adapter preserves the user's local-only intent while removing only narrowly
recognized negative side-effect clauses before canonical classification.

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

_LOCAL_ONLY_REPLACEMENT = " keep the finished result local only "


def normalize_desktop_execution_objective(objective: str) -> str:
    """Rewrite only explicit negative external-side-effect clauses.

    This is intentionally narrow. Any ambiguous or positive mutation language is
    left untouched so the canonical coordinator continues to block it.
    """

    normalized = objective
    for pattern in _NEGATED_EXTERNAL_SIDE_EFFECTS:
        normalized = pattern.sub(_LOCAL_ONLY_REPLACEMENT, normalized)
    return " ".join(normalized.split())


class DesktopExecutionCoordinator(ExecutionCoordinator):
    """Canonical coordinator with Desktop-specific negation normalization."""

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
