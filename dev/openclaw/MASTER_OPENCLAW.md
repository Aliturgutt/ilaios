# MASTER_OPENCLAW.md

## 1. PURPOSE

OpenClaw is a temporary deterministic development actuator for this repository. It executes bounded work only and MUST NOT become a released ILAIOS runtime/product dependency.

OpenClaw does not redesign architecture, invent requirements, infer missing authority, bypass dependencies, bypass approvals, or promote release state.

## 2. CANONICAL AUTHORITY

Use these authorities in order:

1. `ILAIOS_Master_Implementation_Specification_v1_0_CANONICAL_FINAL.docx`
2. `ILAIOS_Canonical_Milestone_Manifest_v1_0.docx`
3. `docs/canonical/ILAIOS_ENTERPRISE_AI_OPERATING_SYSTEM_CANONICAL_ARCHITECTURE.md` for product architecture and engineering requirements; it does not override implementation or promotion order.
4. `dev/openclaw/execution_plan.yaml`
5. the active bounded package

Repository state, tests, static checks, CI/runtime evidence, and durable evidence determine actual completion. A lower authority never overrides a higher authority.

## 3. CANONICAL IDS

Only these execution IDs are valid:

- `PRE.S00`
- `VIDEO.V01` through `VIDEO.V30`
- `PRE.S01`
- `PLATFORM.P00` through `PLATFORM.P20`
- `RELEASE.R00` through `RELEASE.R03`

Legacy Mxx/Axx labels are traceability metadata only.

## 4. PACKAGE REQUIREMENTS

Before executing a milestone, `execution_plan.yaml` must explicitly provide:

- milestone_id
- package_id
- dependencies
- allowed_paths
- forbidden_paths
- actions
- validations
- requirements
- evidence_requirements
- approvals
- budget_policy
- rollback
- stop_conditions
- expected_post_state
- commit_policy
- status

Missing or conflicting data is not inferred.

## 5. DEPENDENCY GATE

A milestone may execute only when every declared dependency has durable PASS evidence and repository/runtime evidence does not contradict it.

Never skip dependencies. Declared parallelism only: after `PLATFORM.P02`, `PLATFORM.P03` and `PLATFORM.P04` may run independently; `PLATFORM.P05` requires both PASS.

## 6. SCOPE CONTROL

Every action must be explicitly authorized and remain inside `allowed_paths` and outside `forbidden_paths`. Never modify unrelated files or canonical authority documents.

## 7. EXECUTION LOOP

For each READY milestone:

1. verify dependencies;
2. capture pre-state;
3. execute only listed actions;
4. run all listed validations;
5. capture post-state;
6. decide PASS / FAIL / BLOCKED;
7. persist exact evidence;
8. commit/push only when policy permits and all required gates PASS;
9. recompute the READY set.

A command completing is not enough for PASS.

## 8. NON-BLOCKING PROJECT CONTINUATION

A failed milestone is NEVER converted to PASS and a dependency is NEVER bypassed.

On FAIL or BLOCKED:

1. persist exact failure evidence;
2. do not commit defective partial work;
3. execute only the package-defined rollback when needed;
4. recompute the canonical dependency graph;
5. continue automatically with any other READY milestone whose dependencies are independently proven PASS;
6. mark downstream milestones that depend on the failed/blocked milestone as BLOCKED/UNREACHABLE for the current run;
7. continue until no READY milestone remains.

This rule prevents one independent failure from stopping unrelated reachable work. It does NOT authorize execution of a dependent milestone whose predecessor failed.

## 9. VALIDATION

Use exactly the active package validations. Failed, missing, ambiguous, or unavailable required validation means NOT PASS. Never disable checks, weaken tests, hide defects, or fabricate evidence.

## 10. COMMIT / PUSH

Commit/push only when the active package permits it, validations PASS, required evidence exists, and only allowed changes are included. Never force-push unless explicitly authorized.

## 11. ROLLBACK

Use only rollback actions explicitly declared by the active package. Never invent recovery or rewrite pushed Git history.

## 12. PROHIBITED AUTONOMY

OpenClaw MUST NOT independently:

- redesign binding architecture;
- change security boundaries or policy priority;
- change ExecutionGrant semantics;
- bypass verifier, Secrets, DLP, HITL, FinOps, budget, pricing, or approval requirements;
- invent milestone IDs or requirements;
- skip dependencies;
- rewrite proven video behavior unnecessarily;
- perform autonomous direct production mutation;
- promote ReleaseState;
- make OpenClaw a runtime/product dependency.

## 13. IDENTITY MIGRATION

`PLATFORM.P00` freezes the migration baseline. `PLATFORM.P01` performs the controlled identity migration. Preserve Git history and historical Hermes provenance.

## 14. RELEASE

`PLATFORM.P20 PASS` creates promotion eligibility evidence only. It does not mean production.

Release order is strictly:

`RELEASE.R00 -> RELEASE.R01 -> RELEASE.R02 -> RELEASE.R03`

R01/R02/R03 require explicit human promotion decisions. OpenClaw may prepare/validate release evidence but never autonomously promote release state.

## 15. EVIDENCE

Normal evidence lives under `dev/openclaw/evidence/`. Evidence must prove what was inspected, what changed, exact commands/results, validations, Git state before/after, and milestone decision.

## 16. FAILURE REPORT

For every FAIL/BLOCKED/STOP evidence bundle include:

- milestone ID;
- status;
- failed condition;
- exact action/command;
- relevant path/symbol;
- exit code/result;
- evidence path;
- rollback state;
- downstream impact.

After reporting, continue only with independent READY work as defined in section 8.

## 17. SUCCESS ADVANCE

On PASS, persist durable evidence, apply commit/push policy, reread `execution_plan.yaml`, and automatically execute the next READY milestone. Do not ask for routine approval between ordinary PASS milestones.

## 18. CURRENT CONTINUATION

`PRE.S00` and `VIDEO.V01` through `VIDEO.V30` have already been executed under prior bounded packages. Their durable evidence remains authoritative only where repository state does not contradict it.

The continuation plan begins at `PRE.S01`, then follows the canonical PLATFORM and RELEASE dependency graph.
