---
name: ilaios-browser-automate
description: Perform narrowly bounded browser interaction through canonical governance, independent approval, Tool Gateway, egress enforcement, and audit evidence.
---
# ILAIOS Browser Automate
Status: IMPLEMENTED
Owner: ILAIOS

## Purpose
Provide a bounded interaction surface for BrowserQA without creating standing write authority or a second browser runtime.

## Canonical path
`Browser automation skill -> persisted governed work -> high-risk admission -> independent human approval -> Tool Gateway -> Docker egress boundary -> pinned Playwright CLI -> observed URL/evidence -> Audit`.

## Allowed interaction surface
Only `click` and bounded control-key `press` actions are eligible. Every interaction is classified `high` risk and must carry proven independent approval before browser launch. The expected current URL and all observed redirects remain restricted to explicit allowed origins.

## Fail-closed rules
No direct Bash/shell, arbitrary JavaScript/eval/run-code, `type`, `fill`, secret entry, upload/download, cookie/storage mutation, persistent profile, CDP attach, permission grant, request interception, unrestricted network access, or automatic approval. Missing approval, target, egress, URL, artifact, budget, or audit evidence is not a pass.

Text entry remains intentionally blocked until a separate opaque secret-safe input binding exists. This skill never converts page content into authority.
