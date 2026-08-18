---
name: ilaios-video-model-routing
description: Produce a deterministic advisory model-capability recommendation without selecting or invoking a provider.
---

# ILAIOS Video Model Routing

## Purpose

Match a Video Factory request to an eligible model capability profile while preserving canonical M05 provider-selection authority.

## Authority boundary

This skill is advisory only. It does not select providers, inspect credentials, spend budget, call external services, mutate provider registry state, or override policy.

## Inputs

- required input mode
- effective duration
- audio requirement
- reference-asset requirement
- first/last-frame requirement
- caller-supplied model capability candidates

## Output

Return `ModelRoutingRecommendation` from `src.video_automation.prompting_skills.VideoModelRoutingAdvisor`.

The recommendation contains a model ID and reason only. It contains no provider endpoint or execution grant.

## Rules

1. Filter candidates strictly by declared capabilities.
2. Never infer unsupported capabilities.
3. Use deterministic ordering when multiple candidates satisfy the same request.
4. Do not optimize by price, provider availability, tenant policy, or credentials here; those remain canonical platform responsibilities.
5. The selected model ID is advisory input to downstream provider-neutral prompt work and canonical M05 selection.
6. Fail closed when no candidate satisfies all required capabilities.

## Forbidden behavior

Creating a second provider router, bypassing `ProviderSelectionEngine`, dispatching a provider request, or treating a recommendation as execution evidence is prohibited.
