from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from services.desktop_agent_factory_plan import plan_factory_assignments
from services.desktop_agent_auto_router import AutomaticRoutingUnavailable
from services.execution_coordinator import classify_execution_plan

NOW = datetime(2026, 9, 28, tzinfo=timezone.utc)


def settings(objective):
    selected = classify_execution_plan(objective).capability_ids
    preflight = Mock()
    preflight.check.return_value = SimpleNamespace(eligible=True)
    return {'delivery': object(), 'worker_runtime_ready': True,
        'bindings': {f'worker-{index}': (f'adapter-{index}', capability)
                     for index, capability in enumerate(selected)},
        'preflight': preflight, 'runtime': object(), 'db': object()}


def test_plan_single_factory_and_tenant_scope():
    objective = 'Create a video about our product'
    config = settings(objective)
    plan = plan_factory_assignments(objective=objective, config=config,
        tenant='tenant-a', now=NOW)
    assert len(plan) == 1
    assert plan[0].capability_id == classify_execution_plan(objective).capability_ids[0]
    assert config['preflight'].check.call_args.kwargs['tenant'] == 'tenant-a'


def test_no_partial_plan_if_any_factory_unavailable():
    objective = 'Create a video and a website for our product'
    config = settings(objective)
    selected = classify_execution_plan(objective).capability_ids
    assert len(selected) >= 2
    plan = plan_factory_assignments(objective=objective, config=config,
        tenant='tenant-a', now=NOW)
    assert {item.capability_id for item in plan} == set(selected)
    del config['bindings']['worker-1']
    with pytest.raises(AutomaticRoutingUnavailable):
        plan_factory_assignments(objective=objective, config=config,
            tenant='tenant-a', now=NOW)


def test_ambiguous_and_unready_factory_rejected():
    objective = 'Create a video about our product'
    config = settings(objective)
    capability = classify_execution_plan(objective).capability_ids[0]
    config['bindings']['duplicate'] = ('another-adapter', capability)
    with pytest.raises(AutomaticRoutingUnavailable):
        plan_factory_assignments(objective=objective, config=config,
            tenant='tenant-a', now=NOW)
    config['bindings'].pop('duplicate')
    config['worker_runtime_ready'] = False
    with pytest.raises(AutomaticRoutingUnavailable):
        plan_factory_assignments(objective=objective, config=config,
            tenant='tenant-a', now=NOW)
