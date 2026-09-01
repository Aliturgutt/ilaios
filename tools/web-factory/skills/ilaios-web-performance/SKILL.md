---
name: ilaios-web-performance
description: Evaluate provider-independent web performance using measurable budgets, rendering and asset analysis, runtime observations, and regression evidence without requiring Vercel-specific infrastructure.
---
# ILAIOS Web Performance
Status: IMPLEMENTED
Owner: ILAIOS

## Purpose
Keep Web Factory output fast through measurable budgets and regression evidence rather than framework folklore.

## Contract
1. Measure before optimizing; identify the actual bottleneck and affected user path.
2. Evaluate document weight, JavaScript execution, images/fonts, request waterfalls, caching, rendering and layout stability.
3. Prefer portable web-platform improvements before provider-specific optimizations.
4. Treat framework/CDN/provider optimizations as optional adapters behind the generic contract.
5. Do not trade accessibility, correctness, security, SEO or maintainability for synthetic benchmark gains.
6. Record before/after evidence for material optimizations.
7. Performance PASS cannot imply production readiness or deployment verification.

## Evidence
Capture measurement environment, representative route, budgets, before/after result, regression risk and remaining hotspots.
