"""Registry proofs for the in-place ILAIOS Knowledge/RAG capability evolution."""

from services.capability_registry import capability


def test_rag_extends_single_existing_knowledge_capability() -> None:
    knowledge = capability("ilaios.capability.knowledge")

    assert knowledge.display_name == "Knowledge / RAG and Project Context"
    assert knowledge.domain == "intelligence"
    assert knowledge.implementation_roots == (
        "src/knowledge_graph",
        "src/project_manager",
        "services/knowledge_rag.py",
    )
    assert {
        "ilaios.capability.core",
        "ilaios.capability.identity-tenant",
        "ilaios.capability.privacy-dlp",
        "ilaios.capability.evidence-audit",
        "ilaios.capability.provider-routing",
    } <= knowledge.dependencies
