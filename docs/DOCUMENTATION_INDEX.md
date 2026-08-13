# ILAIOS Documentation Index

Status: CONTROLLED NAVIGATION INDEX — NOT AN INDEPENDENT ARCHITECTURE AUTHORITY

## Canonical documentation set (19 items)

The active canonical documentation set is exactly 19 items: 18 Markdown documents plus the `docs/adr/` decision-record directory.

1. `docs/canonical/SYSTEM_ARCHITECTURE.md`
2. `docs/canonical/AUTONOMOUS_NODE_ARCHITECTURE.md`
3. `README.md`
4. `docs/canonical/PRODUCT_REQUIREMENTS.md`
5. `docs/canonical/IMPLEMENTATION_SPEC.md`
6. `docs/canonical/DEPENDENCY_GRAPH.md`
7. `docs/canonical/API_CONTRACTS.md`
8. `docs/canonical/SECURITY_ARCHITECTURE.md`
9. `docs/canonical/DATA_ARCHITECTURE.md`
10. `docs/security/THREAT_MODEL.md`
11. `docs/canonical/TESTING_AND_EVALUATION.md`
12. `docs/canonical/DEPLOYMENT_ARCHITECTURE.md`
13. `docs/operations/FINOPS.md`
14. `docs/governance/ENGINEERING_STANDARDS.md`
15. `docs/governance/GOVERNANCE.md`
16. `docs/governance/MILESTONES.md`
17. `docs/adr/`
18. `docs/operations/OBSERVABILITY.md`
19. `docs/operations/FAILURE_RECOVERY.md`

## Authority rule

`SYSTEM_ARCHITECTURE.md` is the primary architecture authority. Specialist canonical documents own only their declared scope. `README.md` and this index provide navigation/orientation and do not create a second architecture authority. ADRs record decision rationale and do not override architecture.

Target truth in documentation and current implementation truth are separate. Code, tests, CI, runtime, deployment and durable evidence establish what is actually implemented today. Status/roadmap prose cannot promote implementation maturity by assertion.

## Supporting controlled documentation

Existing documents under `docs/governance/`, `docs/security/`, `docs/deployment/`, `docs/platform/`, `docs/release/`, `docs/core/`, `docs/video_automation/` and `docs/migration/` remain supporting operational, evidence, status, runbook or migration material unless explicitly declared otherwise by the canonical set above. They may not redefine a canonical architecture contract.

## Compatibility and archive

Historical canonical paths retained as redirects or compatibility shims are not independent authorities. Superseded source content is retained under `docs/archive/pre-2026-08-13/` and/or Git history for provenance.

See `docs/migration/CANONICAL_DOCUMENTATION_MIGRATION_2026-08-13.md` for the migration classification.
