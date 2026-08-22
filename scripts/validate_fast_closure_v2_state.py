#!/usr/bin/env python3
"""Validate the durable Fast-Closure V2 coordination state.

This validator is intentionally fail-closed. It validates coordination metadata only;
it does not grant merge authority or replace repository protection, CI, or governance.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

TOKEN_STATES = {
    "AVAILABLE",
    "RESERVED",
    "PRE_MERGE_VALIDATION",
    "MERGED",
    "EXACT_MASTER_VALIDATION",
    "RELEASED",
}

LIFECYCLE_STATES = {
    "DEVELOPING",
    "CI_RUNNING",
    "MERGE_READY",
    "TOKEN_WAIT",
    "MERGING",
    "EXACT_MASTER_VERIFY",
    "BLOCKED_EXTERNAL",
    "BLOCKED_INTERNAL",
    "CLOSED",
}

EXPECTED_SCHEDULERS = {
    "desktop": 0,
    "unified": 12,
    "identity": 24,
    "web_app": 36,
    "agents": 48,
}

EXPECTED_WORKSTREAMS = {
    "desktop",
    "video_native_reference",
    "website_v2",
    "identity",
    "web_app",
    "agents",
    "app_factory",
    "mobile_store",
    "microsoft_store",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate(data: dict[str, Any]) -> None:
    require(data.get("schema_version") == 1, "schema_version must be 1")
    require(data.get("mode") == "FAST_CLOSURE_V2", "mode must be FAST_CLOSURE_V2")

    stagger = data.get("scheduler_stagger")
    require(stagger == EXPECTED_SCHEDULERS, "scheduler_stagger must match the canonical 00/12/24/36/48 plan")

    token = data.get("merge_token")
    require(isinstance(token, dict), "merge_token must be an object")
    token_state = token.get("state")
    require(token_state in TOKEN_STATES, f"invalid merge token state: {token_state!r}")
    owner = token.get("owner")
    if token_state in {"AVAILABLE", "RELEASED"}:
        require(owner is None, f"{token_state} token must not retain an owner")
        require(token.get("freeze_active") is False, f"{token_state} token must not keep freeze_active")
    else:
        require(isinstance(owner, str) and owner, f"{token_state} token requires an owner")

    workstreams = data.get("workstreams")
    require(isinstance(workstreams, dict), "workstreams must be an object")
    require(set(workstreams) == EXPECTED_WORKSTREAMS, "workstream set must contain exactly the nine canonical lanes")

    ranks: list[int] = []
    for name, state in workstreams.items():
        require(isinstance(state, dict), f"workstream {name} must be an object")
        lifecycle = state.get("lifecycle")
        require(lifecycle in LIFECYCLE_STATES, f"invalid lifecycle for {name}: {lifecycle!r}")
        scheduler = state.get("scheduler")
        require(scheduler in EXPECTED_SCHEDULERS, f"invalid scheduler for {name}: {scheduler!r}")
        rank = state.get("priority_rank")
        require(isinstance(rank, int) and 1 <= rank <= 9, f"invalid priority_rank for {name}")
        ranks.append(rank)
        require(isinstance(state.get("next_action"), str) and state["next_action"].strip(), f"{name} requires next_action")
        if lifecycle == "BLOCKED_EXTERNAL":
            require(bool(state.get("blocked_reason")), f"{name} BLOCKED_EXTERNAL requires blocked_reason")

    require(sorted(ranks) == list(range(1, 10)), "priority_rank values must be unique 1..9")

    if owner is not None:
        require(owner in workstreams, "merge token owner must name a known workstream")
        require(
            workstreams[owner]["lifecycle"] in {"MERGE_READY", "TOKEN_WAIT", "MERGING", "EXACT_MASTER_VERIFY"},
            "merge token owner lifecycle must be merge-related",
        )

    metrics = data.get("metrics")
    require(isinstance(metrics, dict), "metrics must be an object")
    for key, value in metrics.items():
        require(isinstance(value, int) and value >= 0, f"metric {key} must be a non-negative integer")


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".github/automation/fast-closure-v2-state.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    validate(data)
    print(f"FAST_CLOSURE_V2_STATE_VALID: {path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"FAST_CLOSURE_V2_STATE_INVALID: {exc}", file=sys.stderr)
        raise SystemExit(1)
