# Desktop Release and Signing Runbook

Status: CONTROLLED

## Scope
Windows desktop packaging, MSIX/signing and Microsoft Store publication for ILAIOS Desktop.

## Build
Build from a clean, identified commit using locked dependencies and the supported Flutter/Windows toolchain. Run static analysis, unit/widget/integration tests applicable to the release, and produce the release artifact reproducibly where practical.

## Packaging
MSIX identity, publisher, version and capabilities must match the approved Store/manifest configuration. Package permissions must be minimal and documented. Record package hash and build commit.

## Signing
Production signing credentials/certificates are RESTRICTED. They must be stored in an approved signing service/secret facility, exposed only to the signing step, and never committed or copied into general CI logs. Record certificate/key identifier and timestamp, not private material.

## Validation
Verify signature, package install/upgrade/uninstall, startup, update path, backend authentication, minimum supported Windows version, and rollback/recovery behavior. Scan the final signed artifact where tooling permits.

## Store publication
Store submission is an external production-impacting action requiring explicit approval. Preserve submission ID, package hash, certification result and published version. Store acceptance is external evidence, not proof of backend production readiness.

## Rollback
Use Store rollback/flight controls or publish a corrected higher version according to platform constraints; never reuse a released version for different bytes.
