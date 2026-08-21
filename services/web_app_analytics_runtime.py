"""Authenticated analytics projection for Phase 6 generated Web Apps.

Analytics is a read-only projection over the canonical Phase-5 CRUD runtime. It
inherits canonical authorization, tenant/project scoping and resource visibility
from ``WebAppCrudRuntime`` and cannot mutate records or create a second data or
authorization authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Literal

from services.identity import Principal
from services.web_app_crud_runtime import CrudRecord, WebAppCrudRuntime

AnalyticsMetric = Literal["count", "sum"]


class WebAppAnalyticsRuntimeError(RuntimeError):
    """Typed fail-closed analytics projection failure."""

    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


@dataclass(frozen=True, slots=True)
class AnalyticsPoint:
    category: str
    value: float
    records: int


@dataclass(frozen=True, slots=True)
class AnalyticsSeries:
    resource_type: str
    dimension: str
    metric: AnalyticsMetric
    metric_field: str | None
    points: tuple[AnalyticsPoint, ...]
    source_total: int
    covered_records: int
    truncated: bool


class WebAppAnalyticsRuntime:
    """Build deterministic chart-ready aggregates from authenticated CRUD data."""

    def __init__(self, crud: WebAppCrudRuntime, *, max_records: int = 1000) -> None:
        if max_records < 1 or max_records > 10_000:
            raise ValueError("max_records outside bounded range")
        self._crud = crud
        self._max_records = max_records

    def series(
        self,
        *,
        principal: Principal,
        resource_type: str,
        dimension: str,
        metric: AnalyticsMetric,
        now: datetime,
        metric_field: str | None = None,
        filters: dict[str, object] | None = None,
        search: str | None = None,
    ) -> AnalyticsSeries:
        self._field(dimension, "dimension")
        if metric not in ("count", "sum"):
            raise WebAppAnalyticsRuntimeError("INVALID_METRIC", "unsupported analytics metric")
        if metric == "sum":
            if metric_field is None:
                raise WebAppAnalyticsRuntimeError(
                    "MISSING_METRIC_FIELD", "sum metric requires metric_field"
                )
            self._field(metric_field, "metric_field")
        elif metric_field is not None:
            raise WebAppAnalyticsRuntimeError(
                "UNEXPECTED_METRIC_FIELD", "count metric does not accept metric_field"
            )

        records: list[CrudRecord] = []
        offset = 0
        source_total = 0
        while len(records) < self._max_records:
            limit = min(100, self._max_records - len(records))
            page = self._crud.list(
                principal=principal,
                resource_type=resource_type,
                now=now,
                offset=offset,
                limit=limit,
                filters=filters,
                search=search,
                sort_field="resource_id",
            )
            source_total = page.total
            records.extend(page.items)
            offset += len(page.items)
            if not page.items or offset >= page.total:
                break

        buckets: dict[str, tuple[Decimal, int]] = {}
        for record in records:
            if dimension not in record.payload:
                raise WebAppAnalyticsRuntimeError(
                    "MISSING_DIMENSION", f"record {record.resource_id} is missing dimension"
                )
            category = self._category(record.payload[dimension])
            total, count = buckets.get(category, (Decimal(0), 0))
            if metric == "count":
                buckets[category] = (total + Decimal(1), count + 1)
                continue
            assert metric_field is not None
            if metric_field not in record.payload:
                raise WebAppAnalyticsRuntimeError(
                    "MISSING_METRIC_VALUE", f"record {record.resource_id} is missing metric value"
                )
            buckets[category] = (
                total + self._number(record.payload[metric_field], record.resource_id),
                count + 1,
            )

        points = tuple(
            AnalyticsPoint(category=category, value=float(total), records=count)
            for category, (total, count) in sorted(buckets.items(), key=lambda item: item[0])
        )
        return AnalyticsSeries(
            resource_type=resource_type,
            dimension=dimension,
            metric=metric,
            metric_field=metric_field,
            points=points,
            source_total=source_total,
            covered_records=len(records),
            truncated=source_total > len(records),
        )

    @staticmethod
    def _field(value: str, label: str) -> None:
        if not value or len(value) > 80 or not value.replace("_", "").isalnum():
            raise WebAppAnalyticsRuntimeError("INVALID_FIELD", f"invalid {label}")

    @staticmethod
    def _category(value: object) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (str, int)) and not isinstance(value, bool):
            rendered = str(value).strip()
            if rendered and len(rendered) <= 120:
                return rendered
        raise WebAppAnalyticsRuntimeError(
            "INVALID_DIMENSION_VALUE", "analytics dimension must be bounded scalar"
        )

    @staticmethod
    def _number(value: object, resource_id: str) -> Decimal:
        if isinstance(value, bool) or not isinstance(value, (int, float, str)):
            raise WebAppAnalyticsRuntimeError(
                "INVALID_METRIC_VALUE", f"record {resource_id} metric is not numeric"
            )
        try:
            number = Decimal(str(value))
        except InvalidOperation as exc:
            raise WebAppAnalyticsRuntimeError(
                "INVALID_METRIC_VALUE", f"record {resource_id} metric is not numeric"
            ) from exc
        if not number.is_finite():
            raise WebAppAnalyticsRuntimeError(
                "INVALID_METRIC_VALUE", f"record {resource_id} metric is not finite"
            )
        return number


__all__ = [
    "AnalyticsPoint",
    "AnalyticsSeries",
    "WebAppAnalyticsRuntime",
    "WebAppAnalyticsRuntimeError",
]
