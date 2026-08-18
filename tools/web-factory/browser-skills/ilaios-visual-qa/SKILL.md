---
name: ilaios-visual-qa
description: Capture read-only visual and rendered-page evidence for authorized Web Factory targets without inferring backend, deployment or production truth.
---
# ILAIOS Visual QA
Status: IMPLEMENTED
Owner: ILAIOS

## Purpose
Collect snapshots/screenshots and inspect observable rendered states for Web Factory validation.

## Contract
Operate only through BrowserQA `web.verify`, Tool Gateway, persisted governance work and the egress-enforced browser adapter. Check observable hierarchy, required text, visible overflow/breakage, rendered assets and declared viewport outcomes when the test setup supplies them.

## Limits
Appearance cannot prove backend integration, auth correctness, database state, provider E2E, deployment identity, tenant isolation or release maturity. No DOM mutation, arbitrary code, form entry, credentials, storage/cookie changes, uploads/downloads, permission grants or direct browser process access.

Missing or ambiguous visual evidence is reported as unresolved, never promoted to PASS.
