"""Server-only boundary for future trusted Desktop agent evidence producers.

No production producer is registered until authenticated heartbeat and
agent-bound adapter verification are available. Client payloads are never inputs.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from services.desktop_agent_trust_evidence import LiveEvidence, AgentAdapterEvidence


class TrustedAgentEvidenceProvider(Protocol):
    """Implement only in a server-controlled authenticated integration."""
    producer_id: str

    def live(self, *, agent_id: str, now: datetime) -> LiveEvidence | None: ...

    def adapter(self, *, agent_id: str, adapter_id: str,
                now: datetime) -> AgentAdapterEvidence | None: ...


@dataclass(frozen=True)
class AgentEvidenceSnapshot:
    live: LiveEvidence | None
    adapter: AgentAdapterEvidence | None
    trusted_producers: frozenset[str]


def server_agent_evidence(*, agent_id: str, adapter_id: str, now: datetime,
                          provider: TrustedAgentEvidenceProvider | None = None,
                          approved_producers: frozenset[str] = frozenset()) -> AgentEvidenceSnapshot:
    """Fail closed until a server-approved provider supplies both records."""
    if (provider is None or not agent_id or not adapter_id
            or not provider.producer_id or provider.producer_id not in approved_producers):
        return AgentEvidenceSnapshot(None, None, frozenset())
    live = provider.live(agent_id=agent_id, now=now)
    adapter = provider.adapter(agent_id=agent_id, adapter_id=adapter_id, now=now)
    return AgentEvidenceSnapshot(live, adapter, frozenset({provider.producer_id}))
