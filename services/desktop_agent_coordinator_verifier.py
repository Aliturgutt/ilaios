"""Read-only binding of a Desktop agent to an installed coordinator adapter.

The coordinator remains the sole execution authority; this verifier cannot dispatch.
"""
from __future__ import annotations
from services.execution_coordinator import ExecutionCoordinator


class CoordinatorAdapterVerifier:
    def __init__(self, coordinator: ExecutionCoordinator, agent_capabilities: dict[str, str]):
        self._coordinator = coordinator
        self._agent_capabilities = dict(agent_capabilities)

    def verify(self, *, agent_id: str, adapter_id: str) -> bool:
        capability = self._agent_capabilities.get(agent_id)
        if not capability or not adapter_id:
            return False
        # Matrix alone is insufficient: it can describe an unavailable adapter.
        descriptor = next((row for row in self._coordinator.adapter_matrix()
            if row['capability_id'] == capability), None)
        if (descriptor is None or descriptor['adapter_id'] != adapter_id
                or descriptor['executable'] is not True):
            return False
        installed = self._coordinator._adapters.get(capability)
        return bool(installed is not None
            and installed.descriptor.capability_id == capability
            and installed.descriptor.adapter_id == adapter_id)
