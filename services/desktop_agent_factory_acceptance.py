"""Fail-closed, factory-specific acceptance reconciliation.

Receipts and coordinator ACCEPTED states alone never certify a factory.
Each capability needs a server-provisioned, distinct product verifier that
attests the exact worker artifact digest. This module never calls _accept.
"""
import hashlib
import json
import sqlite3
from services.desktop_agent_factory_coordinator_binding import inspect_factory_execution


def inspect_factory_acceptance(coordinator, *, request_id, principal_id,
                               tenant_id, verifiers):
    db = coordinator._database_path
    plan = inspect_factory_execution(db, request_id=request_id,
        principal_id=principal_id, tenant_id=tenant_id)
    steps = plan.get('steps', ())
    if not steps or plan.get('parent_status') not in ('ADMITTED', 'ACCEPTED'):
        raise PermissionError('factory coordinator plan unavailable')
    if not isinstance(verifiers, dict) or any(
            not callable(verifiers.get(step['capability_id'])) for step in steps):
        raise PermissionError('factory-specific verifier unavailable')
    accepted = []
    with sqlite3.connect(db, timeout=10) as conn:
        for step in steps:
            child_id = step['child_request_id']
            state = coordinator.get(child_id, principal_id=principal_id,
                                    tenant_id=tenant_id)
            if state['execution_status'] != 'ACCEPTED':
                raise PermissionError('child coordinator has not accepted product')
            row = conn.execute('SELECT d.agent_id,r.payload,a.sha256,a.content '
                'FROM desktop_agent_assignments d JOIN desktop_agent_result_receipts r '
                'ON r.request_id=d.request_id AND r.agent_id=d.agent_id '
                'JOIN desktop_agent_artifacts a ON a.request_id=d.request_id '
                'WHERE d.request_id=? AND d.agent_id=? AND d.principal_id=? '
                'AND d.tenant_id=?',
                (child_id, step['agent_id'], principal_id, tenant_id)).fetchone()
            if not row or hashlib.sha256(row[3]).hexdigest() != row[2]:
                raise PermissionError('bound factory artifact missing or corrupt')
            receipt = json.loads(row[1])
            if receipt.get('status') != 'completed' or receipt.get('artifact_sha256') != row[2]:
                raise PermissionError('factory receipt mismatch')
            evidence = verifiers[step['capability_id']](coordinator=coordinator,
                request_id=child_id, agent_id=step['agent_id'],
                principal_id=principal_id, tenant_id=tenant_id,
                artifact_sha256=row[2])
            if (not isinstance(evidence, dict) or evidence.get('verified') is not True
                    or evidence.get('artifact_sha256') != row[2]
                    or evidence.get('agent_id') != step['agent_id']):
                raise PermissionError('factory product verifier rejected artifact')
            accepted.append({'capability_id': step['capability_id'],
                'request_id': child_id, 'agent_id': step['agent_id'],
                'artifact_sha256': row[2]})
    return {'verified': True, 'factory_results': tuple(accepted),
            'parent_coordinator_accepted': plan['parent_status'] == 'ACCEPTED'}
