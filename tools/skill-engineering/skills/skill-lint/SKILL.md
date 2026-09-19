# ILAIOS Skill Engineering — Lint

## Purpose

Perform the cheapest deterministic package-hygiene gate immediately after skill creation and before semantic validation. This stage detects structural drift early without executing the skill, invoking providers, mutating repositories, or claiming security assurance.

## Inputs

- immutable candidate package digest;
- package file inventory;
- manifest and schema documents;
- canonical Skill Engineering package contract version;
- evidence identifiers for the inspected candidate.

## Required checks

1. Required package files and directories are present.
2. `skill_id`, logical taxonomy identity, package path, and version are internally consistent.
3. Manifest, input schema, output schema, provenance document, and eval document are parseable and structurally well formed.
4. Required deny-set declarations remain present and no declaration attempts to own Policy, Approval, Tool Gateway, routing, Validation, Audit, Evidence, tenant, or Core authority.
5. Eval kinds include the canonical GOLDEN, NEGATIVE, ADVERSARIAL, MALFORMED, and REGRESSION matrix.
6. Findings are bound to the exact candidate digest and evidence identifiers.

## Fail-closed behavior

Missing files, malformed documents, identity drift, forbidden authority ownership, invalid digests, or incomplete evidence produce `BLOCKED`. Lint must never repair files automatically, broaden permissions, retrieve secrets, access unrestricted network resources, mutate master, execute a provider, promote a candidate, or self-certify maturity.

## Output

Emit a deterministic lint report containing the candidate digest, checks performed, findings, evidence identifiers, and unresolved blockers. `PASS` means package hygiene is suitable for the next lifecycle gate only; it does not mean validated, secure, compatible, promoted, verified, deployed, or production-ready.

## Governance boundary

This skill is non-authoritative. Canonical Policy, Approval, tenant controls, Tool Gateway, runtime admission, routing, Validation, Audit, and Evidence remain external and authoritative.
