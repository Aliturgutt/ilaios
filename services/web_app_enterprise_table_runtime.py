"""Governed enterprise-table projection for Phase 8 generated Web Apps.

This module is deliberately subordinate to ``WebAppCrudRuntime``. It adds no
identity, authorization, tenant, persistence, policy, approval, audit, evidence,
or routing authority. Table reads and selected-row validation always flow through
the canonical CRUD runtime and therefore inherit its fail-closed authorization.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from services.identity import Principal
from services.web_app_crud_runtime import CrudRecord, WebAppCrudRuntime

TableDensity = Literal["compact", "comfortable", "spacious"]
ColumnSource = Literal["resource_id", "version", "created_at", "updated_at", "payload"]


class WebAppEnterpriseTableError(ValueError):
    """Typed fail-closed table-contract error."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class EnterpriseTableColumn:
    key: str
    label: str
    source: ColumnSource
    payload_key: str | None = None


@dataclass(frozen=True, slots=True)
class EnterpriseTableRow:
    resource_id: str
    version: int
    cells: tuple[tuple[str, object | None], ...]


@dataclass(frozen=True, slots=True)
class EnterpriseTablePage:
    resource_type: str
    columns: tuple[EnterpriseTableColumn, ...]
    rows: tuple[EnterpriseTableRow, ...]
    selected_resource_ids: tuple[str, ...]
    offset: int
    limit: int
    total: int
    density: TableDensity


