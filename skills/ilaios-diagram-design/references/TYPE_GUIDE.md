# Diagram Type Guide

Select one dominant visual grammar.

## `architecture`

Use when the question is "what components exist and how are they connected?"

Best for:
- platform topology;
- factory composition;
- Control Plane / worker / tool / provider relationships;
- service boundaries.

Avoid when the dominant meaning is chronological ordering.

## `flowchart`

Use when the question is "what decision happens next?"

Best for:
- admission;
- policy;
- approvals;
- bounded repair;
- pass/fail delivery gates.

Default direction is top-to-bottom when the request is decision-heavy.

## `sequence`

Use when ordered messages between actors are the meaning.

Best for:
- sign-in → prompt → plan → route → execute → verify;
- Control Plane to worker/provider exchanges;
- authorization and evidence write sequences.

Node count is actor count; edge order is message order.

## `state-machine`

Use when legal state transitions matter more than topology.

Best for:
- job lifecycle;
- approval states;
- maturity state;
- deploy/recovery states.

Cycles are expected; keep states concise.

## `data-flow`

Use when producers, stores, processors, and consumers matter.

Best for:
- evidence;
- authorized context;
- RAG;
- telemetry;
- artifact movement.

Use explicit store/process node kinds in labels or subtitles.

## `dependency`

Use for prerequisite order where A must exist before B.

Best for:
- implementation sequencing;
- capability dependencies;
- promotion prerequisites.

Do not confuse dependency with runtime message flow.

## `trust-boundary`

Use when zones and crossing rules matter.

Group nodes using the `group` field. Use `forbidden` edges only for explicitly prohibited paths; never infer denial merely from missing edges.

## `capability-map`

Use for stable ILAIOS capability ownership relationships.

This is not a maturity report. A capability map may show architectural ownership without claiming implementation or production status.

## Split rule

Split a diagram when:
- two different dominant grammars are required;
- the node/edge budget is exceeded;
- labels must be reduced below comfortable reading size;
- an overview and a detailed control path compete for attention.

Prefer one overview plus one detail over a single dense "everything diagram."
