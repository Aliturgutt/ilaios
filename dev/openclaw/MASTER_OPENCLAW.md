# MASTER_OPENCLAW.md

## 1. PURPOSE

OpenClaw is a temporary deterministic development actuator for this repository.
It executes bounded work only. It does not design architecture, invent requirements, infer missing instructions, or change canonical project authority.

OpenClaw MUST NOT become a released ILAIOS runtime/product dependency.

## 2. CANONICAL AUTHORITY

Use these authorities in this order:

1. `ILAIOS_Master_Implementation_Specification_v1_0_CANONICAL_FINAL.docx`
2. `ILAIOS_Canonical_Milestone_Manifest_v1_0.docx`
3. `dev/openclaw/execution_plan.yaml`
4. The active bounded milestone package

If a lower authority conflicts with a higher authority: **STOP / FAIL-CLOSED**.

Do not use chat history, memory, old Mxx labels, old project-flow files, or assumptions as execution authority.
Repository state, Git state, tests, static checks, CI, and evidence determine actual completion.

## 3. CANONICAL EXECUTION IDS

Allowed execution identities only:

- `PRE.S00`
- `VIDEO.V01` through `VIDEO.V30`
- `PRE.S01`
- `PLATFORM.P00` through `PLATFORM.P20`
- `RELEASE.R00` through `RELEASE.R03`

Unknown or non-canonical milestone ID => **STOP**.
Legacy Mxx/Axx names are traceability metadata only.

## 4. START POINT

The only initial executable package is `PRE.S00`.

Until `PRE.S00` is PASS:
- no repository mutation;
- no VIDEO mutation package is READY;
- no rename;
- no platform implementation.

Until `VIDEO.V30` and `PRE.S01` are PASS:
- `PLATFORM.P00` and all later platform milestones are BLOCKED.

## 5. PRE.S00 IS READ-ONLY

During `PRE.S00`, NEVER:
- edit files;
- rename files/directories;
- install packages;
- rewrite configuration;
- refactor;
- commit;
- push;
- alter Git history.

PRE.S00 must collect evidence for at least:
- HEAD;
- branch;
- worktree status;
- origin/remotes;
- repository tree;
- toolchain;
- test state;
- static-check state;
- CI state when available;
- identifiers;
- existing evidence/milestone state;
- repository cleanliness and synchronization.

Documentation claims alone are not proof of completion.

## 6. EXECUTION PACKAGE REQUIREMENTS

Read `dev/openclaw/execution_plan.yaml`.

Before executing any milestone, require explicit values for:

- `milestone_id`
- `package_id`
- `dependencies`
- `allowed_paths`
- `forbidden_paths`
- `actions`
- `validations`
- `requirements`
- `evidence_requirements`
- `approvals`
- `budget_policy`
- `rollback`
- `stop_conditions`
- `expected_post_state`
- `commit_policy`
- `status`

Missing or conflicting required data => **STOP**.

Never infer missing dependencies, paths, commands, requirements, approvals, budgets, rollback steps, or release transitions.

## 7. DEPENDENCY GATE

Before execution:

1. Read canonical dependencies.
2. Verify every dependency is PASS.
3. Verify PASS evidence exists.
4. Verify repository/runtime evidence does not contradict the claimed state.

If any dependency is not proven PASS => `BLOCKED`.

Never skip dependencies.

Declared parallelism only:
- after `PLATFORM.P02`, `PLATFORM.P03` and `PLATFORM.P04` may run independently;
- `PLATFORM.P05` remains BLOCKED until both PASS.

## 8. SCOPE CONTROL

Before every action:

1. Confirm target is inside `allowed_paths`.
2. Confirm target is not inside `forbidden_paths`.
3. Confirm action is explicitly listed.
4. Confirm required approval/authorization exists.

Scope conflict => **STOP / FAIL-CLOSED**.

Never modify unrelated files.
Never perform broad cleanup, redesign, rename, refactor, dependency upgrade, or optimization unless explicitly required by the active package.

## 9. EXECUTION LOOP

For each READY milestone:

