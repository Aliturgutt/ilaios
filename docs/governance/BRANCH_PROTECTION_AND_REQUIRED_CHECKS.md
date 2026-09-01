# Branch Protection and Required Checks

Status: CONTROLLED
Owner: Repository owner

## Scope
Applies to the default `master` branch and any future protected release branches.

## Required posture
`master` MUST be protected. Direct routine pushes, force pushes, history rewrites, branch deletion, and bypass of required checks are prohibited. Changes SHOULD enter through a bounded pull request. Admin capability does not create an exception to quality or security gates.

## Required checks
Required check names MUST be taken from the actual GitHub Actions/status contexts present in the repository and updated here whenever workflows are renamed. A check MUST NOT be marked required until it is stable and runs on the relevant PR path. Conversely, a required quality/security check MUST NOT be removed merely to unblock a merge.

Minimum categories for code-changing PRs:
- repository/platform CI applicable to changed code;
- website build/lint/typecheck/test when website paths change;
- security/supply-chain checks where configured;
- deployment readiness checks only when deployment infrastructure changes.

Documentation-only PRs may use path-aware reduced checks if the workflow explicitly supports that distinction.

## Merge rules
Required checks must pass; conversations requiring action must be resolved; branch must not contain unresolved merge conflicts; merge must preserve traceability. Squash or merge commit may be used according to repository settings, but the resulting commit must identify the PR purpose.

## Bypass and emergency change
Routine bypass is forbidden. Emergency change requires explicit owner authorization, recorded reason, bounded scope, immediate post-change validation, and retrospective PR/evidence. Emergency authority never permits fabricated evidence or secret exposure.

## Evidence
Accepted evidence: repository ruleset/branch-protection configuration, PR metadata, exact status contexts, and resulting protected-branch commit SHA.
