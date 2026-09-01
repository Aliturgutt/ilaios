"""Evidence-backed RAG.14 canary FinOps meter and hard spend guard.

Rates are resolved at execution time from the AWS public Price List bulk files;
no currency rate is hard-coded in the repository. Cost is derived from the
actual Fargate task lifetimes observed in the canary cluster plus the observed
EFS state size. This is a bounded canary estimate, not an AWS invoice.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import time
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, cast


class FinOpsEvidenceError(RuntimeError):
    """RAG.14 FinOps evidence is unavailable, malformed, or over budget."""


_REGION = "eu-central-1"
_CLUSTER = "ilaios-r01-canary"
_ECS_PRICE_URL = (
    "https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/"
    "AmazonECS/current/eu-central-1/index.json"
)
_EFS_PRICE_URL = (
    "https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/"
    "AmazonEFS/current/eu-central-1/index.json"
)
_SECONDS_PER_MONTH = Decimal(730 * 60 * 60)
_GIB = Decimal(1024**3)


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise FinOpsEvidenceError(f"required environment variable is missing: {name}")
    return value


def _decimal_env(name: str) -> Decimal:
    raw = _required_env(name)
    try:
        value = Decimal(raw)
    except InvalidOperation as error:
        raise FinOpsEvidenceError(f"{name} must be a decimal value") from error
    if value <= 0:
        raise FinOpsEvidenceError(f"{name} must be positive")
    return value


def _run(*args: str) -> str:
    result = subprocess.run(
        args,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def _aws_json(*args: str) -> Any:
    return json.loads(_run("aws", *args, "--region", _REGION, "--output", "json"))


def _public_price_list(url: str) -> dict[str, object]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "ILAIOS-RAG14-FinOps/1"},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        if response.status != 200:
            raise FinOpsEvidenceError(f"AWS public price list returned HTTP {response.status}")
        raw = response.read()
    payload: object = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise FinOpsEvidenceError("AWS public price list is not a JSON object")
    return cast(dict[str, object], payload)


def _usd_rate_for_usage(
    price_list: dict[str, object],
    *,
    usage_contains: str,
    unit: str,
    excluded_tokens: tuple[str, ...] = (),
) -> Decimal:
    products = price_list.get("products")
    terms = price_list.get("terms")
    if not isinstance(products, dict) or not isinstance(terms, dict):
        raise FinOpsEvidenceError("AWS price list products/terms are missing")
    on_demand = terms.get("OnDemand")
    if not isinstance(on_demand, dict):
        raise FinOpsEvidenceError("AWS price list on-demand terms are missing")
    candidates: list[Decimal] = []
    for raw_sku, raw_product in products.items():
        if not isinstance(raw_sku, str) or not isinstance(raw_product, dict):
            continue
        attributes = raw_product.get("attributes")
        if not isinstance(attributes, dict):
            continue
        usage = str(attributes.get("usagetype", ""))
        if usage_contains not in usage:
            continue
        lowered = usage.lower()
        if any(token.lower() in lowered for token in excluded_tokens):
            continue
        sku_terms = on_demand.get(raw_sku)
        if not isinstance(sku_terms, dict):
            continue
        for term in sku_terms.values():
            if not isinstance(term, dict):
                continue
            dimensions = term.get("priceDimensions")
            if not isinstance(dimensions, dict):
                continue
            for dimension in dimensions.values():
                if not isinstance(dimension, dict) or dimension.get("unit") != unit:
                    continue
                price_per_unit = dimension.get("pricePerUnit")
                if not isinstance(price_per_unit, dict):
                    continue
                usd = price_per_unit.get("USD")
                if not isinstance(usd, str):
                    continue
                try:
                    rate = Decimal(usd)
                except InvalidOperation:
                    continue
                if rate >= 0:
                    candidates.append(rate)
    unique = sorted(set(candidates))
    if len(unique) != 1:
        raise FinOpsEvidenceError(
            f"expected one AWS USD rate for {usage_contains}/{unit}, found {unique}"
        )
    return unique[0]


def _parse_aws_time(value: str) -> float:
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized).timestamp()


def _task_arns(status: str) -> list[str]:
    payload = _aws_json(
        "ecs",
        "list-tasks",
        "--cluster",
        _CLUSTER,
        "--desired-status",
        status,
    )
    arns = payload.get("taskArns", [])
    if not isinstance(arns, list):
        raise FinOpsEvidenceError("ECS task list is malformed")
    return [str(item) for item in arns if isinstance(item, str)]


def _describe_tasks(arns: list[str]) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for offset in range(0, len(arns), 100):
        batch = arns[offset : offset + 100]
        if not batch:
            continue
        payload = _aws_json(
            "ecs",
            "describe-tasks",
            "--cluster",
            _CLUSTER,
            "--tasks",
            *batch,
        )
        tasks = payload.get("tasks", [])
        if not isinstance(tasks, list):
            raise FinOpsEvidenceError("ECS describe-tasks response is malformed")
        results.extend(cast(list[dict[str, object]], tasks))
    return results


def _task_resources(task_definition_arn: str) -> tuple[Decimal, Decimal]:
    payload = _aws_json(
        "ecs",
        "describe-task-definition",
        "--task-definition",
        task_definition_arn,
    )
    task = payload.get("taskDefinition")
    if not isinstance(task, dict):
        raise FinOpsEvidenceError("task definition is malformed")
    try:
        cpu_units = Decimal(str(task["cpu"]))
        memory_mib = Decimal(str(task["memory"]))
    except (KeyError, InvalidOperation) as error:
        raise FinOpsEvidenceError("task resource envelope is malformed") from error
    if cpu_units <= 0 or memory_mib <= 0:
        raise FinOpsEvidenceError("task resource envelope must be positive")
    return cpu_units / Decimal(1024), memory_mib / Decimal(1024)


def _observed_task_usage(started_after: float) -> tuple[list[dict[str, object]], Decimal, Decimal]:
    now = time.time()
    all_arns = sorted(set(_task_arns("RUNNING") + _task_arns("STOPPED")))
    tasks = _describe_tasks(all_arns)
    definition_cache: dict[str, tuple[Decimal, Decimal]] = {}
    observations: list[dict[str, object]] = []
    total_vcpu_seconds = Decimal(0)
    total_gib_seconds = Decimal(0)
    for task in tasks:
        started = task.get("startedAt")
        if not isinstance(started, str):
            continue
        started_epoch = _parse_aws_time(started)
        if started_epoch < started_after:
            continue
        stopped = task.get("stoppedAt")
        stopped_epoch = _parse_aws_time(stopped) if isinstance(stopped, str) else now
        duration_seconds = max(60, math.ceil(max(0.0, stopped_epoch - started_epoch)))
        task_definition_arn = str(task.get("taskDefinitionArn", ""))
        if not task_definition_arn:
            continue
        if task_definition_arn not in definition_cache:
            definition_cache[task_definition_arn] = _task_resources(task_definition_arn)
        vcpu, memory_gib = definition_cache[task_definition_arn]
        total_vcpu_seconds += vcpu * Decimal(duration_seconds)
        total_gib_seconds += memory_gib * Decimal(duration_seconds)
        observations.append(
            {
                "task_arn": task.get("taskArn"),
                "task_definition_arn": task_definition_arn,
                "started_at": started,
                "stopped_at": stopped,
                "billed_duration_seconds": duration_seconds,
                "vcpu": str(vcpu),
                "memory_gib": str(memory_gib),
            }
        )
    if not observations:
        raise FinOpsEvidenceError("no RAG.14 canary Fargate task usage was observed")
    return observations, total_vcpu_seconds, total_gib_seconds


def _efs_state_size() -> int:
    payload = _aws_json("efs", "describe-file-systems", "--creation-token", "ilaios-r01-canary")
    filesystems = payload.get("FileSystems", [])
    if not isinstance(filesystems, list) or len(filesystems) != 1 or not isinstance(filesystems[0], dict):
        raise FinOpsEvidenceError("RAG.14 EFS state file system is unavailable")
    size = filesystems[0].get("SizeInBytes")
    if not isinstance(size, dict) or not isinstance(size.get("Value"), int):
        raise FinOpsEvidenceError("RAG.14 EFS size evidence is malformed")
    return int(size["Value"])


def _workload_counts(root: Path) -> tuple[int, int]:
    startup_path = root / "startup-selftest.json"
    state_path = root / "live-redteam/state-after-quarantine.json"
    startup: object = json.loads(startup_path.read_text(encoding="utf-8"))
    state: object = json.loads(state_path.read_text(encoding="utf-8"))
    if not isinstance(startup, dict) or not isinstance(state, dict):
        raise FinOpsEvidenceError("RAG.14 workload evidence is malformed")
    warm = startup.get("warm_inference_sample_count")
    metrics = state.get("metrics")
    retrievals = metrics.get("retrievals") if isinstance(metrics, dict) else None
    active_units = metrics.get("active_units") if isinstance(metrics, dict) else None
    if not isinstance(warm, int) or warm < 1:
        raise FinOpsEvidenceError("startup embedding sample count is missing")
    if not isinstance(retrievals, int) or retrievals < 1:
        raise FinOpsEvidenceError("live retrieval count is missing")
    embedding_operations = warm + (active_units if isinstance(active_units, int) else 0)
    return max(1, embedding_operations), retrievals


def run(root: Path) -> dict[str, object]:
    if _required_env("RAG14_EXTERNAL_SPEND_APPROVED") != "true":
        raise FinOpsEvidenceError("RAG.14 FinOps meter requires explicit bounded spend approval")
    budget_usd = _decimal_env("RAG14_MAX_CANARY_USD")
    started_after = int(_required_env("RAG14_CANARY_STARTED_AT_MS")) / 1000.0

    ecs_prices = _public_price_list(_ECS_PRICE_URL)
    efs_prices = _public_price_list(_EFS_PRICE_URL)
    vcpu_hour_rate = _usd_rate_for_usage(
        ecs_prices,
        usage_contains="Fargate-vCPU-Hours",
        unit="hours",
        excluded_tokens=("spot", "arm", "windows"),
    )
    memory_gib_hour_rate = _usd_rate_for_usage(
        ecs_prices,
        usage_contains="Fargate-GB-Hours",
        unit="GB-Hours",
        excluded_tokens=("spot", "arm", "windows"),
    )
    efs_gib_month_rate = _usd_rate_for_usage(
        efs_prices,
        usage_contains="TimedStorage-ByteHrs",
        unit="GB-Mo",
        excluded_tokens=("ia", "archive", "infrequent"),
    )

    observations, vcpu_seconds, memory_gib_seconds = _observed_task_usage(started_after)
    observed_seconds = Decimal(str(max(1.0, time.time() - started_after)))
    efs_bytes = _efs_state_size()
    efs_gib = Decimal(efs_bytes) / _GIB
    vcpu_cost = (vcpu_seconds / Decimal(3600)) * vcpu_hour_rate
    memory_cost = (memory_gib_seconds / Decimal(3600)) * memory_gib_hour_rate
    efs_cost = efs_gib * efs_gib_month_rate * (observed_seconds / _SECONDS_PER_MONTH)
    total = vcpu_cost + memory_cost + efs_cost
    if total > budget_usd:
        raise FinOpsEvidenceError(
            f"RAG.14 canary estimated resource cost {total} USD exceeds hard budget {budget_usd} USD"
        )

    embedding_operations, retrievals = _workload_counts(root)
    report: dict[str, object] = {
        "status": "PASS",
        "region": _REGION,
        "pricing_currency": "USD",
        "pricing_source": {
            "ecs": _ECS_PRICE_URL,
            "efs": _EFS_PRICE_URL,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
        },
        "rates": {
            "fargate_vcpu_hour_usd": str(vcpu_hour_rate),
            "fargate_memory_gib_hour_usd": str(memory_gib_hour_rate),
            "efs_standard_gib_month_usd": str(efs_gib_month_rate),
        },
        "observed_usage": {
            "task_count": len(observations),
            "tasks": observations,
            "vcpu_seconds": str(vcpu_seconds),
            "memory_gib_seconds": str(memory_gib_seconds),
            "efs_state_bytes": efs_bytes,
            "observed_window_seconds": str(observed_seconds),
        },
        "estimated_resource_cost_usd": {
            "fargate_cpu": str(vcpu_cost.quantize(Decimal("0.00000001"))),
            "fargate_memory": str(memory_cost.quantize(Decimal("0.00000001"))),
            "efs_state": str(efs_cost.quantize(Decimal("0.00000001"))),
            "total": str(total.quantize(Decimal("0.00000001"))),
        },
        "workload_cost_estimates": {
            "embedding_operations_observed_or_bounded": embedding_operations,
            "retrievals_observed": retrievals,
            "approx_compute_cost_per_embedding_usd": str(
                (total / Decimal(embedding_operations)).quantize(Decimal("0.00000001"))
            ),
            "approx_compute_cost_per_retrieval_usd": str(
                (total / Decimal(retrievals)).quantize(Decimal("0.00000001"))
            ),
        },
        "external_embedding_api_fee_usd": "0",
        "external_embedding_api_fee_boundary": "SELF_HOSTED_NO_EXTERNAL_EMBEDDING_API_FEE",
        "aws_compute_cost_is_zero": False,
        "hard_canary_budget_usd": str(budget_usd),
        "budget_guard_active": True,
        "external_spend_approved": True,
        "currency_cost_claimed": True,
        "cost_claim_boundary": "observed Fargate CPU/memory plus observed EFS state at current public AWS rates; not an invoice and excludes unrelated account charges",
        "production_authority": False,
    }
    root.mkdir(parents=True, exist_ok=True)
    (root / "finops-resource-meter.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"event": "rag14_finops_evidence", **report}, sort_keys=True))
    return report


def main() -> int:
    root = Path(os.environ.get("RAG14_EVIDENCE_ROOT", "rag14-evidence"))
    run(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
