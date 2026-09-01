"""Read-only operational projection over durable publication side-effect state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum

from .publication_ledger import (
    PublicationRecord,
    PublicationSideEffectLedger,
    PublicationState,
)


class PublicationAlertSeverity(str, Enum):
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class PublicationRecoveryAction(str, Enum):
    RECONCILE_PLATFORM_STATE = "RECONCILE_PLATFORM_STATE"
    REVIEW_FAILED_PUBLICATION = "REVIEW_FAILED_PUBLICATION"
    REAUTHORIZE_OAUTH = "REAUTHORIZE_OAUTH"
    CREATE_NEW_GOVERNED_PACKAGE = "CREATE_NEW_GOVERNED_PACKAGE"


@dataclass(frozen=True, slots=True)
class PublicationAlert:
    package_id: str
    platform: str
    account_id: str
    severity: PublicationAlertSeverity
    reason: str
    recommended_actions: tuple[PublicationRecoveryAction, ...]


@dataclass(frozen=True, slots=True)
class PublicationOperationsSnapshot:
    generated_at: str
    total: int
    prepared: int
    submitting: int
    published: int
    ambiguous: int
    failed: int
    alerts: tuple[PublicationAlert, ...]


class PublicationOperationsProjector:
    """Produce dashboard/alert input without mutating publication state."""

    def __init__(self, ledger: PublicationSideEffectLedger) -> None:
        self._ledger = ledger

    def snapshot(
        self,
        *,
        now: datetime | None = None,
        stale_submitting_after: timedelta = timedelta(minutes=15),
    ) -> PublicationOperationsSnapshot:
        observed_now = now or datetime.now(timezone.utc)
        if observed_now.tzinfo is None or observed_now.utcoffset() is None:
            raise ValueError("observability now must be timezone-aware")
        if stale_submitting_after <= timedelta(0):
            raise ValueError("stale_submitting_after must be positive")
        records = self._ledger.records()
        counts = {state: 0 for state in PublicationState}
        alerts: list[PublicationAlert] = []
        for record in records:
            counts[record.state] += 1
            alert = _alert_for_record(
                record,
                now=observed_now,
                stale_submitting_after=stale_submitting_after,
            )
            if alert is not None:
                alerts.append(alert)
        return PublicationOperationsSnapshot(
            generated_at=observed_now.astimezone(timezone.utc).isoformat(),
            total=len(records),
            prepared=counts[PublicationState.PREPARED],
            submitting=counts[PublicationState.SUBMITTING],
            published=counts[PublicationState.PUBLISHED],
            ambiguous=counts[PublicationState.AMBIGUOUS],
            failed=counts[PublicationState.FAILED],
            alerts=tuple(sorted(alerts, key=lambda item: (item.severity.value, item.package_id))),
        )


def _alert_for_record(
    record: PublicationRecord,
    *,
    now: datetime,
    stale_submitting_after: timedelta,
) -> PublicationAlert | None:
    if record.state is PublicationState.AMBIGUOUS:
        return PublicationAlert(
            package_id=record.package_id,
            platform=record.platform,
            account_id=record.account_id,
            severity=PublicationAlertSeverity.CRITICAL,
            reason="publication outcome is ambiguous; blind repost is prohibited",
            recommended_actions=(PublicationRecoveryAction.RECONCILE_PLATFORM_STATE,),
        )
    if record.state is PublicationState.FAILED:
        return PublicationAlert(
            package_id=record.package_id,
            platform=record.platform,
            account_id=record.account_id,
            severity=PublicationAlertSeverity.WARNING,
            reason="publication failed explicitly; same package remains non-retryable",
            recommended_actions=(
                PublicationRecoveryAction.REVIEW_FAILED_PUBLICATION,
                PublicationRecoveryAction.REAUTHORIZE_OAUTH,
                PublicationRecoveryAction.CREATE_NEW_GOVERNED_PACKAGE,
            ),
        )
    if record.state is PublicationState.SUBMITTING:
        updated_at = datetime.fromisoformat(record.updated_at)
        if updated_at.tzinfo is None or updated_at.utcoffset() is None:
            raise ValueError("publication ledger timestamp must be timezone-aware")
        if now - updated_at > stale_submitting_after:
            return PublicationAlert(
                package_id=record.package_id,
                platform=record.platform,
                account_id=record.account_id,
                severity=PublicationAlertSeverity.CRITICAL,
                reason="publication remained SUBMITTING beyond the stale threshold",
                recommended_actions=(PublicationRecoveryAction.RECONCILE_PLATFORM_STATE,),
            )
    return None
