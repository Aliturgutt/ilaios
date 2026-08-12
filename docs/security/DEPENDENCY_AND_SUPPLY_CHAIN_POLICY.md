# Dependency and Supply Chain Policy

Status: CONTROLLED

## Principles
Dependencies must be necessary, maintained, license-compatible with the repository decision, and introduced with bounded permissions. Prefer fewer dependencies and reproducible builds.

## Pinning and lockfiles
Python, npm/Node, Flutter/Dart and infrastructure tooling MUST use the ecosystem's reproducibility mechanism where available. Application dependencies must be locked; CI must install from the committed lock state. Unbounded production dependency ranges are prohibited where a lock mechanism exists.

GitHub Actions used in security/release/deployment-sensitive workflows SHOULD be pinned to immutable commit SHAs; mutable tags require documented risk acceptance and automated update review.

## Updates
Automated update PRs are acceptable but never self-authorize production. Major-version updates require compatibility review. Security updates are prioritized by exploitability, exposure and severity, not CVSS alone.

## Provenance
Release artifacts should retain source commit, dependency lock state, builder/workflow identity, digest, SBOM where supported, and signature/attestation where implemented.

## Vulnerabilities
Confirmed critical/high vulnerabilities affecting reachable production paths require triage, containment/mitigation, patch or compensating control, regression verification, and evidence. False positives require documented justification.

## Prohibited practices
No vendored unknown binaries, secrets in package configuration, disabling TLS verification, bypassing lockfiles for release builds, or weakening scans merely to obtain PASS.
