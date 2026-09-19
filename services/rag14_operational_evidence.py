"""Collect RAG.14 canary recovery, observability, FinOps and rollback evidence.

This module is intentionally canary-only. It can exercise AWS resources only
inside the manually dispatched, explicit-spend RAG.14 workflow and it never
promotes Knowledge/RAG to production.
"""

from __future__ import annotations

import hashlib
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


class OperationalEvidenceError(RuntimeError):
    """A required operational canary invariant was not demonstrated."""


_REGION = "eu-central-1"
_CLUSTER = "ilaios-r01-canary"
_SERVICE = "ilaios-r01-canary"
_LOG_GROUP = "/ilaios/r01/canary/runtime"
_NAMESPACE = "ILAIOS/RAG14"


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise OperationalEvidenceError(f"required environment variable is missing: {name}")
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


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _http_json(path: str) -> tuple[int, dict[str, object]]:
    dns = _required_env("RAG14_CANARY_DNS")
    secret_arn = _required_env("TF_VAR_control_plane_secret_arn")
    token = _run(
        "aws",
        "secretsmanager",
        "get-secret-value",
        "--secret-id",
        secret_arn,
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
    context = ssl._create_unverified_context()  # canary ALB DNS != certificate name
    try:
        with urllib.request.urlopen(request, timeout=30, context=context) as response:
            status = response.status
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        status = error.code
        raw = error.read().decode("utf-8")
    payload: object = json.loads(raw) if raw else {}
    if not isinstance(payload, dict):
        raise OperationalEvidenceError("runtime returned a non-object response")
    return status, cast(dict[str, object], payload)


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
    if not services:
        raise OperationalEvidenceError("RAG.14 ECS service is unavailable")
    return cast(dict[str, Any], services[0])


def _backup_restore_drill(root: Path) -> dict[str, object]:
    service = _service()
    task_definition = str(service["taskDefinition"])
    network = cast(dict[str, Any], service.get("networkConfiguration", {})).get(
        "awsvpcConfiguration"
    )
    if not isinstance(network, dict):
        raise OperationalEvidenceError("service awsvpc configuration is missing")
    subnets = network.get("subnets")
    groups = network.get("securityGroups")
    if (
        not isinstance(subnets, list)
        or not subnets
        or not isinstance(groups, list)
        or not groups
    ):
        raise OperationalEvidenceError("service network scope is incomplete")
    assign_public_ip = str(network.get("assignPublicIp", "DISABLED"))

    request = {
        "cluster": _CLUSTER,
        "taskDefinition": task_definition,
        "launchType": "FARGATE",
        "count": 1,
        "startedBy": f"rag14-backup-{_required_env('RAG14_SOURCE_SHA')[:20]}",
        "networkConfiguration": {
            "awsvpcConfiguration": {
                "subnets": subnets,
                "securityGroups": groups,
                "assignPublicIp": assign_public_ip,
            }
        },
        "overrides": {
            "containerOverrides": [
                {
                    "name": "runtime",
                    "environment": [
                        {
                            "name": "ILAIOS_RAG14_MAINTENANCE_MODE",
                            "value": "backup_restore_test",
                        }
                    ],
                }
            ]
        },
    }
    with tempfile.TemporaryDirectory(prefix="ilaios-rag14-run-task-") as temporary:
        request_path = Path(temporary) / "run-task.json"
        request_path.write_text(json.dumps(request), encoding="utf-8")
        response: object = json.loads(
            _run(
                "aws",
                "ecs",
                "run-task",
                "--cli-input-json",
                f"file://{request_path}",
                "--region",
                _REGION,
                "--output",
                "json",
            )
        )
    if not isinstance(response, dict):
        raise OperationalEvidenceError("ECS maintenance task response is malformed")
    failures = response.get("failures")
    if isinstance(failures, list) and failures:
        raise OperationalEvidenceError(
            f"ECS maintenance task failed to start: {failures}"
        )
    tasks = response.get("tasks")
    if (
        not isinstance(tasks, list)
        or len(tasks) != 1
        or not isinstance(tasks[0], dict)
    ):
        raise OperationalEvidenceError(
            "ECS maintenance task was not created exactly once"
        )
    task_arn = str(cast(dict[str, object], tasks[0]).get("taskArn", ""))
    if not task_arn:
        raise OperationalEvidenceError("ECS maintenance task ARN is missing")

    _run(
        "aws",
        "ecs",
        "wait",
        "tasks-stopped",
        "--cluster",
        _CLUSTER,
        "--tasks",
        task_arn,
        "--region",
        _REGION,
    )
    described = _aws_json(
        "ecs",
        "describe-tasks",
        "--cluster",
        _CLUSTER,
        "--tasks",
        task_arn,
    )
    task = cast(dict[str, Any], described["tasks"][0])
    containers = task.get("containers")
    if (
        not isinstance(containers, list)
        or not containers
        or not isinstance(containers[0], dict)
    ):
        raise OperationalEvidenceError("maintenance task container result is missing")
    exit_code = cast(dict[str, object], containers[0]).get("exitCode")
    if exit_code != 0:
        raise OperationalEvidenceError(
            f"backup/restore maintenance task exited with code {exit_code}: "
            f"{task.get('stoppedReason')}"
        )

    task_id = task_arn.rsplit("/", 1)[-1]
    log_stream = f"runtime/runtime/{task_id}"
    deadline = time.monotonic() + 90.0
    report: dict[str, object] | None = None
    while time.monotonic() < deadline:
        result = _run(
            "aws",
            "logs",
            "get-log-events",
            "--log-group-name",
            _LOG_GROUP,
            "--log-stream-name",
            log_stream,
            "--start-from-head",
            "--region",
            _REGION,
            "--output",
            "json",
            check=False,
        )
        if result:
            try:
                logs: object = json.loads(result)
            except json.JSONDecodeError:
                logs = {}
            if isinstance(logs, dict):
                events = logs.get("events")
                if isinstance(events, list):
                    for event in events:
                        if not isinstance(event, dict):
                            continue
                        try:
                            payload: object = json.loads(
                                str(event.get("message", ""))
                            )
                        except json.JSONDecodeError:
                            continue
                        if (
                            isinstance(payload, dict)
                            and payload.get("event") == "rag14_backup_restore"
                        ):
                            report = cast(dict[str, object], payload)
        if report is not None:
            break
        time.sleep(3)
    if report is None:
        raise OperationalEvidenceError(
            "backup/restore report was not found in task logs"
        )
    if (
        report.get("status") != "PASS"
        or report.get("corrupt_restore_rejected") is not True
    ):
        raise OperationalEvidenceError(
            "backup/restore evidence did not PASS fail-closed checks"
        )
    if report.get("production_authority") is not False:
        raise OperationalEvidenceError(
            "backup drill attempted to claim production authority"
        )
    archive_sha = report.get("archive_sha256")
    if not isinstance(archive_sha, str) or len(archive_sha) != 64:
        raise OperationalEvidenceError("backup archive SHA-256 evidence is invalid")
    _write_json(root / "backup-restore.json", report)
    return report


def _health_window(root: Path) -> dict[str, object]:
    samples: list[dict[str, object]] = []
    started = time.monotonic()
    for index in range(12):
        status, payload = _http_json("/health/ready")
        samples.append({"sample": index + 1, "status": status, "payload": payload})
        if status != 200 or payload.get("status") != "ready":
            raise OperationalEvidenceError(
                "canary failed the sustained deployment health window"
            )
        if index != 11:
            time.sleep(10)
    report: dict[str, object] = {
        "status": "PASS",
        "sample_count": len(samples),
        "window_seconds": round(time.monotonic() - started, 3),
        "samples": samples,
        "production_authority": False,
    }
    _write_json(root / "deployment-health-window.json", report)
    return report


def _metric_payload(
    metric_name: str, value: float, source_sha: str
) -> dict[str, object]:
    return {
        "MetricName": metric_name,
        "Dimensions": [{"Name": "SourceSha", "Value": source_sha}],
        "Value": value,
        "Unit": "Count",
        "StorageResolution": 1,
    }


def _put_metrics(metrics: list[dict[str, object]]) -> None:
    _run(
        "aws",
        "cloudwatch",
        "put-metric-data",
        "--namespace",
        _NAMESPACE,
        "--metric-data",
        json.dumps(metrics, separators=(",", ":")),
        "--region",
        _REGION,
    )


def _alarm_states(names: list[str]) -> dict[str, str]:
    payload = _aws_json("cloudwatch", "describe-alarms", "--alarm-names", *names)
    alarms = payload.get("MetricAlarms", [])
    return {
        str(item.get("AlarmName")): str(item.get("StateValue"))
        for item in alarms
        if isinstance(item, dict)
    }


def _wait_alarm_state(
    names: list[str], expected: str, timeout: float = 90.0
) -> dict[str, str]:
    deadline = time.monotonic() + timeout
    latest: dict[str, str] = {}
    while time.monotonic() < deadline:
        latest = _alarm_states(names)
        if len(latest) == len(names) and all(
            latest.get(name) == expected for name in names
        ):
            return latest
        time.sleep(5)
    raise OperationalEvidenceError(
        f"CloudWatch alarm transition to {expected} timed out: {latest}"
    )


def _observability_alarm_drill(root: Path) -> dict[str, object]:
    source_sha = _required_env("RAG14_SOURCE_SHA")
    rules = {
        "embedding-failure": "EmbeddingFailureProbe",
        "excessive-latency": "ExcessiveLatencyProbe",
        "memory-pressure": "MemoryPressureProbe",
        "retrieval-failure": "RetrievalFailureProbe",
        "index-corruption": "IndexCorruptionProbe",
        "backup-failure": "BackupFailureProbe",
        "authorization-anomaly": "AuthorizationAnomalyProbe",
        "leakage-security": "LeakageSecurityProbe",
    }
    alarm_names = [f"ilaios-rag14-{label}-{source_sha[:10]}" for label in rules]
    alarm_state: dict[str, str] = {}
    ok_state: dict[str, str] = {}
    try:
        for (label, metric_name), alarm_name in zip(
            rules.items(), alarm_names, strict=True
        ):
            _run(
                "aws",
                "cloudwatch",
                "put-metric-alarm",
                "--alarm-name",
                alarm_name,
                "--alarm-description",
                f"RAG.14 canary evidence rule: {label}",
                "--namespace",
                _NAMESPACE,
                "--metric-name",
                metric_name,
                "--dimensions",
                f"Name=SourceSha,Value={source_sha}",
                "--statistic",
                "Maximum",
                "--period",
                "10",
                "--evaluation-periods",
                "1",
                "--datapoints-to-alarm",
                "1",
                "--threshold",
                "0.5",
                "--comparison-operator",
                "GreaterThanThreshold",
                "--treat-missing-data",
                "notBreaching",
                "--region",
                _REGION,
            )
        _put_metrics(
            [
                _metric_payload(metric_name, 1.0, source_sha)
                for metric_name in rules.values()
            ]
        )
        alarm_state = _wait_alarm_state(alarm_names, "ALARM")
        _put_metrics(
            [
                _metric_payload(metric_name, 0.0, source_sha)
                for metric_name in rules.values()
            ]
        )
        ok_state = _wait_alarm_state(alarm_names, "OK")
    finally:
        if alarm_names:
            _run(
                "aws",
                "cloudwatch",
                "delete-alarms",
                "--alarm-names",
                *alarm_names,
                "--region",
                _REGION,
                check=False,
            )
    report: dict[str, object] = {
        "status": "PASS",
        "namespace": _NAMESPACE,
        "rules": rules,
        "alarm_state": alarm_state,
        "recovered_state": ok_state,
        "all_rules_fired": all(value == "ALARM" for value in alarm_state.values()),
        "all_rules_recovered": all(value == "OK" for value in ok_state.values()),
        "production_authority": False,
    }
    _write_json(root / "observability-alerts.json", report)
    return report


def _finops_meter(root: Path) -> dict[str, object]:
    if _required_env("RAG14_EXTERNAL_SPEND_APPROVED") != "true":
        raise OperationalEvidenceError("RAG.14 external spend approval is absent")
    started_ms = int(_required_env("RAG14_CANARY_STARTED_AT_MS"))
    duration_seconds = max(0.0, (time.time() * 1000.0 - started_ms) / 1000.0)
    service = _service()
    desired = int(service.get("desiredCount", 0))
    image_digest = _required_env("RAG14_IMAGE_DIGEST")
    image = _aws_json(
        "ecr",
        "describe-images",
        "--repository-name",
        "ilaios-r01-canary",
        "--image-ids",
        f"imageDigest={image_digest}",
    )
    details = image.get("imageDetails", [])
    image_size = int(details[0].get("imageSizeInBytes", 0)) if details else 0
    efs = _aws_json(
        "efs", "describe-file-systems", "--creation-token", "ilaios-r01-canary"
    )
    systems = efs.get("FileSystems", [])
    efs_bytes = (
        int(systems[0].get("SizeInBytes", {}).get("Value", 0)) if systems else 0
    )
    report: dict[str, object] = {
        "status": "PASS_RESOURCE_METERED",
        "external_spend_approved": True,
        "canary_elapsed_seconds": round(duration_seconds, 3),
        "desired_task_count": desired,
        "vcpu_seconds": round(duration_seconds * 0.25 * desired, 3),
        "memory_gib_seconds": round(duration_seconds * 1.0 * desired, 3),
        "ecr_image_size_bytes": image_size,
        "efs_state_size_bytes": efs_bytes,
        "embedding_api_fee_model": "SELF_HOSTED_NO_EXTERNAL_EMBEDDING_API_FEE",
        "currency_cost_claimed": False,
        "currency_cost_note": (
            "AWS billing currency cost is not claimed before provider billing "
            "evidence settles."
        ),
        "production_authority": False,
    }
    _write_json(root / "finops-resource-meter.json", report)
    return report


def _previous_release_is_verified(task_definition: str) -> dict[str, object]:
    task = _aws_json(
        "ecs",
        "describe-task-definition",
        "--task-definition",
        task_definition,
    )["taskDefinition"]
    image = str(task["containerDefinitions"][0]["image"])
    if "@sha256:" not in image:
        raise OperationalEvidenceError("previous task image is not digest-pinned")
    digest = image.rsplit("@", 1)[1]
    detail = _aws_json(
        "ecr",
        "describe-images",
        "--repository-name",
        "ilaios-r01-canary",
        "--image-ids",
        f"imageDigest={digest}",
    )
    tags = cast(list[str], detail["imageDetails"][0].get("imageTags", []))
    source_tags = [tag for tag in tags if tag.startswith("r01-") and len(tag) == 44]
    if not source_tags:
        raise OperationalEvidenceError(
            "previous task image lacks exact r01 source-SHA tag"
        )
    source_sha = source_tags[0][4:]
    conclusion = _run(
        "gh",
        "api",
        (
            f"/repos/{_required_env('GITHUB_REPOSITORY')}/actions/runs?"
            f"head_sha={source_sha}&event=push&status=completed&per_page=100"
        ),
        "--jq",
        (
            '[.workflow_runs[] | select(.name == "Required CI Gate" and '
            '.conclusion == "success")][0].conclusion // empty'
        ),
    )
    if conclusion != "success":
        raise OperationalEvidenceError(
            "previous task artifact lacks exact-SHA Required CI PASS"
        )
    return {
        "task_definition": task_definition,
        "image": image,
        "source_sha": source_sha,
    }


def _rollback_drill(root: Path) -> dict[str, object]:
    previous = _required_env("RAG14_PREVIOUS_TASK_DEFINITION")
    current = str(_service()["taskDefinition"])
    if previous == current:
        raise OperationalEvidenceError(
            "rollback requires a distinct previous task definition"
        )
    previous_evidence = _previous_release_is_verified(previous)
    rollback_health: dict[str, object] = {}
    try:
        _run(
            "aws",
            "ecs",
            "update-service",
            "--cluster",
            _CLUSTER,
            "--service",
            _SERVICE,
            "--task-definition",
            previous,
            "--force-new-deployment",
            "--region",
            _REGION,
        )
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
        rollback_status, rollback_health = _http_json("/health/ready")
        if rollback_status != 200 or rollback_health.get("status") != "ready":
            raise OperationalEvidenceError(
                "previous verified artifact did not recover health"
            )
    finally:
        _run(
            "aws",
            "ecs",
            "update-service",
            "--cluster",
            _CLUSTER,
            "--service",
            _SERVICE,
            "--task-definition",
            current,
            "--force-new-deployment",
            "--region",
            _REGION,
            check=False,
        )
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
            check=False,
        )
    status, verification = _http_json("/v1/knowledge/verify")
    if status != 200:
        raise OperationalEvidenceError(
            "current RAG.14 runtime did not recover after rollback drill"
        )
    if (
        verification.get("event_chain") != "verified"
        or verification.get("vector_index_integrity") is not True
    ):
        raise OperationalEvidenceError(
            "Knowledge integrity failed after rollback/roll-forward"
        )
    report: dict[str, object] = {
        "status": "PASS",
        "previous_verified_release": previous_evidence,
        "current_task_definition": current,
        "rollback_health": rollback_health,
        "rollforward_knowledge_verification": verification,
        "production_authority": False,
    }
    _write_json(root / "rollback-recovery.json", report)
    return report


def _manifest(root: Path) -> None:
    files: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "operational-evidence-sha256.json":
            files[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    _write_json(root / "operational-evidence-sha256.json", files)


def main() -> int:
    release_state = os.environ.get("ILAIOS_RELEASE_STATE", "CANARY")
    if release_state not in {"CANARY", ""}:
        raise OperationalEvidenceError("operational evidence runner is canary-only")
    root = Path(os.environ.get("RAG14_EVIDENCE_ROOT", "rag14-evidence"))
    root.mkdir(parents=True, exist_ok=True)
    _backup_restore_drill(root)
    _health_window(root)
    _observability_alarm_drill(root)
    _finops_meter(root)
    _rollback_drill(root)
    _manifest(root)
    print("RAG14_OPERATIONAL_EVIDENCE_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
