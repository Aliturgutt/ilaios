"""Desktop-only preflight contract; never creates or dispatches tasks.

Future POST /v1/agents/{agent_id}/assignments accepts objective and
explicit_confirmation=true under authenticated Desktop transport/session.
This gate is intentionally fail-closed until a verified agent-bound adapter
and tenant-scoped live agent state are supplied by a trusted Desktop caller.
"""
from dataclasses import dataclass


class AssignmentRejected(ValueError):
    pass


@dataclass(frozen=True)
class AssignmentContext:
    session_principal: str
    session_tenant: str
    agent_id: str
    agent_tenant: str
    registered: bool
    live_status: str
    accepts_tasks: bool
    verified_adapter_agent_id: str | None


def validate_assignment(body: dict[str, object], context: AssignmentContext) -> str:
    """Return validated objective only; no execution side effects."""
    if not context.session_principal or not context.session_tenant:
        raise AssignmentRejected('authenticated Desktop session required')
    if not context.agent_id or context.agent_tenant != context.session_tenant:
        raise AssignmentRejected('agent is not available in this tenant')
    if not context.registered:
        raise AssignmentRejected('registered agent required')
    if context.live_status not in {'idle', 'ready'} or not context.accepts_tasks:
        raise AssignmentRejected('agent cannot accept tasks')
    if body.get('explicit_confirmation') is not True:
        raise AssignmentRejected('explicit user confirmation required')
    if context.verified_adapter_agent_id != context.agent_id:
        raise AssignmentRejected('verified agent-bound execution adapter required')
    objective = body.get('objective')
    if not isinstance(objective, str) or not objective.strip() or len(objective) > 20000:
        raise AssignmentRejected('valid objective required')
    return objective.strip()
