# ilaios-skill-evaluate

Identity: `ilaios.skill.engineering.evaluate.v1`, IMPLEMENTED.

Purpose: evaluate one immutable candidate against explicit scenarios and assertions, with evidence bound to the exact candidate digest and evaluator/model identity.

## Rules

- Compare the exact candidate content digest; stale evaluation is invalid.
- Record scenario-level assertion results and evidence IDs.
- Keep evaluator identity explicit.
- A test definition is not a passed test; missing execution evidence fails closed.
- Evaluation cannot promote or provision a skill by itself.
