---
name: ilaios-supply-chain-audit
description: Local static ILAIOS supply-chain audit for dependency pinning, workflow action immutability, and container base-image declarations.
---

# ILAIOS Supply Chain Audit

Use this skill for a deterministic, repository-local supply-chain review inside the existing SupplyChainSec path.

## Authority

Owner: `ilaios.agent.security.supply-chain.v1`

Capability: `security.dependency`

The skill has no package installation, registry, lockfile mutation, or release authority.

## Review scope

The analyzer combines the existing dependency-manifest checks with additional local evidence for:

- dependencies that are not exactly pinned or immutably referenced
- GitHub Actions references that are missing an immutable commit SHA
- container base images declared with a mutable `latest` tag

These are provenance/reproducibility findings. Version age or known-vulnerability status is not guessed without external evidence.

## Guardrails

- No package installation.
- No package-manager execution.
- No network or registry query.
- No dependency code execution.
- No automatic lockfile or workflow mutation.
- No release approval.
- No self-verification.

## Status rule

A local static report cannot claim the absence of upstream CVEs or registry compromise. Those require separately authorized external evidence. Independent verifier evidence is still required for `VERIFIED`.
