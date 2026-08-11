# ILAIOS CI / Workflow Audit

Snapshot: 11 August 2026
Scope: `.github/workflows` inventory and repository-level safety assessment.

## Observed workflows

### AWS / release path

- `aws-r01-acm-status.yml`
- `aws-r01-canary-apply.yml`
- `aws-r01-discovery.yml`
- `aws-r01-image-publish.yml`
- `aws-r01-image-scan.yml`
- `aws-r01-oidc-proof.yml`
- `aws-r01-opentofu-readiness.yml`
- `aws-r01-preparation-resources.yml`
- `aws-r02-limited-apply.yml`
- `aws-r02-limited-readiness.yml`
- `aws-r02-live-status.yml`
- `aws-r03-live-status.yml`
- `aws-r03-production-apply.yml`

### Desktop path

- `desktop-ci.yml`
- `desktop-msix-packaging.yml`
- `desktop-msix-signed-release.yml`
- `desktop-windows-release.yml`

## Assessment

### Production/release workflows — KEEP

The AWS workflows are tied to a proven R01-R03 release history and evidence chain. This governance package does not remove, rename or simplify them. Deleting a workflow merely because the release has already happened would destroy repeatability and recovery context.

Any future consolidation must first prove:

1. which workflow is still invoked;
2. which artifacts/evidence paths depend on its name;
3. whether rollback/recovery documentation references it;
4. whether replacement behavior has equivalent or stronger gates.

### Desktop workflows — KEEP / separate workstream

Desktop workflows belong to the Desktop workstream and are excluded from this package. They must not be changed as part of repository-governance cleanup.

## Main CI governance gap

GitHub currently reports `master` as unprotected and no required status checks are enforced through branch protection. This means repository conventions can be bypassed by a direct push even when workflow definitions themselves are strong.

Recommended owner-level configuration after stable check names are confirmed:

- protect `master`;
- require PRs for material changes;
- require the stable platform checks appropriate to the changed scope;
- disallow force pushes;
- disallow deletion of `master`;
- consider requiring resolved review conversations.

Do not blindly require every Desktop/AWS workflow for every documentation or Website-only change; protection rules should match stable, generally applicable checks or use path-aware required checks.

## Workflow change policy for post-v1

Before adding or changing a workflow:

- define the bounded purpose;
- use least GitHub token permissions;
- pin or deliberately version critical third-party actions where practical;
- avoid secrets in logs;
- avoid production mutation on ordinary pull-request events;
- separate validation from promotion;
- require explicit approval for production-sensitive jobs;
- preserve evidence artifacts needed for audit/recovery;
- test on a branch before modifying the production path.

## Current action

No workflow file is modified by this audit. This is intentional: no safe workflow deletion or behavior change is proven necessary from the current evidence.

Result: **workflow inventory healthy; branch-level enforcement needs owner hardening.**
