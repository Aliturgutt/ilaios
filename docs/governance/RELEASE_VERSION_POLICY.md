# ILAIOS Version, Tag and Release Policy

## Scope

This policy defines repository versioning and GitHub release discipline. It does not authorize production deployment; production promotion remains governed by `GOVERNANCE.md` and the release/deployment evidence chain.

## Version scheme

ILAIOS uses Semantic Versioning 2.0.0 for externally meaningful software releases: `MAJOR.MINOR.PATCH`.

- MAJOR: incompatible public contract or architecture change approved through canonical governance.
- MINOR: backward-compatible capability addition.
- PATCH: backward-compatible fix, hardening or documentation/release correction that affects a published release.

Pre-releases use SemVer prerelease identifiers such as `1.1.0-rc.1` when release-candidate validation is required.

## Git tags

Release tags are annotated tags using the form `vMAJOR.MINOR.PATCH` or the corresponding prerelease form. A release tag must point to the exact commit whose required checks passed. Tags are immutable release references; a published tag must not be force-moved. If a release is invalid, publish a corrected version or document revocation rather than rewriting the original tag.

## Release prerequisites

Before a GitHub Release is published:

1. the target commit is on the canonical release branch;
2. applicable required CI checks are green;
3. release notes describe material changes and known limitations;
4. security-sensitive or production-changing actions have their required human approval;
5. release artifacts are reproducible or traceable to the tagged commit;
6. rollback/recovery implications are recorded where material.

## GitHub Release

GitHub Releases are created from immutable version tags. Release title should match the version. Release notes must distinguish repository/software release status from actual production deployment status. A GitHub Release never by itself proves production deployment.

## Authorization

Normal repository preparation, CI validation and release-note generation may be automated. Production-sensitive release or deployment actions remain Class C changes under `GOVERNANCE.md` and require the declared approval model.

## Revocation and correction

Do not delete history to conceal a bad release. Mark the affected release as withdrawn/deprecated in release notes where appropriate, preserve evidence, fix forward, and publish a new version.
