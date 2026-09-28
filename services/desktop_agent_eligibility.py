"""Desktop-only read-only agent eligibility gate.

Inputs must be independently resolved by trusted server-side providers. No
historical runtime route or UI projection is accepted as live proof.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class EligibilityEvidence:
    agent_id: str
    session_tenant: str
    owner_tenant: str | None
    canonical_registered: bool
    persisted_registered: bool
    canonical_authority_matches: bool
    readiness: str | None
    live_agent_id: str | None
    live_status: str | None
    live_observed_at: datetime | None
    adapter_agent_id: str | None
    adapter_verified: bool


@dataclass(frozen=True)
class EligibilityResult:
    eligible: bool
    reasons: tuple[str, ...]


def evaluate_eligibility(e: EligibilityEvidence, *, now: datetime,
                         max_live_age: timedelta = timedelta(seconds=30)) -> EligibilityResult:
    """Pure fail-closed evaluation; does not write state or start execution."""
    reasons: list[str] = []
    if not e.agent_id or not e.canonical_registered or not e.persisted_registered or not e.canonical_authority_matches:
        reasons.append('agent_registration_unverified')
    if not e.session_tenant or not e.owner_tenant or e.owner_tenant != e.session_tenant:
        reasons.append('tenant_ownership_unverified')
    if e.readiness != 'verified':
        reasons.append('agent_readiness_unverified')
    observed = e.live_observed_at
    if (e.live_agent_id != e.agent_id or e.live_status != 'idle'
            or observed is None or observed.tzinfo is None or now.tzinfo is None
            or max_live_age <= timedelta(0)
            or (observed is not None and observed.tzinfo is not None and now.tzinfo is not None
                and not timedelta(0) <= now - observed <= max_live_age)):
        reasons.append('fresh_live_state_unverified')
    if not e.adapter_verified or e.adapter_agent_id != e.agent_id:
        reasons.append('agent_bound_adapter_unverified')
    return EligibilityResult(not reasons, tuple(reasons))
