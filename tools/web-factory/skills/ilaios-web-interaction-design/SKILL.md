---
name: ilaios-web-interaction-design
description: Provider-independent Produce bounded, accessible interaction behavior for Web Factory outputs across pointer, touch, keyboard, focus, direct manipulation, and state feedback.
---
# ILAIOS Web Interaction Design
Status: IMPLEMENTED
Owner: ILAIOS

## Purpose
Make generated sites feel responsive and intentional while keeping every interaction understandable, accessible, and bounded.

## Contract
1. Every interactive surface must expose a clear affordance and non-hover-only path.
2. Pointer effects must remain local to their surface, interruptible, and disposable without corrupting state.
3. Keyboard, focus, touch, and coarse-pointer behavior must remain first-class acceptance paths.
4. Feedback must begin at interaction start and remain continuous through completion or cancellation.
5. Decorative interaction may never obscure content, trap input, or create hidden authority.
6. Prefer native browser/React behavior before adding runtime dependencies.
7. Interaction failure must degrade to a complete static/standard control, not a broken partial state.

## Evidence
PASS requires browser interaction evidence for pointer, keyboard, touch/coarse-pointer fallback, and cleanup/recovery behavior.
