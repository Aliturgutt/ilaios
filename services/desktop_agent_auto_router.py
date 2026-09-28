"""Server-owned deterministic selection; never trusts a UI-selected worker.

Routing is fail-closed: no eligible or ambiguous worker means no assignment.
This module does not dispatch or execute work.
"""
from datetime import datetime
from services.execution_coordinator import classify_execution_plan


class AutomaticRoutingUnavailable(RuntimeError):
    pass


def select_agent(*, objective: str, config: dict, tenant: str, now: datetime) -> tuple[str, str]:
    if not isinstance(objective, str) or not objective.strip() or len(objective) > 20000:
        raise ValueError('valid objective required')
    if not config or config.get('delivery') is None or config.get('worker_runtime_ready') is not True:
        raise AutomaticRoutingUnavailable('verified worker delivery not configured')
    plan = classify_execution_plan(objective.strip())
    if len(plan.capability_ids) != 1:
        raise AutomaticRoutingUnavailable('multi-capability routing not yet supported')
    capability = plan.capability_ids[0]
    candidates = []
    for agent, (adapter_id, supported) in sorted(config['bindings'].items()):
        if supported != capability:
            continue
        eligible = config['preflight'].check(runtime=config['runtime'], db=config['db'],
            tenant=tenant, agent=agent, adapter_id=adapter_id, now=now)
        if eligible.eligible:
            candidates.append(agent)
    if len(candidates) != 1:
        raise AutomaticRoutingUnavailable('requires exactly one verified eligible agent')
    return candidates[0], capability
