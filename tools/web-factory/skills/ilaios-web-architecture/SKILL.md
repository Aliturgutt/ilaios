---
name: ilaios-web-architecture
description: Plan provider-independent website structure, routes, data boundaries, rendering strategy, integration contracts, and deployment constraints for governed ILAIOS Web Factory work.
---
# ILAIOS Web Architecture
Status: IMPLEMENTED
Owner: ILAIOS

## Purpose
Turn an admitted website objective into a bounded architecture plan without binding the product to Vercel, Next.js, React, or any single provider/framework.

## Contract
1. Inspect incumbent repository and product truth before proposing structure.
2. Define routes, rendering mode, state/data boundaries, API contracts, assets, auth and persistence needs.
3. Prefer the smallest architecture that satisfies the objective.
4. Preserve tenant, policy, approval, Tool Gateway, validation, audit and evidence boundaries.
5. Do not create a parallel Core, router, scheduler, policy engine or deployment authority.
6. Framework/provider-specific choices are adapters, never the skill contract.
7. Flag irreversible migrations, lock-in, secret handling, production mutation and paid-service requirements.

## Evidence
Output must identify assumptions, affected surfaces, dependency order, acceptance gates and unresolved blockers. Architecture planning alone is not implementation or production evidence.
