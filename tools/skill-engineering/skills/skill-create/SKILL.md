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
3. Define the smallest additive and backward-compatible skill contract.
4. Declare required capabilities as requests only. Capability declaration never grants permission.
5. Declare allowed tools, risk class, approval expectations, evidence requirements, schemas, tests, evals, and provenance.
6. Reject direct provider coupling when the behavior can be expressed as a provider-independent capability requirement.
7. Generate a candidate package and a validation plan.
8. Require independent review before promotion.
9. Leave maturity at the strongest evidence-backed state. Never infer TESTED, VERIFIED, DEPLOYED, PRODUCTION, or DONE from authored files alone.

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
