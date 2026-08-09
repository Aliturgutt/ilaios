# Hermes Video Automation --- Canonical Module Architecture & Dependency Order

> Historical provenance authority. The active product is ILAIOS and the active capability is ILAIOS Video Automation / Video Factory. Historical Hermes naming below is retained for traceability only.

**Status:** Canonical\
**Scope:** Hermes Video Automation only\
**Parent document:**
`docs/video_automation/ARCHITECTURE_AND_WORKFLOW.md`

## 2.1 Purpose

This document defines the canonical module boundaries and implementation
dependency order for Hermes Video Automation.

The implementation must follow this order unless a later canonical
architecture revision explicitly changes it. Provider-specific
integrations must not dictate the architecture.

## 2.2 Architectural Boundaries

Hermes Video Automation is an independent Hermes domain. It may consume
shared Hermes Core capabilities such as Audit Engine, Evidence Chain,
Validation Pipeline, Tool Gateway, Immutable Context, and Confidence
Scoring, but it must not mix its domain state, providers, credentials,
templates, jobs, or outputs with other Hermes production systems.

The permanent architecture consists of orchestration, domain models,
policy, validation, audit, evidence, job execution, and provider
abstractions. Seedance, Veo, Runway, Kling, FFmpeg, Remotion, TTS
services, transcription services, YouTube, TikTok, Instagram, and
Facebook are replaceable integrations.

## 2.3 Canonical Module Map

### M01 --- Video Domain Models

Defines the stable data contracts used by every later module.

Required models include:

-   `VideoJob`
-   `ResearchPacket`
-   `VideoScript`
-   `ScriptSection`
-   `Scene`
-   `Shot`
-   `AssetRequest`
-   `MediaAsset`
-   `Timeline`
-   `RenderArtifact`
-   `PublishJob`
-   provider request/result contracts
-   validation result contracts
-   cost records
-   job-state records

No provider API logic belongs in this module.

### M02 --- Video Configuration & Policy

Defines deterministic configuration and policy objects for:

-   TEST / PRODUCTION mode
-   provider policy
-   budget policy
-   approval policy
-   retry policy
-   platform targets
-   quality requirements
-   duration and format constraints
-   paid-provider enable/disable rules

TEST MODE must default to paid provider calls disabled.

### M03 --- Provider Interfaces

Defines provider-independent contracts.

Canonical interfaces:

-   `VideoGenerationProvider`
-   `ImageGenerationProvider`
-   `StockMediaProvider`
-   `VoiceProvider`
-   `MusicProvider`
-   `SoundEffectProvider`
-   `TranscriptionProvider`
-   `PublishingProvider`

Provider implementations depend on these interfaces; orchestration must
not depend directly on provider-specific SDKs.

### M04 --- Provider Registry & Capability Model

Registers available providers and describes capabilities such as:

-   supported media type
-   aspect ratios
-   duration limits
-   resolution
-   availability
-   cost characteristics
-   TEST / PRODUCTION eligibility

This module does not choose providers by itself.

### M05 --- Provider Selection Engine

Selects providers deterministically from configuration, policy,
requested capabilities, availability, cost limits, retry state, and
production mode.

Random provider selection is prohibited.

### M06 --- Research Pipeline

Produces a structured `ResearchPacket` containing:

-   topic summary
-   verified facts
-   source references
-   key claims
-   statistics
-   dates
-   entities
-   risks
-   uncertain/prohibited claims

Insufficient research confidence must prevent automatic progression
where policy requires it.

### M07 --- Script Generation

Transforms `VideoJob + ResearchPacket` into a structured `VideoScript`.

Script sections must have stable identifiers so downstream scene
planning can reference them.

### M08 --- Scene Planner

Transforms the structured script into logical scenes.

Each scene must carry its identity, script reference, purpose, duration,
visual intent, narration reference, transition intent, and required
assets.

### M09 --- Shot Planner

Transforms scenes into executable visual units.

Each shot must define its scene reference, shot type, subject, action,
environment, framing, movement, estimated duration, generation prompt,
and required provider capability.

### M10 --- Asset Planner

Determines the assets required by each shot and emits `AssetRequest`
objects.

It plans requirements but does not generate or download media.

### M11 --- Local Test Media Provider

