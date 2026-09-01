---
name: ilaios-video-prompt
description: Compile admitted cinematic shots and canonical continuity state through the existing provider-agnostic ShotPromptCompiler while keeping provider/model controls outside prompt compilation.
---

# ILAIOS Video Prompt

Use this skill after shot planning and continuity binding when Video Factory needs a deterministic provider-agnostic prompt package.

## Canonical execution

This skill delegates prompt compilation to the existing `ShotPromptCompiler`. It does not create a second prompt engine.

The upstream skill methodology is used only as guidance for how admitted shot intent should be prepared: chronological action, motivated camera motion, explicit reference intent, audio intent where supported downstream, and a stable ending state.

Model/provider names, credentials, commercial routing, resolution, and adapter-specific API parameters remain outside canonical prompt compilation.

## Boundaries

The skill does not invoke providers, select routes, mutate media, or bypass M04/M05 and governance.

See `references/model-guidance.md` for provider-replaceable prompting guidance. Exact provider schemas remain adapter concerns.
