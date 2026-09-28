"""Desktop read-only evidence adapter; never treats historical routes as live state."""
from __future__ import annotations
import sqlite3
from datetime import datetime
from pathlib import Path
from services.desktop_agent_trust_evidence import (LiveEvidence, AgentAdapterEvidence, validate_live, validate_adapter)
from services.control_plane.agent_api import canonical_agent_state
from services.desktop_agent_eligibility import EligibilityEvidence, EligibilityResult, evaluate_eligibility


def _owned_agent(db: Path, tenant: str, agent: str) -> bool:
    # SQLite URI mode=ro prevents accidental database creation or mutation.
    if not db.is_file() or not tenant or not agent:
        return False
    with sqlite3.connect(db.resolve().as_uri() + '?mode=ro', uri=True) as conn:
        return conn.execute(
            'SELECT 1 FROM web_app_agents WHERE tenant_id=? AND agent_id=? '
            'AND deleted_at IS NULL LIMIT 1', (tenant, agent)
        ).fetchone() is not None


def desktop_agent_eligibility(*, runtime, db: Path, tenant: str, agent: str,
                              live: LiveEvidence | None,
                              adapter: AgentAdapterEvidence | None,
                              now: datetime, trusted_producers: frozenset[str] = frozenset(),
                              required_adapter_id: str = "") -> EligibilityResult:
    """Resolve canonical/tenant evidence; require independent trusted live/adapter input.

    `live` and `adapter` must be supplied by trusted server providers, never HTTP
    request payloads or UI projections. Missing provider evidence denies access.
    """
    owner = None
    try:
        if _owned_agent(db, tenant, agent):
            owner = tenant
        rows = canonical_agent_state(runtime)['agents']
        record = next((row for row in rows if row['agent_id'] == agent), None)
    except (OSError, sqlite3.Error, ValueError, KeyError, TypeError):
        record = None
    record = record or {}
    live_ok = validate_live(live, agent_id=agent, now=now,
                            trusted_producers=trusted_producers)
    adapter_ok = validate_adapter(adapter, agent_id=agent,
                                  adapter_id=required_adapter_id, now=now,
                                  trusted_producers=trusted_producers)
    evidence = EligibilityEvidence(
        agent_id=agent, session_tenant=tenant, owner_tenant=owner,
        canonical_registered=bool(record),
        persisted_registered=record.get('registered') is True,
        canonical_authority_matches=record.get('authority_matches_canonical') is True,
        readiness=record.get('readiness'),
        live_agent_id=agent if live_ok else None, live_status='idle' if live_ok else None,
        live_observed_at=live.observed_at if live_ok else None,
        adapter_agent_id=agent if adapter_ok else None,
        adapter_verified=adapter_ok,
    )
    return evaluate_eligibility(evidence, now=now)
