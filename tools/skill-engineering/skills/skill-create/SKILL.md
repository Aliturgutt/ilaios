# ILAIOS Skill Create

## Purpose

Create a candidate first-party ILAIOS skill package without granting the skill execution authority.

This skill is an authoring and specification capability. It must preserve the canonical ILAIOS Core and all governance boundaries.

## Required inputs

- objective
- target logical skill ID from the canonical taxonomy
- requested capabilities
- constraints and acceptance criteria

## Workflow

1. Inspect the relevant ILAIOS contracts, existing skill packages, tests, and dependency boundaries.
2. Confirm that the requested behavior belongs in the Skill Layer rather than Policy, Approval, Routing, Tool Gateway, Validation, Audit, Evidence, Tenant, Planner, or Core.
3. Define the smallest additive and backward-compatible skill contract with one bounded job and a clear activation context. Extend an existing canonical skill when that avoids overlapping ownership.
4. Keep the common path concise. Put high-frequency, non-negotiable workflow and safety rules in `SKILL.md`; move deep examples, uncommon alternatives, migrations, and edge cases to `references/` when needed. References must not hide safety-critical rules required at execution time.
5. Match instruction precision to risk: allow flexible guidance where several choices are safe, structured constraints where a preferred pattern exists, and deterministic validation for correctness- or security-critical requirements.
6. Declare required capabilities as requests only. Capability declaration never grants permission.
7. Declare allowed tools, risk class, approval expectations, evidence requirements, schemas, tests, evals, and provenance.
8. Reject direct provider coupling when the behavior can be expressed as a provider-independent capability requirement.
9. Define acceptance before promotion with GOLDEN, NEGATIVE, ADVERSARIAL, MALFORMED, and REGRESSION scenarios. Common-case success is insufficient without malformed-input and bypass resistance.
10. Generate a candidate package and a validation plan.
11. Require independent review before promotion.
12. Leave maturity at the strongest evidence-backed state. Never infer TESTED, VERIFIED, DEPLOYED, PRODUCTION, or DONE from authored files alone.

## Progressive disclosure

Discovery metadata should be enough to decide whether the skill applies. `SKILL.md` owns the normal workflow and mandatory boundaries. Optional `references/` hold lower-frequency depth. Optional scripts are implementation aids only and receive no execution authority from being packaged with a skill; execution must still pass canonical ILAIOS admission and Tool Gateway controls.

## Mandatory boundaries

The generated skill must not:

- rewrite or duplicate the canonical Core;
- implement a parallel planner, router, policy engine, approval engine, Tool Gateway, Audit Engine, Validation Pipeline, Evidence Chain, tenant authority, or authorization system;
- bypass Policy, Approval, Tool Gateway, tenant, budget, privacy, security, audit, or evidence controls;
- embed secrets or credentials;
- grant itself filesystem, network, browser, shell, provider, or production permissions;
- copy third-party implementation text or code without an explicitly compatible provenance decision;
- mutate master or production;
- self-certify its own output.

## Output

Return a candidate skill package description containing:

- logical skill ID;
- package identity/version;
- purpose and non-goals;
- inputs/outputs;
- requested capabilities;
- allowed tool declarations;
- risk and approval requirements;
- evidence requirements;
- schemas;
- test/eval plan;
- provenance;
- unresolved blockers.

A candidate package is not a promoted or production-verified skill.
