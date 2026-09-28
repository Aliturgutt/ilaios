"""Only server-issued human provenance permits persisted general resume."""
from datetime import datetime, timezone
import pytest
from services.desktop_agent_legacy_provenance import requires_agent_resume_guard
from services.desktop_human_intent_provenance import record_human_intent
from services.desktop_agent_assignment_store import record_agent_assignment
from tests.test_execution_coordinator import _coordinator


def test_historical_multiple_adapters_and_verified_human_intent(tmp_path):
    coordinator, *_ = _coordinator(tmp_path)
    db = coordinator._database_path
    for request_id, objective in [('old-video', 'Create a video about our product'),
                                  ('old-web', 'Build a website for our product')]:
        coordinator.prepare(request_id, objective, token='token', principal_id='owner',
                            tenant_id='tenant-a', now=datetime.now(timezone.utc))
        assert requires_agent_resume_guard(db, request_id)
    with pytest.raises(ValueError):
        record_human_intent(db, 'old-web', 'wrong-owner', 'tenant-b')
    # Historical rows cannot be retrospectively certified as human intent:
    # server-issued human provenance requires the new exec- namespace.
    with pytest.raises(ValueError):
        record_human_intent(db, 'old-web', 'owner', 'tenant-a')
    coordinator.prepare('exec-new-human', 'Create a video about our product',
        token='token', principal_id='owner', tenant_id='tenant-a',
        now=datetime.now(timezone.utc))
    record_human_intent(db, 'exec-new-human', 'owner', 'tenant-a')
    assert not requires_agent_resume_guard(db, 'exec-new-human')
    record_agent_assignment(db, request_id='exec-new-human', agent_id='agent-a',
        principal_id='owner', tenant_id='tenant-a')
    assert requires_agent_resume_guard(db, 'exec-new-human')
    reopened, *_ = _coordinator(tmp_path)
    assert requires_agent_resume_guard(reopened._database_path, 'old-web')
    assert requires_agent_resume_guard(reopened._database_path, 'exec-new-human')
