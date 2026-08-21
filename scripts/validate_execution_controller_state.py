#!/usr/bin/env python3
"""Validate ILAIOS execution-controller state files using only stdlib."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ALLOWED_STATUS = {
    "NOT_STARTED",
    "IN_PROGRESS",
    "BLOCKED",
    "TESTED",
    "VERIFIED",
    "DEPLOYED",
    "PRODUCTION",
}
ALLOWED_BLOCKERS = {None, "REPOSITORY", "CI", "PROVIDER", "EXTERNAL", "HUMAN"}
REQUIRED_TOP_LEVEL = {
    "schema_version",
    "task_id",
    "task_source",
    "status",
    "current_phase",
    "master_sha",
    "base_sha",
    "head_sha",
    "branch",
    "pr",
    "ci",
    "next_action",
    "blocker",
    "repair",
    "lock",
    "evidence",
    "updated_at",
}


def fail(path: Path, message: str) -> None:
    raise ValueError(f"{path}: {message}")


def validate(path: Path) -> None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(path, f"invalid JSON: {exc}")

    if not isinstance(data, dict):
        fail(path, "root must be an object")

    missing = sorted(REQUIRED_TOP_LEVEL - set(data))
    if missing:
        fail(path, f"missing required keys: {', '.join(missing)}")

    if data["schema_version"] != "ilaios.execution-controller.v1":
        fail(path, "unsupported schema_version")
    if not isinstance(data["task_id"], str) or not data["task_id"].strip():
        fail(path, "task_id must be a non-empty string")
    if data["status"] not in ALLOWED_STATUS:
        fail(path, f"invalid status: {data['status']!r}")
    if not isinstance(data["next_action"], str) or not data["next_action"].strip():
        fail(path, "next_action must be a non-empty string")

    source = data["task_source"]
    if not isinstance(source, dict) or not source.get("type") or not source.get("reference"):
        fail(path, "task_source requires non-empty type and reference")

    ci = data["ci"]
    if not isinstance(ci, dict) or set(ci) != {"run_id", "conclusion", "exact_sha"}:
        fail(path, "ci must contain exactly run_id, conclusion, exact_sha")
    if ci["conclusion"] == "success" and not ci["exact_sha"]:
        fail(path, "successful CI requires exact_sha evidence")

    blocker = data["blocker"]
    if not isinstance(blocker, dict) or set(blocker) != {"type", "detail", "human_action"}:
        fail(path, "blocker must contain exactly type, detail, human_action")
    if blocker["type"] not in ALLOWED_BLOCKERS:
        fail(path, f"invalid blocker type: {blocker['type']!r}")
    if data["status"] == "BLOCKED" and blocker["type"] is None:
        fail(path, "BLOCKED status requires blocker.type")
    if blocker["type"] == "HUMAN" and not blocker["human_action"]:
        fail(path, "HUMAN blocker requires human_action")

    repair = data["repair"]
    if not isinstance(repair, dict) or set(repair) != {
        "retry_count",
        "last_failure_fingerprint",
        "last_root_cause",
    }:
        fail(path, "repair object shape is invalid")
    if not isinstance(repair["retry_count"], int) or repair["retry_count"] < 0:
        fail(path, "repair.retry_count must be a non-negative integer")

    lock = data["lock"]
    if not isinstance(lock, dict) or set(lock) != {
        "owner",
        "scope",
        "acquired_at",
        "expires_at",
    }:
        fail(path, "lock object shape is invalid")
    if not isinstance(lock["scope"], list) or not all(isinstance(x, str) for x in lock["scope"]):
        fail(path, "lock.scope must be a list of strings")
    if lock["owner"] and not lock["scope"]:
        fail(path, "active lock owner requires non-empty scope")

    if not isinstance(data["evidence"], list):
        fail(path, "evidence must be a list")

    if data["status"] in {"VERIFIED", "DEPLOYED", "PRODUCTION"} and not data["evidence"]:
        fail(path, f"{data['status']} requires evidence")


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: validate_execution_controller_state.py <state.json> [...]", file=sys.stderr)
        return 2

    failed = False
    for raw in argv[1:]:
        path = Path(raw)
        try:
            validate(path)
            print(f"PASS {path}")
        except ValueError as exc:
            failed = True
            print(f"FAIL {exc}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
