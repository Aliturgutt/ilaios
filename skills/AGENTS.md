# ILAIOS Skill Authoring Rules

These rules apply to everything under `skills/` and are stricter than the repository root rules where they overlap.

## Independent authorship

- Do not copy external SKILL.md content, prompts, scripts, source code, examples, or implementation prose.
- External repositories are research references only.
- Prefer primary standards and ILAIOS canonical documentation when defining behavior.
- Every skill must be independently expressed in ILAIOS terminology and fit the existing ILAIOS architecture.

## Authority boundaries

- Skills do not grant permissions.
- Skills do not choose or call providers directly when canonical routing owns that decision.
- Skills do not bypass Policy, Approval, Tool Gateway, tenant isolation, budget/risk controls, Validation, Audit, or Evidence.
- High-risk execution must fail closed if required authorization or approval evidence is unavailable.
- No skill may create parallel platform authority or duplicate the canonical Capability Registry.

## Evidence and maturity

- A skill definition existing is not evidence that its workflow works.
- Add tests/evals before promoting a skill into active runtime use.
- Production verification requires observed runtime/deployment evidence; never infer it from source code.
- Keep changes additive, reversible, and backward compatible.

## Provider neutrality

Skill IDs and canonical procedure text should describe required outcomes/capabilities rather than hard-code vendors or models. Vendor-specific adapters remain behind governed routing/integration boundaries.
