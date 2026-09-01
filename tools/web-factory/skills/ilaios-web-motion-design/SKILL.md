---
name: ilaios-web-motion-design
description: Design provider-independent motion behavior for Web Factory outputs using ILAIOS-native hierarchy, continuity, causality, performance, and accessibility contracts.
---
# ILAIOS Web Motion Design
Status: IMPLEMENTED
Owner: ILAIOS

## Purpose
Turn static composition into deliberate motion that explains hierarchy, state, continuity, or causality without becoming decorative noise.

## Contract
1. Derive motion intensity from DesignContext/DesignStrategy; do not apply universal reveal choreography.
2. Prefer transform/opacity and bounded compositor-friendly effects before expensive runtime animation.
3. Keep motion interruptible, reversible where appropriate, and spatially continuous.
4. Use motion only when it improves comprehension, navigation, direct manipulation, or product presentation.
5. Require reduced-motion static equivalence and preserve the same information/actions when motion is disabled.
6. Keep third-party animation engines optional adapters; the canonical behavior contract remains ILAIOS-owned and provider-independent.
7. Do not let motion code gain Policy, Approval, Tool Gateway, credential, tenant, or execution authority.

## Evidence
PASS requires generated-source evidence plus browser-observed motion behavior at required viewport/input modes. Source presence alone is not verification.
