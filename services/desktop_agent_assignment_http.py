"""Desktop authenticated agent assignment admission; server-owned scope only."""
from __future__ import annotations
import secrets
from datetime import datetime, timezone
from http import HTTPStatus
from services.desktop_agent_assignment_contract import AssignmentContext, validate_assignment
from services.execution_coordinator import classify_execution_plan, ExecutionCoordinatorError


def submit_agent_assignment(handler, body: dict[str, object]) -> None:
    session = handler._authenticated_session()
    config = getattr(handler.server, 'agent_assignment', None)
    if config is None:
        handler._send_error(HTTPStatus.SERVICE_UNAVAILABLE, 'agent assignment unavailable')
        return
    if set(body) != {'agent_id', 'objective', 'explicit_confirmation'}:
        raise ValueError('assignment accepts only agent_id, objective and explicit_confirmation')
    agent = body['agent_id']
    if not isinstance(agent, str) or not agent or agent not in config['bindings']:
        handler._send_error(HTTPStatus.FORBIDDEN, 'agent unavailable')
        return
    adapter_id, capability = config['bindings'][agent]
    objective = body['objective']
    if not isinstance(objective, str) or not objective.strip() or len(objective) > 20000:
        raise ValueError('valid objective required')
    if body['explicit_confirmation'] is not True:
        raise ValueError('explicit confirmation required')
    plan = classify_execution_plan(objective.strip())
    if plan.capability_ids != (capability,):
        raise ValueError('objective does not match agent capability')
    now = datetime.now(timezone.utc)
    eligibility = config['preflight'].check(runtime=config['runtime'], db=config['db'],
        tenant=session.tenant_id, agent=agent, adapter_id=adapter_id, now=now)
    if not eligibility.eligible:
        handler._send_error(HTTPStatus.FORBIDDEN, 'agent eligibility denied')
        return
    validate_assignment(body, AssignmentContext(session.principal_id, session.tenant_id,
        agent, session.tenant_id, True, 'idle', True, agent))
    request_id = 'agentexec-' + secrets.token_hex(16)
    execution = handler.server.coordinator.prepare(request_id, objective.strip(),
        token=handler.server.bearer_token, principal_id=session.principal_id,
        tenant_id=session.tenant_id, now=now)
    actual = execution.get('plan')
    if not isinstance(actual, dict) or actual.get('capabilities') != [capability]:
        raise ExecutionCoordinatorError('actual route differs from verified agent capability')
    from services.desktop_agent_assignment_store import record_agent_assignment
    record_agent_assignment(handler.server.coordinator._database_path,
        request_id=request_id, agent_id=agent, principal_id=session.principal_id,
        tenant_id=session.tenant_id)
    if execution.get('execution_status') == 'ADMITTED' and config.get('delivery') is None:
        handler._start_execution(request_id)
    handler._send_json(HTTPStatus.CREATED, {'request_id': request_id,
        'agent_id': agent, 'execution_status': execution.get('execution_status'),
        'blocker_code': execution.get('blocker_code')})
