import pytest
from services.desktop_agent_assignment_contract import (
    AssignmentContext, AssignmentRejected, validate_assignment,
)

BASE = dict(session_principal='user', session_tenant='tenant-a',
            agent_id='agent-1', agent_tenant='tenant-a', registered=True,
            live_status='idle', accepts_tasks=True,
            verified_adapter_agent_id='agent-1')
BODY = {'objective': 'Perform verified Desktop task', 'explicit_confirmation': True}

@pytest.mark.parametrize('override', [
    {'session_principal': ''}, {'session_tenant': ''},
    {'agent_tenant': 'tenant-b'}, {'registered': False},
    {'live_status': 'offline'}, {'live_status': 'busy'},
    {'accepts_tasks': False}, {'verified_adapter_agent_id': None},
    {'verified_adapter_agent_id': 'another-agent'},
])
def test_fail_closed_for_missing_authority_or_readiness(override):
    with pytest.raises(AssignmentRejected):
        validate_assignment(BODY, AssignmentContext(**(BASE | override)))

@pytest.mark.parametrize('body', [
    {'objective': 'task'}, {'objective': 'task', 'explicit_confirmation': False},
    {'objective': ' ', 'explicit_confirmation': True},
    {'objective': 7, 'explicit_confirmation': True},
    {'objective': 'x' * 20001, 'explicit_confirmation': True},
])
def test_invalid_requests_rejected(body):
    with pytest.raises(AssignmentRejected):
        validate_assignment(body, AssignmentContext(**BASE))

def test_validated_request_has_no_execution_side_effect():
    assert validate_assignment(BODY, AssignmentContext(**BASE)) == BODY['objective']
