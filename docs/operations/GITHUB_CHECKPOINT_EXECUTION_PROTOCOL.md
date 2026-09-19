# GitHub Checkpoint Execution Protocol

## Purpose

Long-running ILAIOS work must remain recoverable if an interactive session ends or times out. GitHub branch, commit, pull request, CI and evidence state are the durable execution checkpoints.

## Required execution model

For every non-trivial implementation:

1. Start from the current verified `master` HEAD; never reuse a stale SHA from conversation history.
2. Use a dedicated branch/PR for the bounded workstream. Do not develop directly on `master`.
3. Commit each meaningful atomic implementation checkpoint as soon as it is coherent. Do not hold several unrelated phases only in an interactive session.
4. Record the exact branch HEAD SHA before evaluating tests or CI.
5. Tests and gates must be attributable to that exact HEAD. A PASS from an older SHA is not reusable evidence.
6. If an interactive session ends, resume by re-reading repository, branch, PR, HEAD SHA, changed files and CI state from GitHub. Do not repeat already committed work.
7. Merge only when the exact PR head satisfies all required gates and the branch is still based on an acceptable current `master` state.
8. After merge, re-read `master` and run/verify any required exact-master gates before claiming the phase verified.
9. Begin the next bounded phase from the new verified `master` HEAD.

## Evidence rule

`PLAN != IMPLEMENTATION`

`COMMIT != MERGED`

`MERGED != CI VERIFIED`

`CI PASS != PRODUCTION VERIFIED`

No phase may be reported as DONE, VERIFIED, DEPLOYED or PRODUCTION without the evidence required for that maturity level.

## Timeout recovery checkpoint

A resumable checkpoint consists of at least:

- repository: `Aliturgutt/ilaios`
- branch
- exact branch HEAD SHA
- PR number when opened
- completed atomic scope
- current required CI/gate state
- remaining next atomic step
- blockers or external dependencies

When work resumes, GitHub is re-read first and this checkpoint is reconstructed from live state.

## Conflict isolation

Parallel Website design, Desktop design, runtime, provider and release work must not be mixed into one catch-all branch. Cross-cutting work should avoid editing design-owned files unless its contract explicitly requires it. Dependency order is preferred over large conflict-heavy rebases.

## Fail-closed rule

Unknown, stale, missing or unattributed evidence does not satisfy a gate. If the exact current state cannot be proved, report BLOCKED or NOT VERIFIED rather than inferring success.
