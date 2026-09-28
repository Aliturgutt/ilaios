import pytest
from services.desktop_agent_factory_contract_audit import audit_factory_contracts
from services.desktop_agent_factory_verifiers import provision_factory_verifiers
from services.execution_coordinator import _VIDEO, _WEB, _APP, _SOFTWARE, _DOCUMENT


def test_nine_canonical_factories_have_explicit_worker_acceptance_gaps():
    contracts = audit_factory_contracts()
    assert len(contracts) == 9
    assert all(contract.missing_proof for contract in contracts)
    local = {contract.capability_id for contract in contracts if contract.local_runtime}
    assert {_VIDEO, _WEB, _APP, _SOFTWARE, _DOCUMENT} <= local
    assert {contract.capability_id for contract in contracts if contract.worker_product_verifier} == {_VIDEO}


@pytest.mark.parametrize('capability', [_WEB, _APP, _SOFTWARE, _DOCUMENT])
def test_local_product_runtime_cannot_enable_unverified_worker_contract(capability):
    with pytest.raises(PermissionError):
        provision_factory_verifiers(enabled_capabilities=(capability,))
