from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from services.desktop_agent_auto_router import select_agent, AutomaticRoutingUnavailable
from services.execution_coordinator import classify_execution_plan

OBJECTIVE = 'Create a video about our product'
CAPABILITY = classify_execution_plan(OBJECTIVE).capability_ids[0]
NOW = datetime(2026, 9, 28, tzinfo=timezone.utc)


def config():
    preflight = Mock()
    preflight.check.return_value = SimpleNamespace(eligible=True)
    return {'delivery': object(), 'worker_runtime_ready': True,
        'bindings': {'video-worker': ('verified-video', CAPABILITY),
                     'unrelated-worker': ('verified-web', 'unrelated-capability')},
        'preflight': preflight, 'runtime': object(), 'db': object()}


def test_automatically_selects_only_verified_matching_worker():
    settings = config()
    assert select_agent(objective=OBJECTIVE, config=settings, tenant='tenant-a', now=NOW) == ('video-worker', CAPABILITY)
    assert settings['preflight'].check.call_args.kwargs['tenant'] == 'tenant-a'
    assert settings['preflight'].check.call_count == 1


def test_unconfigured_ineligible_or_ambiguous_worker_fails_closed():
    settings = config()
    for field in ('delivery', 'worker_runtime_ready'):
        invalid = dict(settings, **{field: None})
        with pytest.raises(AutomaticRoutingUnavailable):
            select_agent(objective=OBJECTIVE, config=invalid, tenant='tenant-a', now=NOW)
    settings['preflight'].check.return_value = SimpleNamespace(eligible=False)
    with pytest.raises(AutomaticRoutingUnavailable):
        select_agent(objective=OBJECTIVE, config=settings, tenant='tenant-a', now=NOW)
    settings['preflight'].check.return_value = SimpleNamespace(eligible=True)
    settings['bindings']['second-video'] = ('another-verified-video', CAPABILITY)
    with pytest.raises(AutomaticRoutingUnavailable):
        select_agent(objective=OBJECTIVE, config=settings, tenant='tenant-a', now=NOW)
