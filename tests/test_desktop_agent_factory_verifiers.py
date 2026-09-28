from types import SimpleNamespace
from unittest.mock import patch
import pytest
from services.desktop_agent_factory_verifiers import (
    CANONICAL_FACTORY_CAPABILITIES, provision_factory_verifiers,
    verify_video_worker_product)
from services.execution_coordinator import _VIDEO, _WEB


def test_all_nine_factories_canonical_but_unimplemented_verifiers_closed():
    assert len(CANONICAL_FACTORY_CAPABILITIES) == 9
    assert provision_factory_verifiers() == {}
    with pytest.raises(PermissionError):
        provision_factory_verifiers(enabled_capabilities=(_VIDEO, _WEB))
    with pytest.raises(ValueError):
        provision_factory_verifiers(enabled_capabilities=('unrecognized',))
    assert set(provision_factory_verifiers(enabled_capabilities=(_VIDEO,))) == {_VIDEO}


def test_video_requires_dedicated_matching_owner_agent_and_digest():
    from services.desktop_agent_video_product_runtime import VerifiedWorkerVideoRuntime
    runtime = object.__new__(VerifiedWorkerVideoRuntime)
    runtime._agent_id = 'video-agent'
    runtime._principal_id = 'owner'
    runtime._tenant_id = 'tenant'
    runtime._coordinator_db = 'coordinator.sqlite'
    coordinator = SimpleNamespace(_adapters={_VIDEO:SimpleNamespace(
        _runtime=SimpleNamespace(_video=runtime))}, _database_path='coordinator.sqlite')
    kwargs = dict(coordinator=coordinator, request_id='child', agent_id='video-agent',
                  principal_id='owner', tenant_id='tenant', artifact_sha256='digest')
    with patch('services.desktop_agent_verified_execution_adapter.VerifiedAgentExecutionAdapter.verify_product_contract',
               return_value={'verified':True,'agent_id':'video-agent','artifact_sha256':'digest'}):
        assert verify_video_worker_product(**kwargs)['verified'] is True
        with pytest.raises(PermissionError):
            verify_video_worker_product(**dict(kwargs, tenant_id='other'))
        with pytest.raises(PermissionError):
            verify_video_worker_product(**dict(kwargs, agent_id='other'))
        with pytest.raises(PermissionError):
            verify_video_worker_product(**dict(kwargs, artifact_sha256='forged'))
