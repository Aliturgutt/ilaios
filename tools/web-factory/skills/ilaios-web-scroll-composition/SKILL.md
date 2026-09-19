---
name: ilaios-web-scroll-composition
description: Design and validate scroll-linked composition, progress, sticky sequencing, and narrative continuity for provider-independent Web Factory output.
---
# ILAIOS Web Scroll Composition
Status: IMPLEMENTED
Owner: ILAIOS

## Purpose
Use scrolling as an information and continuity mechanism rather than an unbounded animation trigger.

## Contract
1. Choose standard, section-linked, or narrative-linked scroll behavior from project context.
2. Scroll work must be passive and animation-frame bounded; avoid layout thrash and synchronous heavy work.
3. Sticky or progressive sections must preserve reading order, landmarks, and keyboard navigation.
4. Scroll effects must not block access to content or require precise gesture timing.
5. Reduced-motion mode must remove scroll-linked movement while keeping semantic sequence intact.
6. Mobile layouts may recompose or simplify instead of mechanically shrinking desktop effects.
7. Scroll state never grants execution authority or bypasses canonical Web runtime governance.

## Evidence
PASS requires browser evidence for smoothness, no overflow/overlap, reduced-motion behavior, and mobile/desktop composition parity.
