# ILAIOS CI / Workflow Audit

Snapshot: 16 August 2026
Scope: `.github/workflows` validation/release surface plus live default-branch enforcement.

## Authority boundary

This is a mutable CI/governance status projection. Workflow files, live GitHub rulesets, exact-head workflow runs and deployment evidence are stronger current-reality evidence than this prose.

## Current validation authority

`Required CI Gate` is the stable required status check enforced on `master` by the active `ILAIOS Master Protection` ruleset.

The current required validation surface includes fail-closed jobs for the applicable change scope, including:

- changed-path classification and diff hygiene;
- secret scanning;
- CI supply-chain hardening;
- DB migration safety;
- API contract safety;
- Software Factory operational/assurance/final-closure checks;
- repository malware scanning with ClamAV;
- full Platform validation (`pytest`, Ruff and strict mypy);
- Website validation when Website paths require it.

Additional Desktop/Windows/MSIX and capability-specific workflows remain separate exact-head evidence gates where their scopes apply; they are not fabricated as universally required checks for unrelated documentation-only changes.

## Live default-branch enforcement

Current GitHub ruleset evidence shows:

- default branch: `master`;
- pull request required;
- `Required CI Gate` required;
- review-thread resolution required;
- non-fast-forward/force-style updates blocked;
- default-branch deletion blocked;
- no configured bypass actor;
- `.github/CODEOWNERS` exists for default, canonical/governance/security/operations, workflow/infra and release-sensitive paths.

The remaining review-governance limitation is explicit: required approving review count is currently `0`; CODEOWNER approval and approval-after-last-push are not enforced. Required CI is therefore the current independent automated verifier, not evidence of an independent human approval.

## AWS / external-mutation workflow posture

The R01-R03 deployment/recovery workflows are retained because they preserve release, rollback and evidence lineage. They must not be deleted merely because historical release evidence exists.

Current CI hardening keeps external mutation/spend paths separate from ordinary PR validation. In particular, guarded provider/AWS evidence workflows require explicit manual dispatch/approval inputs and exact source binding where configured. Repository CI success alone does not authorize cloud spend, production mutation or capability promotion.

RAG.14's guarded AWS canary path is an example: repository-side readiness is merged, but the live canary/evidence run remains separately gated by exact source evidence and explicit bounded external-spend authority.

## Desktop workflow posture

Desktop workflows remain a separate governed release surface. Current merged evidence covers Desktop CI, Windows Gate, unsigned MSIX/package validation, sidecar packaging smoke, Python 3.12 sidecar build pinning and bounded packaged E2E paths.

Those proofs do not establish:

- real Windows Google/Microsoft/passwordless external OIDC acceptance;
- Windows signing certificate/PFX authority;
- Partner Center publisher/package identity;
- Store submission/certification.

Those remain external release evidence gates.

## Workflow hardening policy

Before adding or changing a workflow:

- define the bounded purpose and exact source identity;
- use least GitHub token permissions;
- pin critical third-party actions to immutable revisions where required by repository policy;
- disable persisted checkout credentials unless explicitly required and justified;
- never expose secrets in logs;
- keep external mutation/spend off ordinary pull-request events;
- separate validation, evidence collection, promotion and release authority;
- preserve artifacts needed for audit/recovery;
- fail closed when required state/evidence is unavailable;
- never weaken or skip a failing gate merely to obtain green CI.

## Current decision

The old 11 August conclusion that `master` was unprotected is superseded by live ruleset evidence. Current result:

**workflow/CI validation authority is active and fail-closed; default-branch protection is active; independent human-review enforcement remains a deliberate governance gap; external mutation and production proof remain separate capability/release gates.**
