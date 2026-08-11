# ILAIOS Post-v1 Automation Plan

Status: **DRAFT / NON-CANONICAL**

Purpose: define how automation may continue after v1 without modifying the current OpenClaw canonical controller until a governed post-v1 graph is adopted.

## Current controller boundary

The existing `dev/openclaw/MASTER_OPENCLAW.md` and `dev/openclaw/execution_plan.yaml` govern the current canonical namespace and release history. This governance package does not edit them.

A post-v1 controller amendment should be created only after the selected post-v1 workstream has explicit dependencies, scope, validations, evidence and approval rules.

## Automation responsibilities

Automation may:

1. read current `master` and evidence before every action;
2. revalidate selected capabilities;
3. create bounded branches and PRs;
4. update tests and documentation inside declared scope;
5. run/inspect CI where available;
6. close stale duplicate PRs when supersession is proven;
7. persist audit/evidence records;
8. stop dependent work when a required gate fails;
9. continue only truly independent ready work.

## Mandatory fail-closed rules

Automation must not:

- infer missing canonical authority;
- create a new production milestone by naming convention alone;
- weaken tests or checks;
- skip dependencies;
- rewrite Git history;
- force-push;
- mutate production infrastructure without explicit release authorization;
- create/rotate credentials or secrets without explicit authorization;
- make paid/provider purchases without explicit authorization;
- change DNS/domain ownership;
- perform signing or Store submission without the external prerequisites and approval;
- change Website or Desktop implementation from the repository-governance track;
- fabricate evidence or certification claims.

## Proposed execution loop

For each future post-v1 package:

1. **Resolve authority** — confirm the package is formally adopted and active.
2. **Verify dependencies** — every dependency must have durable accepted evidence.
3. **Capture pre-state** — branch, commit, relevant tests and current evidence.
4. **Bound scope** — allowed/forbidden paths and external-action boundary.
5. **Implement minimally** — preserve proven behavior.
6. **Targeted validation** — unit/integration/negative/e2e appropriate to scope.
7. **Repository validation** — applicable lint/type/test/pre-commit/diff gates.
8. **Persist evidence** — exact results, limitations and hashes where relevant.
9. **Create PR** — no direct risky master mutation.
10. **Inspect CI** — failures are NOT PASS.
11. **Merge only when allowed** — no automatic production promotion.
12. **Recompute ready set** — continue only with dependency-proven work.

## Automation state model

Use only:

- `READY`
- `RUNNING`
- `PASS`
- `FAIL`
- `BLOCKED`
- `NOT_SELECTED`

`BLOCKED` is a valid outcome and must not be converted to PASS to keep automation moving.

## External gates that automation must surface to the owner

Examples:

- GitHub repository/branch policy changes not available to the automation identity;
- legal/license choice;
- payment or developer-account verification;
- app-store declarations and signing identities;
- production-spend approval;
- new data-processing/privacy commitments;
- selection of the primary post-v1 product workstream.

## Recommended adoption process

1. merge this governance baseline;
2. finish Stage 1 capability revalidation;
3. owner selects the first post-v1 workstream;
4. convert only the selected branch of `post_v1_dependency_graph.draft.yaml` into a governed canonical amendment;
5. update `MASTER_OPENCLAW.md` / `execution_plan.yaml` in a dedicated controller PR;
6. validate the controller against a no-op/read-only dry run;
7. only then permit automatic implementation packages.

## Current conclusion

The automation framework is ready in principle, but the current canonical controller should remain unchanged until the post-v1 product selection gate is resolved. This avoids accidentally turning a planning proposal into production execution authority.
