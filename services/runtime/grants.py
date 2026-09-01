"""Scoped execution grants, revocation, budgets, and kill switches."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


class GrantError(PermissionError):
    """Raised when work lacks a valid execution grant."""


@dataclass(frozen=True, slots=True)
class BlastRadiusBudget:
    max_side_effects: int
    max_resources: int

    def __post_init__(self) -> None:
        if self.max_side_effects < 0 or self.max_resources < 0:
            raise GrantError("blast-radius limits cannot be negative")


@dataclass(frozen=True, slots=True)
class ExecutionGrant:
    grant_id: str
    subject_id: str
    actions: frozenset[str]
    resources: frozenset[str]
    expires_at: datetime
    budget: BlastRadiusBudget


class GrantPolicy:
    """Fail-closed grant policy; stopped subjects require explicit reset."""

    def __init__(self) -> None:
        self._revoked: set[str] = set()
        self._stopped: set[str] = set()
        self._side_effects: dict[str, int] = {}
        self._resources: dict[str, set[str]] = {}

    def authorize(
        self,
        grant: ExecutionGrant,
        *,
        subject_id: str,
        action: str,
        resource: str,
        now: datetime,
    ) -> None:
        if grant.grant_id in self._revoked:
            raise GrantError("grant is revoked")
        if subject_id in self._stopped:
            raise GrantError("subject is stopped")
        if grant.subject_id != subject_id:
            raise GrantError("grant subject mismatch")
        if now.tzinfo is None or grant.expires_at.tzinfo is None:
            raise GrantError("grant times must be timezone-aware")
        if now >= grant.expires_at:
            raise GrantError("grant is expired")
        if action not in grant.actions or resource not in grant.resources:
            raise GrantError("action or resource is outside grant scope")
        used_effects = self._side_effects.get(grant.grant_id, 0)
        used_resources = self._resources.get(grant.grant_id, set())
        if used_effects >= grant.budget.max_side_effects:
            raise GrantError("side-effect budget exhausted")
        if resource not in used_resources and len(used_resources) >= grant.budget.max_resources:
            raise GrantError("resource budget exhausted")

    def record_side_effect(self, grant: ExecutionGrant, resource: str) -> None:
        self._side_effects[grant.grant_id] = self._side_effects.get(grant.grant_id, 0) + 1
        self._resources.setdefault(grant.grant_id, set()).add(resource)

    def revoke(self, grant_id: str) -> None:
        self._revoked.add(grant_id)

    def kill(self, subject_id: str) -> None:
        self._stopped.add(subject_id)

    def reset_stopped_subject(self, subject_id: str, *, human_approved: bool) -> None:
        if not human_approved:
            raise GrantError("stopped work requires explicit human approval")
        self._stopped.discard(subject_id)
