# ILAIOS Documentation Index

Status: CONTROLLED NAVIGATION — NOT AN INDEPENDENT ARCHITECTURE AUTHORITY

The canonical documentation model contains exactly 19 items: 18 primary Markdown documents plus the `adr/` directory. Architecture is target/normative truth; current implementation state is established by code, tests, CI, runtime, deployment, and durable evidence.

## Canonical items

1. [README](../README.md)
2. [System Architecture](canonical/SYSTEM_ARCHITECTURE.md)
3. [Autonomous Node Architecture](canonical/AUTONOMOUS_NODE_ARCHITECTURE.md)
4. [Product Requirements](canonical/PRODUCT_REQUIREMENTS.md)
5. [Implementation Specification](canonical/IMPLEMENTATION_SPEC.md)
6. [Dependency Graph](canonical/DEPENDENCY_GRAPH.md)
7. [API Contracts](canonical/API_CONTRACTS.md)
8. [Security Architecture](canonical/SECURITY_ARCHITECTURE.md)
9. [Data Architecture](canonical/DATA_ARCHITECTURE.md)
10. [Threat Model](security/THREAT_MODEL.md)
11. [Testing and Evaluation](canonical/TESTING_AND_EVALUATION.md)
12. [Deployment Architecture](canonical/DEPLOYMENT_ARCHITECTURE.md)
13. [FinOps](operations/FINOPS.md)
14. [Engineering Standards](governance/ENGINEERING_STANDARDS.md)
15. [Governance](governance/GOVERNANCE.md)
16. [Milestones](governance/MILESTONES.md)
17. [Observability](operations/OBSERVABILITY.md)
18. [Failure Recovery](operations/FAILURE_RECOVERY.md)
19. [Architecture Decision Records](adr/README.md)

## Supporting documentation

`SECURITY.md`, `CONTRIBUTING.md`, controlled runbooks, implementation/status evidence, and migration evidence remain scoped supporting material. Files under `archive/` are historical and non-authoritative.

## Authority boundary

`canonical/SYSTEM_ARCHITECTURE.md` is the primary architecture authority. Specialist canonical documents govern only their declared scope. ADRs record rationale and do not override canonical documents. Compatibility paths, archive material, projections, status reports, and migration records cannot create a second Core, Control Plane, routing authority, policy authority, registry identity truth, governed runtime, or evidence/provenance truth.
