# Skill: ILAIOS Web Production QA

## Purpose

Evaluate a Web Factory output against explicit acceptance criteria and collect evidence for release decisions. This skill performs QA; it does not itself declare production status.

## Preconditions

- candidate artifact or deployment target is identified;
- acceptance criteria are available;
- required tenant/project context is resolved;
- any browser/network execution has passed canonical policy and approval gates.

## Procedure

1. Bind the QA run to the exact candidate revision/deployment identity when available.
2. Verify navigation, critical CTAs, forms, error states, responsive behavior, accessibility-critical flows, and localization paths required by the acceptance criteria.
3. Check that observed output corresponds to the intended candidate rather than stale or unrelated deployment state.
4. Record failures as evidence; do not repair silently or reinterpret failures as passes.
5. Request bounded repair through the normal governed workflow when remediation is allowed.
6. Re-run only the affected and required regression checks after a repair.
7. Produce an evidence-backed QA result with explicit PASS/FAIL/NOT-OBSERVABLE items.

## Required evidence

- exact candidate/deployment identity where observable;
- executed checks and observed results;
- unresolved failures or unavailable checks;
- evidence references generated through the canonical evidence path.

## Forbidden

- bypassing policy/approval to reach a production system;
- treating local build success as production verification;
- treating a deployed URL as proof that the correct revision is served;
- claiming production readiness when required checks are not observable or have failed.
