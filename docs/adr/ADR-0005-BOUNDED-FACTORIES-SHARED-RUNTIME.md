# ADR-0005 — Bounded Factories on the Shared Governed Runtime

**Status:** Accepted — Canonical Rationale  
**Date:** 2026-08-13  
**Clarified:** 2026-09-01  
**Authority:** This ADR records rationale only and does not override canonical documents.

## Context

ILAIOS requires domain-specific execution without fragmenting platform authority. The canonical architecture and capability registry define **nine bounded factory capability identities**:

1. Video / Media Factory
2. Web Factory
3. Software Factory
4. App Factory
5. Research / Data Factory
6. Security Factory
7. Creative / Document Factory
8. Commerce / Growth Factory
9. Personal Operations Factory

These are separate bounded factory identities. Terms such as `Software/App` may describe a related product or dependency area, but **must not be interpreted as one factory, one capability identity, or an instruction to merge Software Factory and App Factory**.

Making each factory a mini-platform would duplicate planning, policy, routing, state, recovery, and evidence. Conversely, collapsing bounded factories merely because they share runtime infrastructure or have dependencies would erase domain and authority boundaries without removing the underlying responsibilities.

## Decision

A Factory is a **bounded domain workflow/DAG and orchestration layer** running on the shared ILAIOS Control Plane and governed execution runtime. Factories may compose capabilities and typed artifacts but do not own a second Core, Planner, policy authority, routing truth, or evidence truth.

The canonical factory topology contains **nine bounded factory capability identities**. A dependency or governed handoff between factories does **not** imply consolidation.

In particular:

- **Software Factory and App Factory remain separate.** App Factory depends on Software Factory and reuses shared software primitives through governed contracts. The dependency does not transfer execution, approval, client-mutation, signing, deployment, or store-submission authority.
- **Security Factory remains separate.** It provides bounded defensive security outcomes. Platform-wide security controls such as identity/tenant isolation, Policy, Privacy/DLP, Secrets/Crypto, execution admission, and evidence remain cross-cutting platform concerns and are not absorbed into Security Factory.
- Software Factory may hand typed intent and evidence to Security, Research/Data, Creative/Document, Commerce/Growth, Personal Operations, App, or other explicitly supported factory boundaries. Such handoffs do not propagate authority.
- Shared runtime, governance, routing, evidence, recovery, or infrastructure is a reason to reuse platform capabilities, **not** a reason to merge factory identities.

No factory-count consolidation from nine to eight, seven, six, or another number is implied or authorized by this ADR. Any future factory merge, split, addition, or removal requires new repository evidence, explicit canonical architecture review, dependency/authority analysis, regression impact analysis, and an approved architecture decision. Conversation-level interpretation, UI grouping, naming convenience, or documentation shorthand is not sufficient justification.

## Consequences

- Nine factory capability identities remain independently addressable at the domain layer while sharing one governed platform/runtime.
- Factories can evolve independently without fragmenting platform authority.
- Cross-factory composition uses typed contracts, explicit handoffs, and the shared Control Plane.
- Factory dependencies are not parent/child authority inheritance unless a canonical contract explicitly says so.
- Factory-specific hidden runtimes and direct provider bypasses are prohibited.
- Shared recovery, approval, routing, evidence, security controls, and budget controls remain reusable platform capabilities.
- Documentation, UI, tests, and future architecture analysis must distinguish **factory identity**, **dependency**, **cross-cutting platform capability**, and **presentation grouping**. They must not infer a factory merge from one of the other three concepts.

## Canonical References

- `../canonical/SYSTEM_ARCHITECTURE.md`
- `../canonical/DEPENDENCY_GRAPH.md`
- `../canonical/PRODUCT_REQUIREMENTS.md`
- `../../services/capability_registry.py`
- `../../services/integrations/software_app_handoff.py`
- `../../services/integrations/software_specialized_factory_handoff.py`
- `../../tests/test_capability_registry.py`
