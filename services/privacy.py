"""Tenant privacy, residency, retention, legal hold, export, and DLP controls."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from enum import Enum


class PrivacyError(PermissionError):
    """A privacy or tenant-data boundary denied an operation."""


class DataState(str, Enum):
    ACTIVE = "active"
    DELETION_PENDING = "deletion_pending"
    DELETED = "deleted"


@dataclass(frozen=True, slots=True)
class RegulatoryProfile:
    profile_id: str
    required_regions: frozenset[str]
    prohibited_export_classes: frozenset[str]
    independently_certified: bool = False


@dataclass(frozen=True, slots=True)
class TenantDataPolicy:
    tenant_id: str
    allowed_regions: frozenset[str]
    retention: timedelta
    allowed_purposes: frozenset[str]
    allowed_fields: frozenset[str]
    dlp_blocked_classes: frozenset[str]
    regulatory_profile: RegulatoryProfile | None = None

    def __post_init__(self) -> None:
        if (
            not self.tenant_id
            or not self.allowed_regions
            or self.retention <= timedelta(0)
        ):
            raise ValueError("tenant, residency, and positive retention are required")


@dataclass(frozen=True, slots=True)
class DataRecord:
    record_id: str
    tenant_id: str
    region: str
    purpose: str
    fields: tuple[tuple[str, str], ...]
    classifications: frozenset[str]
    created_at: datetime
    state: DataState = DataState.ACTIVE
    deletion_due: datetime | None = None


@dataclass(frozen=True, slots=True)
class LegalHold:
    hold_id: str
    tenant_id: str
    record_id: str
    reason: str
    approved_by: str
    active: bool = True


@dataclass(frozen=True, slots=True)
class PrivacyEvent:
    operation: str
    tenant_id: str
    record_id: str
    actor_id: str
    occurred_at: datetime
    reason: str


class TenantDataStore:
    """Reference authoritative boundary; every operation carries tenant context."""

    def __init__(self) -> None:
        self._policies: dict[str, TenantDataPolicy] = {}
        self._records: dict[str, DataRecord] = {}
        self._holds: dict[str, LegalHold] = {}
        self._events: list[PrivacyEvent] = []

    def register_policy(self, policy: TenantDataPolicy) -> None:
        if policy.regulatory_profile is not None:
            required = policy.regulatory_profile.required_regions
            if required and not policy.allowed_regions <= required:
                raise PrivacyError("tenant residency conflicts with regulatory profile")
        self._policies[policy.tenant_id] = policy

    def create(self, record: DataRecord, actor_id: str) -> None:
        policy = self._policy(record.tenant_id)
        if record.record_id in self._records:
            raise PrivacyError("record already exists")
        if record.region not in policy.allowed_regions:
            raise PrivacyError("residency policy denied region")
        if record.purpose not in policy.allowed_purposes:
            raise PrivacyError("purpose limitation denied processing")
        if not {name for name, _ in record.fields} <= policy.allowed_fields:
            raise PrivacyError("data minimization denied unapproved fields")
        self._records[record.record_id] = record
        self._event("create", record, actor_id, record.created_at, record.purpose)

    def read(
        self, record_id: str, tenant_id: str, actor_id: str, now: datetime
    ) -> DataRecord:
        record = self._record(record_id, tenant_id)
        if record.state is not DataState.ACTIVE:
            raise PrivacyError("record is not active")
        self._event("read", record, actor_id, now, "authorized tenant read")
        return record

    def export(
        self, record_id: str, tenant_id: str, actor_id: str, now: datetime
    ) -> DataRecord:
        record = self._record(record_id, tenant_id)
        policy = self._policy(tenant_id)
        blocked = set(record.classifications) & set(policy.dlp_blocked_classes)
        profile = policy.regulatory_profile
        if profile is not None:
            blocked |= set(record.classifications) & set(
                profile.prohibited_export_classes
            )
        if blocked:
            raise PrivacyError("DLP denied export")
        self._event("export", record, actor_id, now, "approved tenant export")
        return record

    def place_hold(self, hold: LegalHold, actor_id: str, now: datetime) -> None:
        self._record(hold.record_id, hold.tenant_id)
        if not hold.reason or not hold.approved_by or hold.hold_id in self._holds:
            raise PrivacyError("legal hold requires unique approval and reason")
        self._holds[hold.hold_id] = hold
        self._event(
            "legal_hold", self._records[hold.record_id], actor_id, now, hold.reason
        )

    def release_hold(self, hold_id: str, actor_id: str, now: datetime) -> None:
        hold = self._holds.get(hold_id)
        if hold is None or not hold.active:
            raise PrivacyError("active legal hold not found")
        self._holds[hold_id] = replace(hold, active=False)
        self._event(
            "release_hold", self._records[hold.record_id], actor_id, now, hold.reason
        )

    def request_deletion(
        self, record_id: str, tenant_id: str, actor_id: str, now: datetime
    ) -> DataRecord:
        record = self._record(record_id, tenant_id)
        if any(
            hold.active and hold.record_id == record_id and hold.tenant_id == tenant_id
            for hold in self._holds.values()
        ):
            raise PrivacyError("active legal hold blocks deletion")
        due = min(record.created_at + self._policy(tenant_id).retention, now)
        updated = replace(record, state=DataState.DELETION_PENDING, deletion_due=due)
        self._records[record_id] = updated
        self._event(
            "deletion_request", updated, actor_id, now, "tenant deletion workflow"
        )
        return updated

    def execute_deletion(
        self, record_id: str, tenant_id: str, actor_id: str, now: datetime
    ) -> DataRecord:
        record = self._record(record_id, tenant_id)
        if (
            record.state is not DataState.DELETION_PENDING
            or record.deletion_due is None
            or now < record.deletion_due
        ):
            raise PrivacyError("deletion is not due")
        updated = replace(record, state=DataState.DELETED, fields=())
        self._records[record_id] = updated
        self._event("delete", updated, actor_id, now, "retention/deletion lifecycle")
        return updated

    def events(self) -> tuple[PrivacyEvent, ...]:
        return tuple(self._events)

    def _policy(self, tenant_id: str) -> TenantDataPolicy:
        try:
            return self._policies[tenant_id]
        except KeyError as exc:
            raise PrivacyError("tenant policy not found") from exc

    def _record(self, record_id: str, tenant_id: str) -> DataRecord:
        record = self._records.get(record_id)
        if record is None or record.tenant_id != tenant_id:
            raise PrivacyError("record not found for tenant")
        return record

    def _event(
        self,
        operation: str,
        record: DataRecord,
        actor_id: str,
        now: datetime,
        reason: str,
    ) -> None:
        self._events.append(
            PrivacyEvent(
                operation, record.tenant_id, record.record_id, actor_id, now, reason
            )
        )
