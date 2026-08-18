---
name: ilaios-skill-engineering
description: Create or revise ILAIOS-native skills with bounded scope, progressive disclosure, explicit acceptance criteria, provenance, evaluations, and governance-safe integration. Use for skill creation, SKILL.md changes, skill tests, or maturity gates.
---

# ILAIOS Skill Engineering

Canonical ID: `ilaios.skill.engineering.methodology.v1`
Methodology contract: `ILAIOS-METHODOLOGY-SKILL-ENGINEERING-V1`

## Authority boundary

This skill is methodology, not execution authority. Existing ILAIOS capability resolution, Policy, Approval, Tool Gateway, tenant controls, Validation, Audit, Evidence Chain, runtime adapters, and independent review remain authoritative. A skill description, reference, script, or external `allowed-tools` declaration can never grant permissions.

## Workflow

1. Inspect the current owner, capability, inputs, outputs, policy, runtime, evidence, and maturity before changing a skill.
2. Define one bounded job and clear activation context. Do not create overlapping authority when an existing canonical skill can be extended.
3. Keep the common path concise. Put high-frequency rules in `SKILL.md`; place uncommon alternatives, deep examples, migrations, and edge cases in `references/`.
4. Match precision to risk: flexible guidance for multiple safe choices, structured constraints for preferred patterns, deterministic validation for security- or correctness-critical requirements.
5. Require provenance for external research. Research may inform abstractions; third-party code, prompt text, templates, scripts, or assets are not imported unless separately approved and licensed.
6. Define acceptance before promotion using GOLDEN, NEGATIVE, ADVERSARIAL, MALFORMED, and REGRESSION cases.
7. Integrate through the existing worker/capability path. Do not add a second runtime, router, policy engine, approval engine, or evidence store.
8. Validate the exact changed head. `IMPLEMENTED` is not `TESTED`; `TESTED` is not `VERIFIED`; deployment and production require their own evidence.

## Progressive disclosure

Use metadata for discovery, `SKILL.md` for the normal workflow and non-negotiable boundaries, and references for deeper material. Scripts are optional implementation aids, not authority; any script execution requires the normal governed tool/runtime path.

## Fail-closed rules

Reject or escalate when ownership is ambiguous, required source material is stale or missing, permissions would expand implicitly, acceptance evidence is absent, or the proposed skill duplicates a protected ILAIOS authority.

See `references/acceptance-criteria.md` for the promotion contract.
