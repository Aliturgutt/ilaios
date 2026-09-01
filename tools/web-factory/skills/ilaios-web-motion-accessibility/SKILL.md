---
name: ilaios-web-motion-accessibility
description: Enforce provider-independent accessibility requirements for animation, scroll effects, direct manipulation, and interactive showcases in generated Web Factory output.
---
# ILAIOS Web Motion Accessibility
Status: IMPLEMENTED
Owner: ILAIOS

## Purpose
Ensure dynamic presentation never makes content, navigation, controls, or state understanding depend on motion.

## Contract
1. Honor prefers-reduced-motion and provide equivalent static information/actions.
2. Do not use motion as the only signal for state, hierarchy, error, success, or navigation.
3. Avoid non-interruptible motion, focus displacement, keyboard traps, and hover-only semantics.
4. Keep touch/coarse-pointer fallbacks functional without precision pointer tracking.
5. Prevent scroll-jacking and motion that blocks normal document navigation.
6. Maintain readable contrast, target size, focus visibility, and text scaling under dynamic states.
7. Fail closed on missing motion-accessibility evidence in acceptance paths that use dynamic behavior.

## Evidence
PASS requires observed reduced-motion, keyboard, touch/coarse-pointer, focus, and fallback checks across required viewport/locale coverage.
