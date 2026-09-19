# ILAIOS 47-Agent Runtime Integration Red-Team

Integration branch: `agent/47-agent-runtime-redteam`

## Objective
Safely move the canonical agent execution/runtime work onto current `master` without creating a second Core, scheduler, router, policy engine, evidence store, or agent engine.

## Merge facts
- Current master at integration start: `08cc5a42ad604be0cead3e1d657b9bdb5a492e5c`.
- Legacy P0 branch head: `492d5eb015b25498454ee4d8a3b8ad0a9f4dc1f4`.
- The P0 branch is 57 commits ahead and 32 commits behind current master.
- Semantically overlapping post-merge-base files are `services/named_agent_executor.py` and `services/runtime/execution.py`; these require manual semantic merge.
- Static registry promotion is forbidden. Registry presence is identity/governance only; effective EXECUTABLE/VERIFIED state must be evidence-derived.

## Required completion sequence
1. Integrate P0 runtime/readiness/evidence/provider code into current master.
2. Bind `OPENROUTER_API_KEY` to the canonical agent provider runtime, not only Video Factory.
3. Verify the 5 Core + 10 Engineering + 6 defensive Security P0 agents with real execution/evidence gates.
4. Bind Web/Media/Intelligence (P1) and Operations/Meta (P2) through the same runtime and factory/tool boundaries.
5. Preserve the already-merged authenticated `/v1/agents/state` and `/v1/agents/commands` Desktop provisioning boundary.
6. Complete the approved Agents UI binding and live telemetry projection.
7. Run the 47-agent matrix and exact-head repository/Desktop/Windows/MSIX gates.
8. Promote readiness only from persisted execution and independent-verification evidence.

## Security invariants
- No caller-supplied authority/capability widening.
- No arbitrary external offensive Security execution.
- No API key persisted in source, logs, Desktop state, or evidence payloads.
- Provider failure, quota exhaustion, budget exhaustion, missing verifier evidence, malformed output, or evidence-store failure must fail closed.
