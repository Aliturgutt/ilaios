# Hermes Enterprise OS - Post-Core Roadmap

## Purpose

Define the fixed implementation order after completion of the Core phase.

This roadmap does not introduce optional features, parallel workstreams, or
architecture changes. It establishes the dependency order for the next atomic
implementation units already represented in the repository structure.

## Fixed Post-Core Phase Order

1. Code Intelligence
2. Knowledge Graph
3. Project Manager
4. Core Integration

## Phase 1 - Code Intelligence

Objective:

Provide deterministic source-code analysis models and services that can inspect
repository structure without modifying files or executing code.

Atomic implementation order:

1. Code Entity Model
2. Source File Analyzer
3. Symbol Extraction
4. Dependency Extraction
5. Repository Code Index

Dependencies:

- Completed Hermes Core
- Existing `src/code_intelligence/models.py`

Out of scope:

- Automatic code modification
- Refactoring
- Pull request creation
- Live external API calls
- Language-server integration
- Semantic vector search

## Phase 2 - Knowledge Graph

Objective:

Represent validated project entities and relationships as a deterministic,
queryable graph.

Atomic implementation order:

1. Graph Entity Model
2. Graph Edge Model
3. In-Memory Graph Store
4. Graph Validation
5. Code Intelligence Graph Adapter

Dependencies:

- Completed Code Intelligence phase
- Existing `src/knowledge_graph/models.py`

Out of scope:

- External graph databases
- Embedding generation
- Autonomous inference
- Cross-project synchronization

## Phase 3 - Project Manager

Objective:

Represent project work, dependencies, and execution state through deterministic
project-management models and services.

Atomic implementation order:

1. Project Model
2. Work Item Model
3. Dependency Validation
4. Project State Store
5. Knowledge Graph Project Adapter

Dependencies:

- Completed Knowledge Graph phase
- Existing `src/project_manager/models.py`

Out of scope:

- Calendar integration
- Team collaboration
- Notifications
- Autonomous prioritization
- External project-management platforms

## Phase 4 - Core Integration

Objective:

Connect Code Intelligence, Knowledge Graph, and Project Manager to the completed
Core through explicit, validated adapters.

Atomic implementation order:

1. Code Intelligence Core Adapter
2. Knowledge Graph Core Adapter
3. Project Manager Core Adapter
4. Integrated Validation Flow
5. Integrated Audit and Evidence Flow

Dependencies:

- Completed Code Intelligence phase
- Completed Knowledge Graph phase
- Completed Project Manager phase
- Completed Hermes Core

Out of scope:

- Desktop Companion
- Mobile application
- Secure cloud API
- Plugin runtime
- Remote execution
- Approval user interface

## Next Atomic Unit

The next atomic implementation unit is:

`Code Intelligence - Code Entity Model`

This unit must:

- remain inside `src/code_intelligence`
- use deterministic typed Python models
- include complete unit tests
- make no external API calls
- make no filesystem modifications
- introduce no new framework
- preserve compatibility with strict mypy, ruff, pytest, and pre-commit

## Completion Rule

Each atomic unit is complete only when:

- production code is implemented
- unit tests are implemented
- `pre-commit run --all-files` passes
- `ruff check .` passes
- `mypy --strict .` passes
- `python -m pytest -q` passes
- changes are committed atomically
- changes are pushed only after all checks pass
- local `HEAD` matches `origin/master`
- the working tree is clean
