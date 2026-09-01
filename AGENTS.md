# ILAIOS Operating Rules

These instructions apply to every Codex/agent task in this repository unless a more specific nested `AGENTS.md` adds stricter requirements.

## 1. Evidence-first status reporting

Never report work as `DONE`, `Completed`, `Production Ready`, `Working`, or `100%` merely because it was planned, proposed, partially implemented, or code was written.

Use only evidence-backed status. If evidence is missing, report one of:

- `NOT STARTED`
- `IN PROGRESS`
- `PARTIAL`
- `BLOCKED`
- `IMPLEMENTED`
- `TESTED`
- `VERIFIED`
- `DEPLOYED`
- `PRODUCTION`
- `DONE`

Maturity is ordered and non-equivalent:

`IMPLEMENTED != TESTED != VERIFIED != DEPLOYED != PRODUCTION != DONE`

`PRODUCTION` or `DONE` is allowed only when all relevant acceptance criteria are demonstrably satisfied.

## 2. Required evidence

Every material completion claim must be backed by the strongest applicable evidence:

- Git change: exact branch, commit SHA, and scoped diff/status evidence.
- Pull request: real PR number, state, and exact head SHA.
- Test/CI: commands actually executed, PASS/FAIL results, and exact commit/head where applicable.
- Deployment: real deployment identifier, target URL/domain, and production verification.
- Runtime/Desktop/UI: actual execution and observed behavior; do not infer runtime success from code inspection alone.
- File/artifact: real path and hash when integrity matters.

Never invent command output, test results, screenshots, runtime behavior, deployment state, provider behavior, or external service state.

## 3. Current reality beats memory

Always distinguish:

- `TARGET TRUTH`: intended architecture, specification, roadmap, or desired state.
- `CURRENT REALITY`: what code, tests, CI, runtime, deployment, and evidence prove now.

Live repository/runtime/CI/deployment evidence outranks prior chats, memory, stale status documents, plans, and assumptions.

## 4. Read before changing

Before editing a subsystem, inspect the relevant code, contracts, tests, dependency boundaries, and governing documentation.

Do not redesign the ILAIOS architecture or rewrite Core from scratch unless explicitly required by an approved architectural change.

Do not break working contracts for convenience.

Prefer small, reversible, reviewable changes with focused tests.

## 5. Protected governance boundaries

Treat the following as high-protection boundaries:

- Policy
- Approval
- Authorization
- Fencing
- Tenant isolation
- Evidence integrity
- Auditability

Do not bypass or weaken them for speed, convenience, performance, or implementation simplicity.

## 6. Execution honesty

Do not say an operation was performed unless it actually occurred through an available tool/runtime/service and the result was observed.

If authentication, quota, provider access, payment, deployment access, local runtime access, user interaction, or another external dependency blocks execution, report `BLOCKED` with the exact blocker and exact remaining work.

If a task stops midway, never close it as complete. Leave a precise continuation state.

## 7. Git safety

Unless explicitly requested and justified:

- Do not force-push.
- Do not rewrite published history.
- Do not delete user data or destructive resources.
- Do not commit secrets, API keys, tokens, credentials, private keys, or sensitive environment values.
- Do not expose secrets in logs or final responses.

Use feature branches for implementation work. Avoid direct development on `master` unless the user explicitly requests it and repository policy allows it.

## 8. Mandatory final evidence report

At the end of every implementation task, report:

- `CURRENT REALITY`
- `Files changed`
- `Branch`
- `Commit SHA`
- `Tests actually run`
- `Test results`
- `CI status`
- `Deployment status`
- `Runtime verification`
- `Blockers`
- `Exact remaining work`
- `Final maturity/status`

If an item was not executed or not observable, say so explicitly rather than guessing.

## 9. Completion rule

No evidence -> no `DONE`.
