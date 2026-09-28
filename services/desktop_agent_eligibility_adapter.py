"""Desktop read-only evidence adapter; never treats historical routes as live state."""
from __future__ import annotations
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Mapping
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
                              live: Mapping[str, object] | None,
                              adapter: Mapping[str, object] | None,
                              now: datetime) -> EligibilityResult:
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
    live = live or {}
    adapter = adapter or {}
    evidence = EligibilityEvidence(
        agent_id=agent, session_tenant=tenant, owner_tenant=owner,
        canonical_registered=bool(record),
        persisted_registered=record.get('registered') is True,
        canonical_authority_matches=record.get('authority_matches_canonical') is True,
        readiness=record.get('readiness'),
        live_agent_id=live.get('agent_id'), live_status=live.get('status'),
        live_observed_at=live.get('observed_at'),
        adapter_agent_id=adapter.get('agent_id'),
        adapter_verified=adapter.get('verified') is True,
    )
    return evaluate_eligibility(evidence, now=now)