class WebAppEnterpriseTableRuntime:
    """Deterministic table projection over the canonical CRUD runtime."""

    def __init__(self, crud: WebAppCrudRuntime) -> None:
        self._crud = crud

    def query(
        self,
        *,
        principal: Principal,
        resource_type: str,
        columns: tuple[EnterpriseTableColumn, ...],
        now: datetime,
        offset: int = 0,
        limit: int = 50,
        filters: dict[str, object] | None = None,
        search: str | None = None,
        sort_key: str = "updated_at",
        descending: bool = False,
        selected_resource_ids: tuple[str, ...] = (),
        density: TableDensity = "comfortable",
    ) -> EnterpriseTablePage:
        self._validate_columns(columns)
        self._validate_density(density)
        self._validate_query_inputs(filters=filters, search=search)
        sort_field = self._resolve_sort_field(columns, sort_key)
        page = self._crud.list(
            principal=principal,
            resource_type=resource_type,
            now=now,
            offset=offset,
            limit=limit,
            filters=filters,
            search=search,
            sort_field=sort_field,
            descending=descending,
        )
        selected = self._validate_selection(
            principal=principal,
            resource_type=resource_type,
            selected_resource_ids=selected_resource_ids,
            now=now,
        )
        rows = tuple(self._project_row(record, columns) for record in page.items)
        return EnterpriseTablePage(
            resource_type=resource_type,
            columns=columns,
            rows=rows,
            selected_resource_ids=selected,
            offset=page.offset,
            limit=page.limit,
            total=page.total,
            density=density,
        )

    @staticmethod
    def _project_row(
        record: CrudRecord, columns: tuple[EnterpriseTableColumn, ...]
    ) -> EnterpriseTableRow:
        cells: list[tuple[str, object | None]] = []
        for column in columns:
            if column.source == "payload":
                assert column.payload_key is not None
                value = record.payload.get(column.payload_key)
            else:
                value = getattr(record, column.source)
            cells.append((column.key, value))
        return EnterpriseTableRow(
            resource_id=record.resource_id,
            version=record.version,
            cells=tuple(cells),
        )

    def _validate_selection(
        self,
        *,
        principal: Principal,
        resource_type: str,
        selected_resource_ids: tuple[str, ...],
        now: datetime,
    ) -> tuple[str, ...]:
        if len(selected_resource_ids) > 100:
            raise WebAppEnterpriseTableError(
                "SELECTION_TOO_LARGE", "selected row count exceeds bounded maximum"
            )
        if len(set(selected_resource_ids)) != len(selected_resource_ids):
            raise WebAppEnterpriseTableError(
                "DUPLICATE_SELECTION", "selected resource IDs must be unique"
            )
        for resource_id in selected_resource_ids:
            self._token(resource_id, "selected_resource_id")
            self._crud.read(
                principal=principal,
                resource_type=resource_type,
                resource_id=resource_id,
                now=now,
            )
        return selected_resource_ids

    @classmethod
    def _validate_columns(cls, columns: tuple[EnterpriseTableColumn, ...]) -> None:
        if not columns or len(columns) > 32:
            raise WebAppEnterpriseTableError(
                "INVALID_COLUMNS", "table requires between 1 and 32 columns"
            )
        keys: set[str] = set()
        for column in columns:
            cls._token(column.key, "column.key")
            cls._token(column.label, "column.label")
            if column.key in keys:
                raise WebAppEnterpriseTableError(
                    "DUPLICATE_COLUMN", "table column keys must be unique"
                )
            keys.add(column.key)
            if column.source == "payload":
                if column.payload_key is None:
                    raise WebAppEnterpriseTableError(
                        "INVALID_COLUMN", "payload column requires payload_key"
                    )
                cls._token(column.payload_key, "column.payload_key")
            elif column.payload_key is not None:
                raise WebAppEnterpriseTableError(
                    "INVALID_COLUMN", "metadata column cannot define payload_key"
                )

    @classmethod
    def _validate_query_inputs(
        cls, *, filters: dict[str, object] | None, search: str | None
    ) -> None:
        if filters is not None:
            if len(filters) > 16:
                raise WebAppEnterpriseTableError(
                    "FILTERS_TOO_LARGE", "filter count exceeds bounded maximum"
                )
            for key, value in filters.items():
                cls._token(key, "filter.key")
                cls._validate_filter_value(value)
        if search is not None:
            if len(search) > 512 or any(ord(char) < 32 for char in search):
                raise WebAppEnterpriseTableError(
                    "INVALID_SEARCH", "search text exceeds bounded or safe input limits"
                )

    @staticmethod
    def _validate_filter_value(value: object) -> None:
        if value is None or isinstance(value, bool | int):
            return
        if isinstance(value, float):
            if not math.isfinite(value):
                raise WebAppEnterpriseTableError(
                    "INVALID_FILTER_VALUE", "filter value must be finite"
                )
            return
        if isinstance(value, str):
            if len(value) > 512 or any(ord(char) < 32 for char in value):
                raise WebAppEnterpriseTableError(
                    "INVALID_FILTER_VALUE", "filter text exceeds bounded or safe input limits"
                )
            return
        raise WebAppEnterpriseTableError(
            "INVALID_FILTER_VALUE", "filter values must be bounded scalar values"
        )

    @staticmethod
    def _validate_density(density: str) -> None:
        if density not in {"compact", "comfortable", "spacious"}:
            raise WebAppEnterpriseTableError("INVALID_DENSITY", "unsupported table density")

    @staticmethod
    def _resolve_sort_field(
        columns: tuple[EnterpriseTableColumn, ...], sort_key: str
    ) -> str:
        metadata = {"resource_id", "version", "created_at", "updated_at"}
        if sort_key in metadata:
            return sort_key
        for column in columns:
            if column.key != sort_key:
                continue
            if column.source in metadata:
                return column.source
            raise WebAppEnterpriseTableError(
                "UNSUPPORTED_SORT", "payload-column sorting is not server-authoritative"
            )
        raise WebAppEnterpriseTableError("INVALID_SORT", "unknown table sort key")

    @staticmethod
    def _token(value: str, field: str) -> str:
        normalized = value.strip()
        if (
            not normalized
            or normalized != value
            or len(normalized) > 128
            or any(not char.isprintable() for char in normalized)
        ):
            raise WebAppEnterpriseTableError("INVALID_TOKEN", f"invalid {field}")
        return normalized
