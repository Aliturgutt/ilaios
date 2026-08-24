#!/usr/bin/env python3
"""Validate the durable Fast-Closure V2 coordination state.

This validator is intentionally fail-closed. It validates coordination metadata only;
it does not grant merge authority or replace repository protection, CI, or governance.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, cast

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
    "PRE_MERGE_VALIDATION",
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

    token_raw = data.get("merge_token")
    require(isinstance(token_raw, dict), "merge_token must be an object")
    token = cast(dict[str, Any], token_raw)
    token_state = token.get("state")
    require(token_state in TOKEN_STATES, f"invalid merge token state: {token_state!r}")
    owner = token.get("owner")
    if token_state in {"AVAILABLE", "RELEASED"}:
        require(owner is None, f"{token_state} token must not retain an owner")
        require(token.get("freeze_active") is False, f"{token_state} token must not keep freeze_active")
    else:
        require(bool(isinstance(owner, str) and owner), f"{token_state} token requires an owner")
        require(token.get("freeze_active") is True, f"{token_state} token must keep freeze_active")

    workstreams_raw = data.get("workstreams")
    require(isinstance(workstreams_raw, dict), "workstreams must be an object")
    workstreams = cast(dict[str, Any], workstreams_raw)
    require(set(workstreams) == EXPECTED_WORKSTREAMS, "workstream set must contain exactly the nine canonical lanes")

    ranks: list[int] = []
    for name, state_raw in workstreams.items():
        require(isinstance(state_raw, dict), f"workstream {name} must be an object")
        state = cast(dict[str, Any], state_raw)
        lifecycle = state.get("lifecycle")
        require(lifecycle in LIFECYCLE_STATES, f"invalid lifecycle for {name}: {lifecycle!r}")
        scheduler = state.get("scheduler")
        require(scheduler in EXPECTED_SCHEDULERS, f"invalid scheduler for {name}: {scheduler!r}")
        rank = state.get("priority_rank")
        require(isinstance(rank, int) and 1 <= rank <= 9, f"invalid priority_rank for {name}")
        ranks.append(cast(int, rank))
        next_action = state.get("next_action")
        require(isinstance(next_action, str) and bool(next_action.strip()), f"{name} requires next_action")
        if lifecycle == "BLOCKED_EXTERNAL":
            require(bool(state.get("blocked_reason")), f"{name} BLOCKED_EXTERNAL requires blocked_reason")

    require(sorted(ranks) == list(range(1, 10)), "priority_rank values must be unique 1..9")

    if owner is not None:
        require(isinstance(owner, str) and owner in workstreams, "merge token owner must name a known workstream")
        owner_state = cast(dict[str, Any], workstreams[cast(str, owner)])
        require(
            owner_state["lifecycle"]
            in {"MERGE_READY", "TOKEN_WAIT", "PRE_MERGE_VALIDATION", "MERGING", "EXACT_MASTER_VERIFY"},
            "merge token owner lifecycle must be merge-related",
        )

    metrics_raw = data.get("metrics")
    require(isinstance(metrics_raw, dict), "metrics must be an object")
    metrics = cast(dict[str, Any], metrics_raw)
    for key, value in metrics.items():
        require(isinstance(value, int) and value >= 0, f"metric {key} must be a non-negative integer")


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".github/automation/fast-closure-v2-state.json")
    raw = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(raw, dict), "state root must be an object")
    validate(cast(dict[str, Any], raw))
    print(f"FAST_CLOSURE_V2_STATE_VALID: {path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"FAST_CLOSURE_V2_STATE_INVALID: {exc}", file=sys.stderr)
        raise SystemExit(1)
