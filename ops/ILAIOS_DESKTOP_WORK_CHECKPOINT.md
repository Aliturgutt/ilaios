# ILAIOS Desktop Work Checkpoint

This file is a temporary, evidence-only checkpoint for Desktop functional closure. It records CURRENT REALITY only; it is not product authority and must not replace canonical Core/control-plane/router/scheduler/governance/evidence authorities.

## Current phase

- Phase: Agents functional closure
- Active PR: #433 (`desktop/agents-functional-closure`)
- Current master observed before this checkpoint update: `94a2f5c2647dbc32ae380ede1c01ccd98b0ed1a2`
- Agents code fix parent/head before checkpoint commit: `f238be45b01ab1fd4f179b9443ebd91a93515749`
- Branch relation at that point: diverged from master, 10 commits ahead / 27 behind; merge base `3d37597993172e2046ea487fe587ea360005c796`.

## Current evidence

Previous exact-head `ac8e5ea73a487d668ebc531b3b784ce46035265c`:

- Required CI Gate: PASS
- Software Factory Final Evidence: PASS
- ILAIOS Desktop CI: FAIL
- ILAIOS Desktop Windows Gate: FAIL
- ILAIOS Desktop MSIX Packaging: FAIL

Root cause from failing Desktop test jobs: the canonical-agent provisioning dialog used a shrink-wrapped `ListView` under `AlertDialog` intrinsic sizing, producing `RenderShrinkWrappingViewport does not support returning intrinsic dimensions` in `agent_controls_test.dart` (`New Agent provisions only the server-projected canonical identity`). Windows Gate and MSIX stopped at the same Desktop test stage.

Bounded repair committed as `f238be45b01ab1fd4f179b9443ebd91a93515749`: the dialog now supplies explicit bounded dimensions and uses a normal scrollable list; the existing provisioning regression test remains intact. No authority, policy, capability, assignment, telemetry, credential, provider, or identity semantics were expanded.

## Merge gate

Do not merge this phase until the exact active PR head has PASS evidence for all of:

- ILAIOS Desktop CI
- ILAIOS Desktop Windows Gate
- ILAIOS Desktop MSIX Packaging
- Required CI Gate
- Software Factory Final Evidence

Also reconcile the active branch with current `master` before final merge/certification; stale-base CI is not exact-master evidence.

## Closure sequence

1. Agents
2. Approvals
3. Governed Live Workspace read projections
4. Workspace actions through Policy / Approval / Tool Gateway
5. Outputs lifecycle
6. Evidence
7. Costs / FinOps
8. Settings persistence and integrations truthfulness
9. Global shell action audit
10. Telemetry producers
11. Golden Windows E2E
12. Exact-master Windows certification/package

Assignment and any other action remain explicitly unavailable unless a governed API and canonical authority path are proven. Microsoft OIDC/App Registration is an agreed external dependency and must not be fabricated.
