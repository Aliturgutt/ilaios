# ILAIOS Browser Skills — Provenance

FIRST-PARTY ILAIOS IMPLEMENTATION

INDEPENDENTLY AUTHORED from ILAIOS governance, BrowserQA, Web Factory, Tool Gateway, validation and evidence contracts.

Methodology reference reviewed: Microsoft `microsoft/playwright-cli` / `@playwright/cli` (Apache-2.0). The review informed command-oriented browser automation, snapshot-based evidence and CLI/skill separation. No upstream implementation code, skill text, prompt text, assets or scripts are copied into these ILAIOS packages.

CODE/TEXT IMPORTED = NONE

PROMPT/SKILL TEXT IMPORTED = NONE

REFERENCE IMPLEMENTATION IMPORTED = NONE

RUNTIME DEPENDENCY ON THIRD-PARTY SKILL REPOSITORIES = NONE

OPTIONAL BROWSER ADAPTER = replaceable Playwright CLI command adapter behind ILAIOS Tool Gateway and an external egress-enforcement boundary.

The Playwright CLI network allowlist is treated only as a guardrail, not as the ILAIOS security boundary. Live execution must fail closed unless the process is run by an ILAIOS-approved network-egress boundary.
