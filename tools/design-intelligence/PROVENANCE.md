# ILAIOS Design Intelligence — Reference Provenance

Status: CONTROLLED RESEARCH RECORD
Research date: 2026-08-13; refreshed 2026-08-18

External references are non-authoritative research inputs. ILAIOS does not vendor, install, import, execute, or depend on them at runtime.

## Taste Skill
- Repository/URL: `Leonxlnx/taste-skill`, https://github.com/Leonxlnx/taste-skill
- Revision: `e988add20dab0fa97d7a76781c48961c8184288e` (`main`).
- License: MIT; repository `LICENSE` inspected at the pinned revision.
- Paths inspected: README, LICENSE, skills and research directory inventory.
- Concepts learned: contextual anti-generic review, hierarchy, typography, spacing, density, motion restraint, responsive fallbacks.
- License-sensitive material: source, prompt expression, scripts, and assets. None copied.
- Decision: ideas only; copied code NO; runtime dependency NO; implementation attribution required NO because no protected implementation or substantial expression was copied.

## Emil Kowalski Skills for Design Engineers
- Repository/URL: `emilkowalski/skills`, https://github.com/emilkowalski/skills
- Revision inspected for this refresh: `e879241fab3cdb22e8d95587cdbf40b57a88d7da` (`main`).
- Prior recorded revision: `78761e1b57f97dce65b983d640c70a68f39e8163` (`main`).
- License: MIT; repository `LICENSE` inspected at the refreshed pinned revision.
- Paths inspected: README, LICENSE, skill directory inventory, and `skills/apple-design/SKILL.md`.
- Concepts learned: immediate and continuous interaction feedback, direct-manipulation continuity, interruptible user-driven motion, continuity between gesture release and settled motion, spatially consistent reversible transitions, reduced-motion/transparency/contrast fallbacks, and scale-aware typography.
- License-sensitive material: prompts, examples, prose, algorithms, source code, and implementation details. None copied.
- Decision: behavioral requirements only; independently worded ILAIOS rules and evaluator checks; copied code/text NO; runtime dependency NO; external runtime authority NO.

## Impeccable
- Repository/URL: `pbakaus/impeccable`, https://github.com/pbakaus/impeccable
- Revision: `bd2535974861db28a9f4a18ec78608488cd868dd` (`main`).
- License: Apache-2.0; repository `LICENSE` inspected at the pinned revision.
- Paths inspected: README, LICENSE, skill and detector directory inventory.
- Concepts learned: design vocabulary, contextual anti-pattern detection, typography/color/spatial/motion/interaction/responsive review, and brand-vs-product context.
- License-sensitive material: detector implementation, rules expression, CLI, extension, prompts, and documentation. None copied.
- Decision: ideas only; copied code NO; runtime dependency NO; implementation attribution required NO.

## Independent implementation evidence
- Neutral requirements: `rules.json` and `SKILL.md`.
- Original standard-library implementation: `services/design_quality.py`.
- Behavioral and contract tests: `tests/test_design_quality.py` and `tests/test_design_intelligence_extension.py`.
- Resulting skill ID: `design.final-polish`, composing native category findings.
- External runtime dependencies: 0. Copied third-party implementation files or fragments: 0.
- The 2026-08-18 refresh extends the existing ILAIOS-owned evaluator in place; it does not create an Apple-design runtime, second design authority, or parallel Web Factory gate.

Before any future reuse of external code or substantial expression, re-review the exact revision and license and preserve all obligations. External prompts, scripts, installers, tools, extensions, or agents must not receive ILAIOS credentials or production authority merely because they are design references.
