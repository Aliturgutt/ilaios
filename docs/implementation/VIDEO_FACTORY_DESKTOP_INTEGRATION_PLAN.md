# Video Factory Desktop Integration Plan

Status: implementation branch in progress.

Red-team finding: Desktop one-prompt video execution currently routes through a deterministic placeholder motion-graphics runtime and can emit `video.desktop.finished_product` / ACCEPTED without proving the requested cinematic content was generated.

Required target path:

1. Parse the user objective into an explicit video request/specification.
2. Build canonical script, scene and shot plans.
3. Carry character/object/world continuity across shots.
4. Compile provider-neutral shot prompts.
5. Select an admitted real video-generation provider.
6. Submit asynchronous generation jobs, poll to terminal state, retrieve and verify generated media.
7. Assemble generated shots with the canonical editing/audio/caption pipeline.
8. Run technical validation and independent semantic/perceptual QA.
9. Run bounded selective repair where possible.
10. Emit ACCEPTED and a user-deliverable MP4 only after all required acceptance evidence passes.

Additional P0 defects discovered during live testing:

- Negated text such as `do not publish` must not be classified as a publish side effect.
- Repeated equivalent user requests must not fail with `proposal identity collision`; proposal content identity and execution/run identity must be distinct.
- Coordinator evidence records (`admitted`, `accepted`, `blocked`) must not appear as user finished-product deliveries.

This document is intentionally limited to the implementation contract; mutable progress belongs in evidence/CI/PR state.