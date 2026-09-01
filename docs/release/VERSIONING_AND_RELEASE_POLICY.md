# Versioning and Release Policy

Status: CONTROLLED

## Version model
ILAIOS uses SemVer-compatible product versions (`MAJOR.MINOR.PATCH`) for externally consumable releases. Pre-release identifiers may be used for canary/preview artifacts. Internal governed release stages such as `RELEASE.R00`, `R01`, `R02`, and `R03` are promotion stages, not substitutes for product version numbers.

## Tags and releases
Production release tags MUST be immutable, annotated where supported, and use `vMAJOR.MINOR.PATCH`. A tag may be published only from the exact commit whose CI, artifact, and deployment evidence is retained. GitHub Release notes must link the commit/tag, changelog entry, relevant PRs, known limitations, and rollback reference.

## Branching
`master` is the integration/default branch. Long-lived release branches are discouraged unless operationally necessary. Hotfix branches must be bounded and reconciled back to `master`.

## Changelog
`CHANGELOG.md` records user/operator-significant changes. Unreleased changes remain under `Unreleased` until a governed release is created.

## Promotion
`VERIFIED` does not mean `PRODUCTION`. R00 eligibility is repository verification only. R01/R02/R03 promotion requires the production readiness checklist, explicit human approval where required, deployment evidence, health/smoke verification, and rollback readiness.

## Rollback
Every production release must identify the prior known-good version/artifact, data compatibility constraints, migration rollback/forward-fix strategy, and stop conditions. Rollback is a controlled production action and requires evidence.
