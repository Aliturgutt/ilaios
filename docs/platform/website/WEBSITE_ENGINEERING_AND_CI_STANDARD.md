# Website Engineering and CI Standard

Status: CONTROLLED
Scope: `apps/website`

## Source of truth
Website behavior is defined by repository code and its committed dependency lock state. Preview success does not replace repository CI.

## Required local/CI gates
The website package must expose deterministic commands for dependency install, lint, type checking, automated tests where present, and production build. CI must execute the commands from the committed lockfile without silently updating dependencies.

At minimum, website-changing PRs must prove: install/reproducibility; lint; TypeScript/typecheck; production build; automated tests for changed logic; and route/metadata checks where relevant. Security-sensitive server code requires negative tests.

## Preview and deployment
Preview deployments are validation environments, not production evidence. A production claim requires exact commit/artifact linkage, production deployment result, canonical-domain verification, TLS, representative smoke tests, and observability.

## Quality
No disabling lint/type/test rules solely to obtain PASS. Environment variables must be declared without committing secrets. Public metadata, sitemap, robots, canonical URLs and localization routes should be tested when changed.

## Failure policy
Any required gate failure blocks merge until fixed or a documented path-aware exception proves the check is not applicable.
