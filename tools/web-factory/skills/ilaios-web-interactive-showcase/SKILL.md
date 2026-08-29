---
name: ilaios-web-interactive-showcase
description: Provider-independent Produce bounded interactive product, media, architecture, or system showcases with context-derived behavior and complete static fallbacks.
---
# ILAIOS Web Interactive Showcase
Status: IMPLEMENTED
Owner: ILAIOS

## Purpose
Create high-value interactive presentation surfaces without turning every site into a demo-heavy template.

## Contract
1. Activate interactive showcase behavior only when context and content justify it.
2. Preserve a complete static representation with the same primary information and actions.
3. Keep pointer/scroll effects local, bounded, and performance-budgeted.
4. Asset-led showcases must use admitted assets and preserve provenance; no remote executable content is implicitly trusted.
5. 3D/WebGL is optional capability, not a required dependency for ordinary generated sites.
6. On unsupported devices, coarse pointers, reduced motion, or runtime failure, degrade to the static equivalent.
7. Showcase presentation may not access privileged cookies, secrets, control-plane APIs, or provider credentials directly.

## Evidence
PASS requires generated-source, fallback, input-mode, performance, and browser runtime evidence. Visual intent alone is insufficient.
