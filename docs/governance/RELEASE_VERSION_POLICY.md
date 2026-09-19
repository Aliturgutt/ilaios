# ILAIOS Release and Version Policy

Status: Governed repository policy

## Purpose

This policy defines how ILAIOS versions, tags and GitHub Releases are created. It does not itself authorize production deployment, cloud mutation, signing, Store submission or external publication.

## Versioning model

ILAIOS uses Semantic Versioning for formal product releases:

`MAJOR.MINOR.PATCH`

- MAJOR: intentionally incompatible public contract or migration boundary.
- MINOR: backward-compatible capability addition or material feature promotion.
- PATCH: backward-compatible defect, security or operational correction.

Pre-release identifiers such as `-rc.1` may be used for release candidates. Build metadata must not be used as a substitute for immutable commit or artifact evidence.

## Source of truth

A formal version is valid only when all of the following agree:

1. the intended release commit on `master`;
2. an annotated Git tag named `vMAJOR.MINOR.PATCH` or an allowed pre-release form;
3. the corresponding GitHub Release object;
4. release notes identifying the exact commit and relevant evidence;
5. required CI/release gates for that commit.

Repository files may expose a runtime/package version, but a file value alone does not establish a formal release.

## Release eligibility

A commit may be proposed for a formal release only when:

- required Platform CI checks are green on the exact release candidate commit;
- no known failing required security or migration gate is bypassed;
- capability maturity and release state remain truthful and separate;
- release notes describe material changes, known limitations and rollback/recovery implications;
- production-sensitive promotion, if any, follows the separate approval model in `GOVERNANCE.md`.

## Tagging rules

- Tags are created from an exact reviewed commit; never from an ambiguous moving branch reference.
- Release tags are immutable. Do not delete and recreate a published release tag to point at a different commit.
- Do not force-move release tags.
- A corrected release receives a new PATCH version rather than rewriting the previous tag.
- Historical Hermes, ILAKOS and ILATEN names must not be introduced into active release identifiers.

## GitHub Release rules

Each formal GitHub Release must contain at minimum:

- version/tag;
- exact commit SHA;
- release date;
- concise change summary;
- compatibility or migration notes when applicable;
- security-relevant changes when applicable;
- known limitations;
- rollback/recovery reference when production behavior changes.

Draft Releases may be prepared automatically. Publication of a production-sensitive release must not bypass the human-approval requirements of `GOVERNANCE.md`.

## Version derivation

`pyproject.toml` currently declares the project version as dynamic. Until a dedicated package-version derivation mechanism is separately implemented and tested, automation must not invent a package version from branch names, timestamps or ungoverned counters.

Formal Git tags and GitHub Releases therefore remain explicit governed release evidence, not inferred deployment state.

## Relationship to capability maturity

`VERIFIED` does not mean `PRODUCTION` and a release tag does not automatically promote every capability to `PRODUCTION`.

Capability maturity continues to use the canonical chain:

`DESIGNED -> SPECIFIED -> IMPLEMENTED -> TESTED -> VERIFIED -> DEPLOYED / PRODUCTION`

Release state and capability maturity are recorded independently. A capability cannot skip an evidence-bearing maturity stage merely because a release object or deployment exists.

## First formal release

This policy does not retroactively invent a version for existing historical commits. The first formal ILAIOS GitHub Release must be selected in a dedicated release PR/approval package after the repository baseline, version number, notes and release evidence are reviewed.

## Prohibited actions

Automation must not:

- create or publish a formal production release merely because CI is green;
- overwrite or force-move a published release tag;
- infer `PRODUCTION` maturity from a tag alone;
- rewrite Git history to manufacture release lineage;
- bypass security, approval or rollback gates to produce a release.
