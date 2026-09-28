"""Server-side agent-bound adapter verification, independent of heartbeat.

Only an injected server-controlled verifier may attest adapter identity.
"""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Protocol
from services.desktop_agent_trust_evidence import AgentAdapterEvidence


class ServerAdapterVerifier(Protocol):
    def verify(self, *, agent_id: str, adapter_id: str) -> bool: ...


class VerifiedAgentAdapterStore:
    def __init__(self, bindings: dict[str, str], verifier: ServerAdapterVerifier | None,
                 *, producer_id: str = 'desktop-server-adapter-verifier'):
        if not producer_id:
            raise ValueError('producer identity required')
        self._bindings = dict(bindings)
        self._verifier = verifier
        self.producer_id = producer_id

    def adapter(self, *, agent_id: str, adapter_id: str,
                now: datetime) -> AgentAdapterEvidence | None:
        if (now.tzinfo is None or not agent_id or not adapter_id
                or self._bindings.get(agent_id) != adapter_id or self._verifier is None):
            return None
        try:
            if self._verifier.verify(agent_id=agent_id, adapter_id=adapter_id) is not True:
                return None
        except Exception:
            return None
        return AgentAdapterEvidence(agent_id, adapter_id, self.producer_id,
                                    now, now + timedelta(minutes=5), True, True)
