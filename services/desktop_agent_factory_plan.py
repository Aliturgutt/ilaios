"""Shared, side-effect-free factory routing plan; execution is a separate gate.

A plan is not a delivery receipt or authorization to execute. Every selected
capability must have exactly one tenant-eligible, verified worker; otherwise
no partial plan is returned. Dependencies follow the canonical coordinator.
"""
from dataclasses import dataclass
from datetime import datetime
from services.desktop_agent_auto_router import AutomaticRoutingUnavailable
from services.execution_coordinator import classify_execution_plan, _dependency_order


@dataclass(frozen=True)
class FactoryAssignment:
    capability_id: str
    agent_id: str
    adapter_id: str


def plan_factory_assignments(*, objective: str, config: dict, tenant: str,
                             now: datetime) -> tuple[FactoryAssignment, ...]:
    if not isinstance(objective, str) or not objective.strip() or len(objective) > 20000:
        raise ValueError('valid objective required')
    if (now.tzinfo is None or not tenant or not config
            or config.get('delivery') is None
            or config.get('worker_runtime_ready') is not True):
        raise AutomaticRoutingUnavailable('verified delivery not configured')
    selected = _dependency_order(classify_execution_plan(objective.strip()).capability_ids)
    if not selected:
        raise AutomaticRoutingUnavailable('no factory selected')
    assignments = []
    for capability in selected:
        eligible_agents = []
        for agent, (adapter, supported) in sorted(config['bindings'].items()):
            if supported != capability:
                continue
            evidence = config['preflight'].check(runtime=config['runtime'],
                db=config['db'], tenant=tenant, agent=agent,
                adapter_id=adapter, now=now)
            if evidence.eligible is True:
                eligible_agents.append(FactoryAssignment(capability, agent, adapter))
        if len(eligible_agents) != 1:
            raise AutomaticRoutingUnavailable(
                'factory has missing or ambiguous verified worker: ' + capability)
        assignments.extend(eligible_agents)
    return tuple(assignments)