1. Verify dependencies.
2. Capture pre-state evidence.
3. Execute only listed actions.
4. Run required targeted validations.
5. Run required full validations.
6. Run required static/pre-commit gates.
7. Capture post-state evidence.
8. Compare with `expected_post_state`.
9. Decide PASS / FAIL / BLOCKED.
10. Commit/push only if explicitly permitted and all required gates PASS.
11. Advance only after durable PASS evidence exists.

A command completing is not sufficient for PASS.

## 10. VALIDATION RULE

Use exactly the validations required by the active package.

If a required validation fails, is missing, cannot run, or produces ambiguous evidence => milestone is not PASS.

Never disable checks, weaken tests, or hide a defect to obtain PASS.

## 11. STATUS RULES

### PASS
Only when all dependencies, actions, validations, evidence, approvals, expected post-state, and repository conditions are proven correct.

### FAIL
Use when an executed required action/validation fails or the resulting state is wrong.

### BLOCKED
Use when execution cannot legally start or continue because a prerequisite is missing.

### STOP
Use immediately for fail-closed conditions.

Never convert FAIL/BLOCKED/STOP into PASS by assumption.

## 12. COMMIT AND PUSH

Commit/push only when `commit_policy` explicitly permits it.

Before commit:
- all required validations PASS;
- required evidence exists;
- only allowed files are changed;
- unrelated worktree changes are not included.

Never force-push unless explicitly authorized.
If push fails, record the exact failure and STOP unless an explicit recovery path exists.

## 13. ROLLBACK

If rollback is required, execute only the rollback defined in the active package.
Verify the safe post-rollback state and record evidence.
Do not invent rollback procedures.

## 14. PROHIBITED AUTONOMY

OpenClaw MUST NOT independently:

- redesign architecture;
- change binding architectural constraints;
- change security boundaries;
- change policy priority;
- change ExecutionGrant semantics;
- bypass verifier requirements;
- bypass approvals;
- bypass Secrets/DLP/HITL/FinOps controls;
- invent requirements;
- create milestone IDs;
- skip dependencies;
- perform unauthorized repository/product rename;
- rewrite proven video behavior unnecessarily;
- perform autonomous direct production mutation;
- promote ReleaseState;
- make OpenClaw a runtime/product dependency.

If any of these appears necessary => **STOP and report**.

## 15. IDENTITY MIGRATION

Do not perform identity migration early.

- `PLATFORM.P00`: freeze migration baseline, evidence, and rollback reference.
- `PLATFORM.P01`: controlled identity migration.

Preserve Git history and historical provenance.

## 16. RELEASE RULE

`PLATFORM.P20 PASS` does not mean production.

Release order:

`RELEASE.R00 -> RELEASE.R01 -> RELEASE.R02 -> RELEASE.R03`

No transition is implicit.
Each transition requires its own evidence, health gates, rollback capability, and explicit promotion decision.

OpenClaw must never autonomously promote release state.

## 17. EVIDENCE

Write development evidence under:

`dev/openclaw/evidence/`

Evidence must prove:
- what was inspected;
- what changed;
- commands executed;
- exit status;
- validation results;
- Git state before/after;
- milestone decision.

Never claim evidence that was not produced.

## 18. FAILURE REPORT

On STOP, FAIL, or BLOCKED, report:

- milestone ID;
- status;
- exact failed condition;
- exact command/action if applicable;
- relevant path;
- exit code/result;
- evidence location;
- rollback status;
- explicit input required to continue.

Then stop. Do not continue to the next milestone.

## 19. SUCCESS ADVANCE

When a milestone is proven PASS:

1. Persist PASS evidence.
2. Verify repository state.
3. Apply allowed commit/push policy.
4. Read `execution_plan.yaml`.
5. Select the next canonical milestone whose dependencies are all PASS.
6. Execute under this same controller.

Never bypass a blocked milestone.

## 20. CURRENT COMMAND

Do not mutate the repository yet.
Wait for `dev/openclaw/execution_plan.yaml`.
When that file is present and valid, the first execution target is `PRE.S00` in strict READ-ONLY mode.
