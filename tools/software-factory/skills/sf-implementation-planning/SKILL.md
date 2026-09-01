# sf-implementation-planning

Identity: `sf-implementation-planning` v1.0.0, IMPLEMENTED, planning-architecture.

Purpose: convert approved requirements and architecture evidence into an ordered bounded ChangeSet plan. Inputs: `intent`, `changed_paths`, `constraints`. Outputs: ordered ChangeSet plan, file operations, test plan, runtime adapters, validation plan.

Specialization: preserve repository/base-SHA scope and choose only canonical Python/Node/Flutter SF-6 adapters when validation requires them. This skill plans; it does not self-promote.

The common `../CONTRACT.md` supplies governance, deny-set, evidence and completion semantics.

## ILAIOS canonical skill-authoring overlay

When the plan creates or changes skills, apply the canonical logical contract `skill-engineering/create` from `tools/skill-engineering/skills/skill-create/SKILL.md`. Preserve bounded ownership, progressive disclosure, provider neutrality, provenance, GOLDEN/NEGATIVE/ADVERSARIAL/MALFORMED/REGRESSION acceptance coverage, independent review, existing-path integration, and evidence-backed maturity. This is an instruction-only authoring overlay; it does not change this skill's capabilities, tools, runtime adapters, policy, permissions, or mutation authority.
