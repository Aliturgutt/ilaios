"""Deliberately fail one RAG.14 canary deployment and prove bounded rollback.

The probe runs only after the exact canary release has already passed its live
health/security checks. It registers a temporary task revision whose Knowledge
embedding mode is intentionally invalid, observes that revision fail closed,
and restores the previously verified exact canary task definition.
"""

from __future__ import annotations

import copy
import json
import os
import ssl
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, cast


class RollbackProbeError(RuntimeError):
    """The bounded bad-deployment/rollback exercise did not prove recovery."""


_REGION = "eu-central-1"
_CLUSTER = "ilaios-r01-canary"
_SERVICE = "ilaios-r01-canary"
_LOG_GROUP = "/ilaios/r01/canary/runtime"
_BAD_MODE = "rag14_invalid_embedding_probe"


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RollbackProbeError(f"required environment variable is missing: {name}")
    return value


def _run(*args: str, check: bool = True) -> str:
    result = subprocess.run(
        args,
        check=check,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def _aws_json(*args: str) -> Any:
    raw = _run("aws", *args, "--region", _REGION, "--output", "json")
    return json.loads(raw)


def _service() -> dict[str, Any]:
    payload = _aws_json(
        "ecs",
        "describe-services",
        "--cluster",
        _CLUSTER,
        "--services",
        _SERVICE,
    )
    services = payload.get("services", [])
    if not isinstance(services, list) or not services or not isinstance(services[0], dict):
        raise RollbackProbeError("RAG.14 canary service is unavailable")
    return cast(dict[str, Any], services[0])


def _expected_current_image() -> str:
    digest = _required_env("RAG14_IMAGE_DIGEST")
    return (
        "101180464425.dkr.ecr.eu-central-1.amazonaws.com/"
        f"ilaios-r01-canary@{digest}"
    )


def _verified_current_task() -> tuple[str, dict[str, Any]]:
    service = _service()
    if service.get("status") != "ACTIVE":
        raise RollbackProbeError("current canary service is not ACTIVE")
    desired = int(service.get("desiredCount", 0))
    running = int(service.get("runningCount", 0))
    if desired < 1 or running < desired:
        raise RollbackProbeError("current canary is not fully running before rollback drill")
    arn = str(service.get("taskDefinition", ""))
    if not arn:
        raise RollbackProbeError("current verified task definition is missing")
    payload = _aws_json("ecs", "describe-task-definition", "--task-definition", arn)
    task = payload.get("taskDefinition")
    if not isinstance(task, dict):
        raise RollbackProbeError("current task definition payload is malformed")
    containers = task.get("containerDefinitions")
    if not isinstance(containers, list) or len(containers) != 1 or not isinstance(containers[0], dict):
        raise RollbackProbeError("current RAG.14 task must contain exactly one runtime container")
    if containers[0].get("image") != _expected_current_image():
        raise RollbackProbeError("rollback target is not the exact verified release image")
    health = Path(_required_env("RAG14_EVIDENCE_ROOT")) / "deployment-health-window.json"
    if not health.is_file():
        raise RollbackProbeError("sustained health evidence is missing before rollback drill")
    health_payload: object = json.loads(health.read_text(encoding="utf-8"))
    if not isinstance(health_payload, dict) or health_payload.get("status") != "PASS":
        raise RollbackProbeError("rollback target has not passed the sustained health window")
    return arn, cast(dict[str, Any], task)


def _bad_registration(current: dict[str, Any]) -> dict[str, object]:
    allowed = (
        "family",
        "taskRoleArn",
        "executionRoleArn",
        "networkMode",
        "volumes",
        "placementConstraints",
        "requiresCompatibilities",
        "cpu",
        "memory",
        "runtimePlatform",
        "ipcMode",
        "pidMode",
        "proxyConfiguration",
        "ephemeralStorage",
    )
    registration: dict[str, object] = {
        key: copy.deepcopy(current[key]) for key in allowed if key in current
    }
    containers = copy.deepcopy(current["containerDefinitions"])
    container = cast(dict[str, Any], containers[0])
    environment = container.get("environment")
    if not isinstance(environment, list):
        environment = []
        container["environment"] = environment
    replaced = False
    for item in environment:
        if isinstance(item, dict) and item.get("name") == "ILAIOS_KNOWLEDGE_EMBEDDING_MODE":
            item["value"] = _BAD_MODE
            replaced = True
    if not replaced:
        environment.append(
            {"name": "ILAIOS_KNOWLEDGE_EMBEDDING_MODE", "value": _BAD_MODE}
        )
    registration["containerDefinitions"] = containers
    return registration


def _register_bad_revision(current: dict[str, Any]) -> str:
    registration = _bad_registration(current)
    with tempfile.TemporaryDirectory(prefix="ilaios-rag14-bad-deployment-") as temporary:
        path = Path(temporary) / "task.json"
        path.write_text(json.dumps(registration), encoding="utf-8")
        result = _aws_json(
            "ecs",
            "register-task-definition",
            "--cli-input-json",
            f"file://{path}",
        )
    task = result.get("taskDefinition")
    if not isinstance(task, dict):
        raise RollbackProbeError("temporary bad task definition registration failed")
    arn = str(task.get("taskDefinitionArn", ""))
    if not arn:
        raise RollbackProbeError("temporary bad task definition ARN is missing")
    containers = task.get("containerDefinitions")
    if not isinstance(containers, list) or not containers or not isinstance(containers[0], dict):
        raise RollbackProbeError("temporary bad task definition is malformed")
    env = {
        str(item.get("name")): str(item.get("value"))
        for item in containers[0].get("environment", [])
        if isinstance(item, dict)
    }
    if env.get("ILAIOS_KNOWLEDGE_EMBEDDING_MODE") != _BAD_MODE:
        raise RollbackProbeError("bad task definition did not bind the intended invalid mode")
    return arn


def _update_service(task_definition: str) -> None:
    _run(
        "aws",
        "ecs",
        "update-service",
        "--cluster",
        _CLUSTER,
        "--service",
        _SERVICE,
        "--task-definition",
        task_definition,
        "--force-new-deployment",
        "--region",
        _REGION,
    )


def _observe_bad_task(bad_arn: str, started_at: float) -> dict[str, object]:
    deadline = time.monotonic() + 180.0
    while time.monotonic() < deadline:
        arns_raw = _run(
            "aws",
            "ecs",
            "list-tasks",
            "--cluster",
            _CLUSTER,
            "--service-name",
            _SERVICE,
            "--desired-status",
            "STOPPED",
            "--region",
            _REGION,
            "--query",
            "taskArns",
            "--output",
            "text",
            check=False,
        )
        arns = [item for item in arns_raw.split() if item]
        if arns:
            described = _aws_json(
                "ecs",
                "describe-tasks",
                "--cluster",
                _CLUSTER,
                "--tasks",
                *arns[:100],
            )
            tasks = described.get("tasks", [])
            if isinstance(tasks, list):
                for raw in tasks:
                    if not isinstance(raw, dict):
                        continue
                    if str(raw.get("taskDefinitionArn")) != bad_arn:
                        continue
                    stopped_at = raw.get("stoppedAt")
                    if isinstance(stopped_at, str):
                        pass
                    containers = raw.get("containers")
                    if not isinstance(containers, list) or not containers or not isinstance(containers[0], dict):
                        continue
                    container = cast(dict[str, object], containers[0])
                    exit_code = container.get("exitCode")
                    if not isinstance(exit_code, int) or exit_code == 0:
                        continue
                    task_arn = str(raw.get("taskArn", ""))
                    if not task_arn:
                        continue
                    return {
                        "task_arn": task_arn,
                        "exit_code": exit_code,
                        "stopped_reason": str(raw.get("stoppedReason", "")),
                        "container_reason": str(container.get("reason", "")),
                        "observed_after_epoch_seconds": max(0.0, time.time() - started_at),
                    }
        time.sleep(5)
    raise RollbackProbeError("intentionally bad task was not observed failing closed")


def _bad_log_proof(task_arn: str) -> str:
    task_id = task_arn.rsplit("/", 1)[-1]
    stream = f"runtime/runtime/{task_id}"
    deadline = time.monotonic() + 90.0
    latest = ""
    while time.monotonic() < deadline:
        latest = _run(
            "aws",
            "logs",
            "get-log-events",
            "--log-group-name",
            _LOG_GROUP,
            "--log-stream-name",
            stream,
            "--start-from-head",
            "--region",
            _REGION,
            "--query",
            "events[].message",
            "--output",
            "text",
            check=False,
        )
        if "configured Knowledge embedding mode is unknown" in latest:
            return latest
        time.sleep(3)
    raise RollbackProbeError(
        "bad task failed, but the expected fail-closed embedding-mode reason was not proven"
    )


def _http_json(path: str) -> tuple[int, dict[str, object]]:
    dns = _required_env("RAG14_CANARY_DNS")
    token = _run(
        "aws",
        "secretsmanager",
        "get-secret-value",
        "--secret-id",
        _required_env("TF_VAR_control_plane_secret_arn"),
        "--region",
        _REGION,
        "--query",
        "SecretString",
        "--output",
        "text",
    )
    request = urllib.request.Request(
        f"https://{dns}{path}",
        headers={"Authorization": f"Bearer {token}"},
        method="GET",
    )
    context = ssl._create_unverified_context()
    try:
        with urllib.request.urlopen(request, timeout=30, context=context) as response:
            status = response.status
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        status = error.code
        raw = error.read().decode("utf-8")
    payload: object = json.loads(raw) if raw else {}
    if not isinstance(payload, dict):
        raise RollbackProbeError("post-rollback runtime returned a non-object payload")
    return status, cast(dict[str, object], payload)


def _verify_recovery(expected_task: str) -> dict[str, object]:
    _run(
        "aws",
        "ecs",
        "wait",
        "services-stable",
        "--cluster",
        _CLUSTER,
        "--services",
        _SERVICE,
        "--region",
        _REGION,
    )
    service = _service()
    if str(service.get("taskDefinition")) != expected_task:
        raise RollbackProbeError("service did not restore the verified task definition")
    if int(service.get("runningCount", 0)) < int(service.get("desiredCount", 1)):
        raise RollbackProbeError("service did not recover its desired running count")
    status, readiness = _http_json("/health/ready")
    if status != 200 or readiness.get("status") != "ready":
        raise RollbackProbeError("service readiness failed after explicit rollback")
    status, verification = _http_json("/v1/knowledge/verify")
    if status != 200:
        raise RollbackProbeError("Knowledge verification endpoint failed after rollback")
    if (
        verification.get("event_chain") != "verified"
        or verification.get("vector_index_integrity") is not True
    ):
        raise RollbackProbeError("Knowledge integrity failed after rollback")
    return {
        "service_task_definition": expected_task,
        "readiness": readiness,
        "knowledge_verification": verification,
    }


def run(root: Path) -> dict[str, object]:
    if os.environ.get("ILAIOS_RELEASE_STATE", "CANARY") not in {"", "CANARY"}:
        raise RollbackProbeError("rollback probe is canary-only")
    root.mkdir(parents=True, exist_ok=True)
    current_arn, current_task = _verified_current_task()
    bad_arn = _register_bad_revision(current_task)
    bad_observation: dict[str, object] | None = None
    failure_log_sha256 = ""
    started_at = time.time()
    try:
        _update_service(bad_arn)
        bad_observation = _observe_bad_task(bad_arn, started_at)
        log_text = _bad_log_proof(str(bad_observation["task_arn"]))
        failure_log_sha256 = __import__("hashlib").sha256(log_text.encode("utf-8")).hexdigest()
    finally:
        _update_service(current_arn)
    recovery = _verify_recovery(current_arn)
    _run(
        "aws",
        "ecs",
        "deregister-task-definition",
        "--task-definition",
        bad_arn,
        "--region",
        _REGION,
        check=False,
    )
    if bad_observation is None:
        raise RollbackProbeError("bad deployment observation was not recorded")
    report: dict[str, object] = {
        "status": "PASS",
        "runtime_source_sha": _required_env("RAG14_SOURCE_SHA"),
        "image_digest": _required_env("RAG14_IMAGE_DIGEST"),
        "verified_task_definition_before_bad_deployment": current_arn,
        "bad_task_definition": bad_arn,
        "bad_embedding_mode": _BAD_MODE,
        "bad_task_observation": bad_observation,
        "bad_failure_log_sha256": failure_log_sha256,
        "bad_deployment_simulated": True,
        "rollback_to_verified_artifact": True,
        "post_rollback": recovery,
        "production_authority": False,
    }
    (root / "rollback-recovery.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"event": "rag14_bad_deployment_rollback", **report}, sort_keys=True))
    return report


def main() -> int:
    root = Path(os.environ.get("RAG14_EVIDENCE_ROOT", "rag14-evidence"))
    run(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