Provides deterministic/local placeholder assets for TEST MODE.

Its purpose is to allow the complete pipeline to be developed and
validated without paid generative-video calls.

### M12 --- Media Acquisition & Generation Orchestrator

Resolves `AssetRequest` objects through registered providers.

Responsibilities include:

-   provider invocation
-   request tracking
-   polling
-   timeout handling
-   bounded retry coordination
-   result normalization
-   asset download/registration
-   provenance recording

Provider-specific API details remain inside provider implementations.

### M13 --- Asset Store & Provenance

Maintains normalized media asset metadata, paths, checksums,
source/provider provenance, job linkage, and validation state.

Every downstream editing/render operation must consume registered assets
rather than uncontrolled paths.

### M14 --- Voice Generation

Produces voice tracks through `VoiceProvider`.

Development may use local/free implementations. Production providers
remain replaceable.

### M15 --- Audio Processing

Handles:

-   audio validation
-   silence/noise processing
-   normalization
-   timeline alignment
-   music/SFX preparation
-   final mix preparation

### M16 --- Caption & Subtitle Engine

Produces structured captions and export formats such as:

-   structured caption JSON
-   SRT
-   VTT
-   burned-in caption instructions

Timing may originate from script timing, voice alignment, or
transcription providers.

### M17 --- Timeline Engine

Builds the canonical timeline from:

-   clips
-   images
-   narration
-   music
-   SFX
-   captions
-   overlays
-   transitions

It produces composition instructions, not the final media file.

### M18 --- FFmpeg Media Engine

Provides deterministic low-level media operations:

-   probe
-   trim
-   concatenate
-   transcode
-   scale/crop
-   frame-rate normalization
-   codec conversion
-   audio normalization/mixing
-   muxing
-   technical inspection

FFmpeg is an integration beneath Hermes orchestration, not the
architecture itself.

### M19 --- Remotion Composition Adapter

Provides programmatic composition for:

-   titles
-   animated text
-   lower thirds
-   overlays
-   branded layouts
-   transitions
-   charts
-   progress indicators
-   reusable visual templates
-   dynamic captions

Remotion complements FFmpeg; it does not replace the media engine.

### M20 --- Render Engine

Consumes validated assets and timeline instructions and creates
`RenderArtifact`.

The artifact must include at least:

-   file path
-   checksum
-   codec
-   resolution
-   duration
-   FPS
-   audio codec
-   aspect ratio
-   file size

### M21 --- Technical Validation

Validates the rendered artifact using deterministic checks including:

-   existence/readability
-   valid container
-   supported codec
-   expected resolution
-   expected duration
-   expected FPS
-   audio presence
-   stream integrity
-   aspect ratio
-   file-size boundaries

FFprobe is a primary inspection mechanism.

### M22 --- Content Validation

Validates semantic/composition requirements including:

-   expected scenes
-   narration consistency
-   captions
-   missing assets
-   intended duration
-   platform requirements
-   CTA requirements
-   branding rules

Publishing must not begin before required validation passes.

### M23 --- Platform Profiles & Adaptation

Defines platform-specific output requirements independently of
publishers.

Initial profile families:

-   YouTube long-form
-   YouTube Shorts
-   TikTok
-   Instagram Reels
-   Facebook Reels

Profiles define format, resolution, duration, metadata, caption,
thumbnail, and publishing requirements.

### M24 --- Publishing Provider Interfaces & Adapters

Implements the `PublishingProvider` abstraction.

Platform adapters may include:

-   YouTube
-   TikTok
-   Instagram
-   Facebook

Credentials must remain isolated by platform/account.

### M25 --- Scheduler & Publishing Queue

Accepts only validated publish jobs and dispatches jobs when their
scheduling conditions are satisfied.

Publishing/upload operations must be job-based rather than long
synchronous requests.

### M26 --- Job State Machine & Execution Control

Canonical states include:

-   `PENDING`
-   `RUNNING`
-   `WAITING_PROVIDER`
-   `VALIDATING`
-   `COMPLETED`
-   `FAILED`
-   `RETRY_PENDING`
-   `CANCELLED`

State transitions must be deterministic and auditable.

### M27 --- Retry & Failure Recovery

