---
name: ilaios-video-model-fit-analysis
description: Produce deterministic model-capability fit advice from M04 capability profiles and an admitted video prompt contract; never select or invoke a provider and never authorize spend.
---

# ILAIOS Video Model Fit Analysis

Use this skill when Video Factory has an admitted input mode and prompt form and needs advisory model-capability filtering before canonical provider selection.

## Inputs

- required input mode,
- prompt form,
- native-audio requirement,
- reference-asset requirement,
- caller-supplied M04 model capability profiles.

## Output

Return an ordered list of model IDs whose declared capabilities satisfy the request, with one rationale per candidate.

## Boundaries

This is advisory capability-fit analysis only. It is not routing authority.

It must not:

- choose a provider account,
- emit a canonical routing decision,
- call M05 on behalf of the runtime,
- bypass provider policy,
- infer pricing or free eligibility,
- use credentials,
- perform network discovery,
- dispatch generation.

M05 Provider Selection Engine remains authoritative for the actual provider route. See `references/model-capability-guidance.md`.
