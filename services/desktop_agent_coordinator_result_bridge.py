"""Read-only reconciliation with coordinator's independent acceptance evidence.

Never calls coordinator._accept or resumes a different local adapter as the agent.
"""
import hashlib
import json
import sqlite3


def reconcile_verified_result(coordinator, *, request_id, principal_id, tenant_id):
    state = coordinator.get(request_id, principal_id=principal_id, tenant_id=tenant_id)
    if state['execution_status'] != 'ACCEPTED':
        return {'verified': False, 'reason': 'coordinator_not_accepted'}
    with sqlite3.connect(coordinator._database_path, timeout=10) as conn:
        row = conn.execute('SELECT r.agent_id, r.payload, a.sha256, a.content '
            'FROM desktop_agent_result_receipts r JOIN desktop_agent_artifacts a '
            'ON a.request_id=r.request_id JOIN desktop_agent_assignments d '
            'ON d.request_id=r.request_id AND d.agent_id=r.agent_id '
            'AND d.principal_id=? AND d.tenant_id=? WHERE r.request_id=?',
            (principal_id, tenant_id, request_id)).fetchone()
    if not row:
        return {'verified': False, 'reason': 'verified_worker_artifact_missing'}
    if hashlib.sha256(row[3]).hexdigest() != row[2]:
        return {'verified': False, 'reason': 'stored_artifact_corrupt'}
    receipt = json.loads(row[1])
    manifest = state.get('result')
    if (not isinstance(manifest, dict) or manifest.get('accepted') is not True
            or receipt.get('status') != 'completed'
            or receipt.get('artifact_sha256') != row[2]
            or manifest.get('artifact_digest') != row[2]
            or manifest.get('delivery_sha256') != row[2]):
        return {'verified': False, 'reason': 'coordinator_evidence_mismatch'}
    return {'verified': True, 'agent_id': row[0], 'artifact_sha256': row[2]}


def inspect_worker_acceptance_readiness(coordinator, *, request_id, principal_id, tenant_id):
    """Fail-closed gate for a future verified agent execution adapter.

    A worker receipt cannot be promoted via the coordinator's private _accept;
    that transition requires product-specific adapter verification and grants.
    """
    state = coordinator.get(request_id, principal_id=principal_id, tenant_id=tenant_id)
    if state['execution_status'] != 'ADMITTED':
        return {'ready': False, 'reason': 'coordinator_not_admitted'}
    with sqlite3.connect(coordinator._database_path, timeout=10) as conn:
        row = conn.execute('SELECT r.agent_id,r.payload,a.sha256,a.content '
            'FROM desktop_agent_result_receipts r JOIN desktop_agent_artifacts a '
            'ON a.request_id=r.request_id JOIN desktop_agent_assignments d '
            'ON d.request_id=r.request_id AND d.agent_id=r.agent_id '
            'AND d.principal_id=? AND d.tenant_id=? WHERE r.request_id=?',
            (principal_id, tenant_id, request_id)).fetchone()
    if not row:
        return {'ready': False, 'reason': 'verified_worker_artifact_missing'}
    if hashlib.sha256(row[3]).hexdigest() != row[2]:
        return {'ready': False, 'reason': 'stored_artifact_corrupt'}
    receipt = json.loads(row[1])
    if receipt.get('status') != 'completed' or receipt.get('artifact_sha256') != row[2]:
        return {'ready': False, 'reason': 'receipt_mismatch'}
    return {'ready': True, 'agent_id': row[0], 'artifact_sha256': row[2],
            'coordinator_accepted': False, 'requires_verified_execution_adapter': True}
