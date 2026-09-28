"""Read-only agent lifecycle: execution authority stays with coordinator."""
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class AgentTaskState:
    execution_status: str
    terminal: bool
    connected: bool


def inspect_task(coordinator, heartbeat, *, request_id: str, agent_id: str,
                 principal_id: str, tenant_id: str, now: datetime) -> AgentTaskState:
    if not all((request_id, agent_id, principal_id, tenant_id)) or now.tzinfo is None:
        raise ValueError('authenticated task context required')
    record = coordinator.get(request_id, principal_id=principal_id, tenant_id=tenant_id)
    return AgentTaskState(record['execution_status'], record['terminal'],
                          heartbeat.live(agent_id=agent_id, now=now) is not None)
