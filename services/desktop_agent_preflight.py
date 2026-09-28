"""Combined server-side live/adapter preflight; never dispatches a task."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from services.desktop_agent_heartbeat import AgentHeartbeatStore
from services.desktop_agent_adapter_verifier import VerifiedAgentAdapterStore
from services.desktop_agent_eligibility_adapter import desktop_agent_eligibility
from services.desktop_agent_eligibility import EligibilityResult


@dataclass(frozen=True)
class AgentPreflight:
    heartbeat: AgentHeartbeatStore
    adapters: VerifiedAgentAdapterStore

    def check(self, *, runtime: object, db: Path, tenant: str, agent: str,
              adapter_id: str, now: datetime) -> EligibilityResult:
        live = self.heartbeat.live(agent_id=agent, now=now)
        adapter = self.adapters.adapter(agent_id=agent, adapter_id=adapter_id, now=now)
        return desktop_agent_eligibility(runtime=runtime, db=db, tenant=tenant,
            agent=agent, live=live, adapter=adapter, now=now,
            trusted_producers=frozenset({self.heartbeat.producer_id, self.adapters.producer_id}),
            required_adapter_id=adapter_id)
