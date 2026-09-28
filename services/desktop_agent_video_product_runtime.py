"""Worker-backed video adapter for the existing governed video product contract.

Explicitly opt in when constructing DurableVideoProductRuntime; never replace
an installed adapter globally. ProductRuntime still owns lease, grant, DAG,
finalization and coordinator acceptance.
"""
import hashlib
import json
import sqlite3
import time
from pathlib import Path

from services.integrations.video_runtime import (DeterministicLocalVideoRuntime,
    _LocalWorkflowExecution, VideoRuntimeError)
from src.video_automation.workflow_orchestrator import VideoWorkflowOrchestrator


class _UploadedVideoWorkflow(_LocalWorkflowExecution):
    def __init__(self, root, job_id, content):
        super().__init__(root, job_id)
        self._content = content

    def _render(self):
        output = self._root / 'final.mp4'
        output.write_bytes(self._content)
        self._rendered_path = output
        return {'sha256': hashlib.sha256(self._content).hexdigest(),
                'size': len(self._content), 'source': 'selected-worker-upload'}


class VerifiedWorkerVideoRuntime(DeterministicLocalVideoRuntime):
    def __init__(self, root, grants, governance, evidence, *, coordinator_db, agent_id,
                 principal_id, tenant_id):
        super().__init__(root, grants, governance, evidence)
        self._coordinator_db = coordinator_db
        self._agent_id = agent_id
        self._principal_id = principal_id
        self._tenant_id = tenant_id

    def _worker_bytes(self, request_id):
        with sqlite3.connect(self._coordinator_db, timeout=10) as conn:
            row = conn.execute('SELECT r.payload,a.sha256,a.content '
                'FROM desktop_agent_assignments d JOIN desktop_agent_result_receipts r '
                'ON r.request_id=d.request_id AND r.agent_id=d.agent_id '
                'JOIN desktop_agent_artifacts a ON a.request_id=d.request_id '
                'WHERE d.request_id=? AND d.agent_id=? AND d.principal_id=? AND d.tenant_id=?',
                (request_id, self._agent_id, self._principal_id, self._tenant_id)).fetchone()
        if row is None or json.loads(row[0]).get('status') != 'completed' or \
                json.loads(row[0]).get('artifact_sha256') != row[1] or \
                hashlib.sha256(row[2]).hexdigest() != row[1]:
            raise VideoRuntimeError('verified selected-worker output unavailable')
        return row[2]

    def execute(self, *, request_id, job_id, grant_id, now):
        content = self._worker_bytes(request_id)
        amount = self._governance.authorize_billable(request_id)
        started = time.monotonic()
        root = None
        try:
            self._grants.authorize_and_record(grant_id, subject_id='worker-video',
                action='video.execute', resource=job_id, now=now)
            root = self._root / request_id
            root.mkdir(parents=True, exist_ok=False)
            execution = _UploadedVideoWorkflow(root, job_id, content)
            workflow = VideoWorkflowOrchestrator().run(job_id, execution.steps())
            # Technical QA independently probes uploaded media; no worker QA is trusted.
            artifact = self._evidence.put_artifact(execution.rendered_path.read_bytes())
            provenance = self._evidence.append_provenance(job_id, artifact,
                'video.selected_worker.verified_upload')
            delivery = self._deliver(content, artifact.digest)
            elapsed = int((time.monotonic() - started) * 1000)
            if elapsed > 60000:
                raise VideoRuntimeError('worker video validation exceeded latency budget')
            result = {'request_id': request_id, 'job_id': job_id,
                'final_stage': workflow.progress.stage.value,
                'executed_stage_count': len(workflow.executed_stages),
                'qa': execution.qa, 'artifact_digest': artifact.digest,
                'artifact_size': artifact.size,
                'provenance_record_hash': provenance.record_hash,
                'delivery': delivery, 'publisher_boundary': 'verified-worker-delivery',
                'provider_boundary': 'selected-worker-upload',
                'latency_ms': elapsed, 'latency_budget_ms': 60000,
                'latency_passed': True, 'metered_units': 1,
                'reserved_minor': amount, 'actual_minor': amount}
            self._governance.reconcile_billable(request_id, actual_minor=amount,
                status='executed', result=result)
            return result
        except Exception:
            self._governance.reconcile_billable(request_id, actual_minor=0,
                status='failed')
            raise
        finally:
            if root is not None and root.exists():
                import shutil
                shutil.rmtree(root)
