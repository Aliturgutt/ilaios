# ILAIOS Desktop Work Checkpoint

Temporary evidence-only checkpoint for Desktop functional closure. CURRENT REALITY only; this file is not a runtime authority and must not replace canonical Core/control-plane/router/scheduler/governance/evidence authorities.

## Current phase

- Phase: Agents functional closure
- Working branch: `desktop/agents-functional-closure-master-sync`
- Fresh base: `master@94a2f5c2647dbc32ae380ede1c01ccd98b0ed1a2`
- Supersedes stale-base work from PR #433 without rewriting its history.
- Merge-base-to-master audit showed no overlap between the 27 intervening master commits and the four Agents code/test paths, so the Agents change can be replayed onto current master without discarding master work.

## Failure and bounded repair evidence

Previous PR #433 exact head `ac8e5ea73a487d668ebc531b3b784ce46035265c`:

- Required CI Gate: PASS
- Software Factory Final Evidence: PASS
- ILAIOS Desktop CI: FAIL
- ILAIOS Desktop Windows Gate: FAIL
- ILAIOS Desktop MSIX Packaging: FAIL

The three Desktop failures stopped in the same regression test: `agent_controls_test.dart` / `New Agent provisions only the server-projected canonical identity`. GitHub Actions logs showed `RenderShrinkWrappingViewport does not support returning intrinsic dimensions` from the canonical-agent provisioning `AlertDialog`.

Bounded repair: replace the shrink-wrapped viewport with an explicitly bounded `SizedBox` and normal scrollable list. The existing provisioning regression remains unchanged. No new authority, capability, permission, assignment, telemetry, credential, provider, identity, policy, or approval path is introduced.

## Merge gate

Do not merge the active Agents phase until the exact active PR head has PASS evidence for all five:

- ILAIOS Desktop CI
- ILAIOS Desktop Windows Gate
- ILAIOS Desktop MSIX Packaging
- Required CI Gate
- Software Factory Final Evidence

Assignment and other actions remain explicitly unavailable unless a governed API and canonical authority path are proven.

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

Microsoft OIDC/App Registration remains an agreed external dependency; never fabricate it.
