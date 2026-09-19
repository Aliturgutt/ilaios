---
name: ilaios-video-stock-search
description: Specify governed stock-media discovery requirements without granting network access or pretending that unimplemented source adapters are active.
---

# ILAIOS Video Stock Search

Use this skill to define search intent, licensing/provenance requirements, aspect ratio, duration, semantic relevance, and fallback order for stock media.

## Target adapter set

Candidate external adapters include Pexels, Pixabay, Unsplash, Wikimedia Commons, NASA, and Internet Archive. Their presence in this specification does not mean an adapter, credential, quota, license check, or E2E path is active.

## Required admission

Any future source adapter must execute through normal ILAIOS routing, Tool Gateway, tenant/security controls, provenance capture, license metadata capture, validation, audit, and evidence.

## Boundaries

Fail closed when source provenance, license/usage metadata, asset identity, or required authorization cannot be established.