Classifies retryable and non-retryable failures and enforces bounded
deterministic retries.

Infinite retry is prohibited.

Retry behavior must respect provider policy, budget policy, and audit
requirements.

### M28 --- Cost Control

Tracks paid operations using:

-   provider
-   operation
-   estimated cost
-   actual cost when available
-   `job_id`
-   timestamp

Policies may enforce maximum cost per video, daily generation cost,
retry cost, and provider-specific limits.

### M29 --- Audit & Evidence Integration

Integrates the video domain with existing Hermes Core Audit Engine and
Evidence Chain.

Important events include job creation, research completion, script
generation, planning, provider selection, generation requests, asset
acquisition, voice generation, render lifecycle, validation, publishing,
upload completion/failure, and retry scheduling.

### M30 --- End-to-End Video Workflow Orchestrator

Coordinates the complete canonical workflow without containing
provider-specific implementation logic.

The orchestrator may only advance when dependencies, policy, validation,
and job-state requirements are satisfied.

## 2.4 Canonical Dependency Order

Implementation order is:

1.  M01 Video Domain Models
2.  M02 Video Configuration & Policy
3.  M03 Provider Interfaces
4.  M04 Provider Registry & Capability Model
5.  M05 Provider Selection Engine
6.  M06 Research Pipeline
7.  M07 Script Generation
8.  M08 Scene Planner
9.  M09 Shot Planner
10. M10 Asset Planner
11. M11 Local Test Media Provider
12. M12 Media Acquisition & Generation Orchestrator
13. M13 Asset Store & Provenance
14. M14 Voice Generation
15. M15 Audio Processing
16. M16 Caption & Subtitle Engine
17. M17 Timeline Engine
18. M18 FFmpeg Media Engine
19. M19 Remotion Composition Adapter
20. M20 Render Engine
21. M21 Technical Validation
22. M22 Content Validation
23. M23 Platform Profiles & Adaptation
24. M24 Publishing Provider Interfaces & Adapters
25. M25 Scheduler & Publishing Queue
26. M26 Job State Machine & Execution Control
27. M27 Retry & Failure Recovery
28. M28 Cost Control
29. M29 Audit & Evidence Integration
30. M30 End-to-End Video Workflow Orchestrator

## 2.5 Dependency Rules

The following rules are binding:

-   No module may depend on a later module merely to simplify
    implementation.
-   Provider-specific SDKs must remain behind provider adapters.
-   Paid production providers are not required to validate the pipeline.
-   TEST MODE must be capable of exercising the pipeline with local/mock
    assets.
-   Rendering cannot begin until required assets and timeline inputs
    exist.
-   Publishing cannot begin until required validation succeeds.
-   Retry logic cannot bypass cost, policy, validation, or approval
    controls.
-   Platform adaptation must remain separate from platform upload logic.
-   Audit/evidence identifiers must preserve `job_id` traceability
    across the workflow.
-   Website/Web Studio modules must not be placed inside the Video
    Automation domain.
-   Other product architectures must not be introduced into this module
    tree.

## 2.6 Initial Implementation Boundary

The first implementation milestone is not "generate a production AI
video."

The first milestone is:

`VideoJob → structured planning → local test assets → timeline → FFmpeg/Remotion composition → render → validation`

with no paid video provider required.

After this deterministic local pipeline passes its quality gates,
production media providers and social publishers can be integrated
behind the already-defined interfaces.

## 2.7 Production Expansion Order

After the local end-to-end pipeline is accepted:

1.  Add the selected production video-generation provider.
2.  Add production voice provider(s) if required.
3.  Add transcription/caption provider(s) if required.
4.  Add YouTube publishing.
5.  Add TikTok publishing.
6.  Add Instagram publishing.
7.  Add Facebook publishing.
8.  Add additional providers only through existing abstractions.

Provider additions must not require redesigning the canonical workflow.

## 2.8 Acceptance Rule

A module is complete only when:

-   its production code exists,
-   its tests exist,
-   its declared dependencies are already accepted,
-   deterministic validation passes,
-   repository quality gates pass,
-   no unauthorized files are modified,
-   the atomic commit is pushed,
-   `HEAD == origin/master`,
-   the working tree is clean.

Only then may implementation advance to the next dependency-ordered
module.
