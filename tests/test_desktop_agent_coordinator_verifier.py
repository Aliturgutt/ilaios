"""Check actual coordinator adapter installation, not only static descriptor metadata."""
from datetime import datetime, timezone
from services.desktop_agent_adapter_verifier import VerifiedAgentAdapterStore
from services.desktop_agent_coordinator_verifier import CoordinatorAdapterVerifier
from tests.test_execution_coordinator import _coordinator

NOW = datetime(2026, 9, 28, tzinfo=timezone.utc)
VIDEO = 'ilaios.capability.video-factory'
WEB = 'ilaios.capability.web-factory'


def test_installed_real_coordinator_adapter_verified(tmp_path):
    coordinator, *_ = _coordinator(tmp_path)
    matrix = coordinator.adapter_matrix()
    video = next(row for row in matrix if row['adapter_id'] == 'video.product-runtime.v1')
    verifier = CoordinatorAdapterVerifier(coordinator, {'agent-video': video['capability_id']})
    store = VerifiedAgentAdapterStore({'agent-video': video['adapter_id']}, verifier)
    evidence = store.adapter(agent_id='agent-video', adapter_id=video['adapter_id'], now=NOW)
    assert evidence is not None and evidence.agent_bound and evidence.verified
    assert store.adapter(agent_id='other', adapter_id=video['adapter_id'], now=NOW) is None
    assert store.adapter(agent_id='agent-video', adapter_id='wrong', now=NOW) is None


def test_unavailable_adapter_cannot_pass_real_coordinator_verifier(tmp_path):
    coordinator, *_ = _coordinator(tmp_path)
    verifier = CoordinatorAdapterVerifier(coordinator, {'agent-web': WEB})
    assert not verifier.verify(agent_id='agent-web', adapter_id='web.product-runtime.v1')


def test_descriptor_without_installed_adapter_cannot_pass(tmp_path):
    coordinator, *_ = _coordinator(tmp_path)
    video = next(row for row in coordinator.adapter_matrix()
                 if row['adapter_id'] == 'video.product-runtime.v1')
    verifier = CoordinatorAdapterVerifier(coordinator, {'agent-video': video['capability_id']})
    coordinator._adapters.pop(video['capability_id'])
    assert not verifier.verify(agent_id='agent-video', adapter_id=video['adapter_id'])
