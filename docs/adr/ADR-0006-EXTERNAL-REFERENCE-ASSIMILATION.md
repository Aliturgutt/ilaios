# ADR-0006 — External Open-Source References Are Assimilated, Not Made Product Authority

**Status:** Accepted — Canonical Rationale  
**Date:** 2026-08-13  
**Authority:** This ADR records rationale only and does not override canonical documents.

## Context

ILAIOS can learn from external open-source projects and skill repositories such as routing systems, editors, research UX patterns, or design-engineering skills. Directly making those repositories critical runtime authority creates upstream availability, supply-chain, licensing, and architectural dependency risk.

## Decision

The default path is: **pin source → license review → security/supply-chain review → study behavior → extract requirements → write ILAIOS specification → implement ILAIOS-native behavior/skill → test → independently evaluate → record provenance/evidence → register → release**. A critical ILAIOS capability must not require an upstream skill repository to remain available, unchanged, or trustworthy at runtime.

## Consequences

- Taste/Emil-style skills are design-intelligence references, not mandatory runtime dependencies.
- OpenCut-style systems may inform video editing semantics without becoming a second Video Engine.
- External routing systems may inform routing but cannot become ILAIOS routing authority.
- Direct third-party runtime dependencies require explicit approval, licensing/security review, and bounded contracts.

## Canonical References

- `../SYSTEM_ARCHITECTURE.md`
- `../DEPENDENCY_GRAPH.md`
- `../THREAT_MODEL.md`
- `../ENGINEERING_STANDARDS.md`
- `../GOVERNANCE.md`
