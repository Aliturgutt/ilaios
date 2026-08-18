# Skill: ILAIOS Skill Create

## Purpose

Create a new ILAIOS-native skill definition from an ILAIOS requirement without copying external skill content and without adding a new authority plane.

## Inputs

- bounded user or product requirement;
- relevant canonical architecture and governance constraints;
- existing capability dependencies;
- acceptance criteria and risk classification.

## Procedure

1. Confirm the requirement belongs in a skill rather than Core, policy, routing, a provider adapter, UI, or another existing platform capability.
2. Inspect related ILAIOS contracts and existing skills to prevent duplicate authority or duplicate behavior.
3. Define one narrow outcome and explicit non-goals.
4. Declare capability dependencies, risk class, approval expectations, inputs, outputs, validation requirements, and required evidence.
5. Write the procedure independently in ILAIOS terminology.
6. Keep provider/model choices abstract unless the skill is explicitly documenting an adapter boundary; provider selection remains governed routing authority.
7. Add fail-closed behavior for unavailable authorization, approval, tenant, security, or evidence prerequisites.
8. Add tests/evals that prove namespace, dependency, governance, and expected-behavior invariants.
9. Do not promote the skill until the relevant validation gates have actually passed.

## Required output

A reviewable ILAIOS-owned skill definition plus metadata/tests appropriate to its risk.

## Forbidden

- copying or lightly rewriting an external skill;
- granting tool or provider access from the skill definition;
- introducing parallel policy, approval, routing, capability registry, audit, or evidence authority;
- reporting the skill as verified or production-ready without evidence.
