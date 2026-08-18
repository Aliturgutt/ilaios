# ilaios-skill-evaluate

Evaluate an ILAIOS-native candidate skill against explicit scenarios and a recorded baseline.

## Purpose

Measure whether a candidate improves task reliability without weakening governance, safety, or evidence requirements.

## Required inputs

- validated candidate package;
- candidate package digest;
- scenario suite;
- model/provider identity used for the run;
- baseline result for the same task class when comparison is required;
- evidence sink.

## Evaluation method

1. Verify candidate digest before execution.
2. Run only authorized scenarios through the governed runtime.
3. Record assertion-level pass/fail results.
4. Record model/provider identity and bounded usage metrics when available.
5. Calculate candidate pass rate and baseline delta.
6. Record evidence identifiers for every material result.
7. Do not promote the skill.

## Output

Produce an evaluation record containing candidate digest, model identity, scenario results, baseline pass rate, candidate pass rate, regression delta, and evidence identifiers.

## Safety rule

Evaluation cannot grant permissions, bypass policy, call tools directly, or self-certify promotion. Missing evidence or mismatched candidate identity is a hard failure.
