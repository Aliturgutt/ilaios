import pytest

from services.operations_meta_agent_execution import (
    OperationsMetaAgentExecutionError,
    operations_meta_binding_for,
)


def test_unknown_operations_meta_agent_fails_closed() -> None:
    with pytest.raises(OperationsMetaAgentExecutionError):
        operations_meta_binding_for("ilaios.agent.operations.unknown.v1")


def test_operations_bindings_do_not_gain_direct_mutation_authority() -> None:
    for agent_id in (
        "ilaios.agent.operations.automation.v1",
        "ilaios.agent.operations.analytics.v1",
        "ilaios.agent.operations.monitoring.v1",
        "ilaios.agent.operations.recovery.v1",
        "ilaios.agent.operations.provider-watcher.v1",
        "ilaios.agent.operations.benchmark.v1",
    ):
        binding = operations_meta_binding_for(agent_id)
        assert binding.execution_mode == "governed-ai"
        assert not binding.permission.endswith(".write")
        assert binding.permission not in {"provider.request", "social.publish"}


def test_self_development_is_proposal_only_and_not_repository_write() -> None:
    binding = operations_meta_binding_for("ilaios.agent.meta.self-development.v1")
    assert binding.execution_mode == "governed-ai"
    assert binding.permission == "repository.read"
    assert binding.capability == "self-development.coordinate"
