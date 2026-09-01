---
name: ilaios-web-e2e
description: Verify bounded non-mutating web journeys with BrowserQA evidence while preserving ILAIOS policy, approval, network and Tool Gateway boundaries.
---
# ILAIOS Web E2E
Status: IMPLEMENTED
Owner: ILAIOS

## Purpose
Execute read/navigation end-to-end checks against an explicitly authorized site and return evidence per acceptance criterion.

## Contract
Use only the governed `web.verify` BrowserQA capability. Every action must be persisted before Tool Gateway dispatch, must match the persisted requester/tenant/workflow/session/action/target binding, and must pass canonical admission and budget controls. Browser output must prove the observed URL and remain within the configured target set.

## Current boundary
BrowserQA currently has read/verification permissions, so v0 deliberately excludes click, press, type, fill, authentication, checkout, destructive or state-changing flows. Those capabilities require a separate canonical permission/capability decision and regression/security evidence; Approval alone does not widen an agent manifest.

A passing journey proves only the exact non-mutating flow observed. It does not prove deployment-to-SHA linkage, backend correctness, provider correctness, tenant isolation, or production readiness unless those are independently evidenced.
