"""Desktop-only contracts for server-produced, read-only agent trust evidence.

Only trusted in-process providers may construct these records. Neither HTTP
payloads nor historical runtime routes constitute current live evidence.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class LiveEvidence:
    agent_id: str
    producer_id: str
    observed_at: datetime
    expires_at: datetime
    status: str
    authenticated: bool


@dataclass(frozen=True)
class AgentAdapterEvidence:
    agent_id: str
    adapter_id: str
    producer_id: str
    verified_at: datetime
    expires_at: datetime
    verified: bool
    agent_bound: bool


def _valid_window(start: datetime, end: datetime, now: datetime,
                  max_age: timedelta) -> bool:
    return (start.tzinfo is not None and end.tzinfo is not None
            and now.tzinfo is not None and max_age > timedelta(0)
            and start <= now <= end and end > start
            and now - start <= max_age)


def validate_live(e: LiveEvidence | None, *, agent_id: str, now: datetime,
                  trusted_producers: frozenset[str],
                  max_age: timedelta = timedelta(seconds=30)) -> bool:
    return bool(e is not None and agent_id and e.agent_id == agent_id
                and e.producer_id in trusted_producers and e.authenticated
                and e.status == 'idle'
                and _valid_window(e.observed_at, e.expires_at, now, max_age))


def validate_adapter(e: AgentAdapterEvidence | None, *, agent_id: str,
                     adapter_id: str, now: datetime,
                     trusted_producers: frozenset[str],
                     max_age: timedelta = timedelta(minutes=5)) -> bool:
    return bool(e is not None and agent_id and adapter_id
                and e.agent_id == agent_id and e.adapter_id == adapter_id
                and e.producer_id in trusted_producers and e.verified
                and e.agent_bound
                and _valid_window(e.verified_at, e.expires_at, now, max_age))
