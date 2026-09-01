---
name: ilaios-differential-review
description: Security review of an evidence-bounded code change without inventing or broadening the supplied diff.
---

# ILAIOS Differential Review

Use this skill when exact repository-change evidence already exists and the security question is limited to the supplied change set.

## Authority

Owner: `ilaios.agent.security.codesec.v1`

Capability: `security.sast`

The skill reuses CodeSec. It does not create a new reviewer, repository reader, or git authority.

## Required inputs

- authorized repository root
- security scope identifier
- `base_sha`: exact lowercase 40-character SHA
- `head_sha`: exact lowercase 40-character SHA
- `changed_paths`: normalized unique repository-relative paths supplied by an authorized repository/GitHub intelligence source
- admitted invocation and execution grant

## Execution

1. Reject malformed SHAs, absolute paths, traversal, duplicate paths, or scope escape.
2. Analyze security findings attributable to the supplied changed paths.
3. Identify whether the supplied change set touches high-protection boundaries such as identity, tenant, policy, approval, security, runtime, tool gateway, provider, governance, or CI workflows.
4. If a protected boundary changes without changed-test evidence, emit an explicit review gap rather than assuming coverage.
5. Preserve exact producer evidence for independent verification.

## Guardrails

- The adapter does not run git commands.
- It does not fetch branches, PRs, or commits.
- It does not infer missing changed paths.
- Deleted paths may be part of the change evidence but are not executed or reconstructed.
- No external network, exploitation, mutation, or self-verification.

## Status rule

A clean producer report is not proof that the full PR is safe unless the supplied differential evidence itself is complete and independently verified.
