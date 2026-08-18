"""Canonical digest truth for persisted named-agent execution evidence."""

from __future__ import annotations

import hashlib
import json

from services.named_agent_executor import NamedAgentExecution


def execution_evidence_digest(execution: NamedAgentExecution) -> str:
    """Hash the admitted identity and complete persisted runtime route.

    The route contains the sequence, immutable skill/provider/capability
    decision, routing evidence, deterministic-first marker, and exact output.
    All producer/verifier paths must use this function rather than a local
    digest variant.
    """
    material = {
        "invocation_id": execution.admission.invocation_id,
        "agent_id": execution.admission.agent_id,
        "verifier_id": execution.admission.verifier_id,
        "route": execution.route,
    }
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()
