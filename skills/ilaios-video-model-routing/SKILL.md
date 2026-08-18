---
name: ilaios-video-model-routing
description: Produce deterministic model-capability candidate advice from M04 capability profiles and an admitted video prompt contract; never select or invoke a provider and never authorize spend.
---

# ILAIOS Video Model Routing

Use this skill when Video Factory has an admitted input mode and prompt form and needs to narrow model candidates before canonical provider selection.

## Inputs

- required input mode,
- prompt form,
- native-audio requirement,
- reference-asset requirement,
- caller-supplied M04 model capability profiles.

## Output

Return an ordered list of model IDs whose declared capabilities satisfy the request, with one rationale per candidate.

## Boundaries

This is advisory capability filtering only.

It must not:

- choose a provider account,
- call M05 on behalf of the runtime,
- bypass provider policy,
- infer pricing or free eligibility,
- use credentials,
- perform network discovery,
- dispatch generation.

M05 Provider Selection Engine remains authoritative for the actual provider route. See `references/model-capability-guidance.md`.
