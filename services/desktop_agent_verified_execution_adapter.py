"""Fail-closed verification adapter for selected Desktop worker artifacts.

This is an admission gate, not a coordinator acceptance adapter. The existing
coordinator grant and product-specific acceptance lifecycle remains mandatory.
"""
import hashlib
import json
import sqlite3


class VerifiedAgentExecutionAdapter:
    def __init__(self, coordinator):
        self.coordinator = coordinator

    def verify(self, *, request_id, agent_id, principal_id, tenant_id):
        state = self.coordinator.get(request_id, principal_id=principal_id,
                                     tenant_id=tenant_id)
        if state['execution_status'] != 'ADMITTED':
            raise PermissionError('execution not admitted')
        if not self.coordinator._governance.admission_proven(request_id):
            raise PermissionError('governance admission not proven')
        with sqlite3.connect(self.coordinator._database_path, timeout=10) as conn:
            row = conn.execute('SELECT r.payload,a.sha256,a.content '
                'FROM desktop_agent_assignments d JOIN desktop_agent_result_receipts r '
                'ON r.request_id=d.request_id AND r.agent_id=d.agent_id '
                'JOIN desktop_agent_artifacts a ON a.request_id=d.request_id '
                'WHERE d.request_id=? AND d.agent_id=? AND d.principal_id=? '
                'AND d.tenant_id=?',
                (request_id, agent_id, principal_id, tenant_id)).fetchone()
        if row is None:
            raise PermissionError('no bound worker result')
        receipt = json.loads(row[0])
        if (receipt.get('status') != 'completed'
                or receipt.get('artifact_sha256') != row[1]
                or hashlib.sha256(row[2]).hexdigest() != row[1]):
            raise PermissionError('worker artifact evidence invalid')
        return {'verified': True, 'agent_id': agent_id, 'artifact_sha256': row[1],
                'coordinator_accepted': False, 'product_acceptance_required': True}
