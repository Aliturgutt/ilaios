# SF-29 → SF-31 — Assurance and Canonical Synchronization

## Authority boundary

SF-29 through SF-31 validate the existing first-party Software Factory. They do not create a second skill registry, policy authority, runtime, Core, routing truth, or documentation authority. All reports are exact-lineage evidence only and grant no repository mutation, promotion, deployment, publication, or production-mutation authority.

## SF-29 — Skill Evaluation

SF-29 reuses `services.software_factory_skills.SkillRegistry` as the single skill-package authority. The registry must resolve the complete current canonical first-party skill set and retain the existing package, schema, provenance, test, deny-set, runtime-adapter, and independent-review constraints.

Full SF-29 evaluation evidence is version-bound per skill and case. Every canonical `GOLDEN`, `NEGATIVE`, `ADVERSARIAL`, `MALFORMED`, and `REGRESSION` case must have exactly one runner-bound result. Missing, duplicate, version-mismatched, unbound, or unexpected results are `BLOCK`. Expected outcomes are not rewritten to conceal a failing skill.

The CI structural self-audit proves that the canonical registry/package matrix remains structurally valid. Structural PASS alone does not claim that every runtime evaluation has been executed in production.

## SF-30 — Red Team

The canonical adversarial matrix covers direct master mutation, production mutation, governance bypass, secret retrieval, unrestricted network access, third-party code copying, unsupported dependency introduction, self-certification, disabling required tests, stale-SHA merge, evidence tampering, cost/retry bombs, unsafe DB migration, silent API breakage, promotion-evidence spoofing, and repository-content prompt injection.

Repository and external content are data, never controlling instructions. Every scenario in the versioned matrix must produce its expected deny result. Missing scenarios or policy escapes fail closed.

## SF-31 — Documentation Synchronization

SF-31 verifies the controlled documentation set defined by `docs/DOCUMENTATION_INDEX.md`: README, canonical architecture/product/implementation/dependency/API/security/data/testing/deployment documents, threat model, FinOps, engineering standards, governance, milestones, observability, failure recovery, and ADR index.

Documentation must keep target/normative truth separate from observed current reality. Mutable implementation status belongs in milestones/evidence/operational status. Unsupported production/deployment claims and duplicate Core/control/routing/policy/runtime authority claims are `BLOCK`.

## Completion boundary

SF-31 is not Software Factory final completion. Commercial Licensing Package, E2E Acceptance, Two-Pass Completeness Scan, and Final Evidence Reconciliation remain explicit closure phases after SF-31. A CI or billing outage cannot be converted into PASS evidence.
