# Model guidance

This file captures ILAIOS-native, provider-replaceable prompting heuristics learned from public model documentation and reference implementations. It is not copied prompt text and is not provider execution authority.

## Cross-model invariants

- Choose input mode before composing.
- Image-to-video should animate the admitted anchor rather than redundantly redesign it.
- Reference-driven generation should give each asset a narrow job and explicitly exclude unwanted transfer.
- Long or complex shots should use chronological state transitions and a deliberate ending state.
- Camera direction should include composition, movement, motivation, and stopping point.
- Audio should be aligned to visible causes and dialogue/performance beats.
- Generation controls stay outside prompt prose unless a downstream model adapter requires a strict schema field.

## Adapter notes

- Seedance 2.x family: strong reference-role, audio, edit/extend, and timeline-oriented prompting; complex shots benefit from explicit starting state, ordered beats, continuity, and ending state.
- Veo 3.x family: concise cinematography + subject + action + context + style/ambience structure; audio can be directed as dialogue, effects, and ambient sound.
- Wan 2.x family: text generation benefits from subject + scene + motion; image-conditioned generation should emphasize motion and camera over restating the image.
- LTX 2.x family: distinguish single-shot, multi-shot, screenplay/dialogue, image-conditioned, and edit workflows; cuts should be explicit and continuity re-established.
- MiniMax H3 family: some modes require strict structured schemas and timing/reference alignment. The downstream adapter must own those exact formatting requirements.

ILAIOS runtime code should consume capability profiles from M04 rather than hard-coding provider eligibility here.
