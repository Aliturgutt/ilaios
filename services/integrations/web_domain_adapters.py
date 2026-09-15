"""Provider adapters for Web custom-domain binding and DNS automation.

These adapters are side-effect boundaries only. They do not grant authority,
resolve tenant ownership, approve production changes, or replace Tool Gateway.
Callers must prove authorization before invoking mutation methods and supply
credentials through scoped providers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping, Protocol, cast

import requests

from .web_publish_runtime import DNSRecordInstruction, WebPublishError


@dataclass(frozen=True, slots=True)
class DomainBindingResult:
    provider: str
    domain: str
    verified: bool
    verification_records: tuple[DNSRecordInstruction, ...]


class VercelDomainTransport(Protocol):
    def api(
        self,
        method: str,
        path: str,
        *,
        token: str,
        team_id: str,
        json_body: Mapping[str, object] | None = None,
    ) -> tuple[int, Mapping[str, object]]: ...


class RequestsVercelDomainTransport:
    def __init__(self, *, timeout_seconds: float = 30.0) -> None:
        if timeout_seconds <= 0:
            raise ValueError("Vercel domain timeout must be positive")
        self._timeout_seconds = timeout_seconds

    def api(
        self,
        method: str,
        path: str,
        *,
        token: str,
        team_id: str,
        json_body: Mapping[str, object] | None = None,
    ) -> tuple[int, Mapping[str, object]]:
        response = requests.request(
            method,
            f"https://api.vercel.com{path}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            params={"teamId": team_id},
            json=None if json_body is None else dict(json_body),
            timeout=self._timeout_seconds,
        )
        try:
            value = response.json()
        except ValueError:
            value = {}
        if not isinstance(value, dict):
            value = {"payload": value}
        return response.status_code, cast(dict[str, object], value)


class VercelProjectDomainAdapter:
    """Attach and verify a custom domain on an existing Vercel project."""

    provider_id = "vercel.project-domain.v1"

    def __init__(
        self,
        *,
        team_id: str,
        project_id: str,
        credential_provider: Callable[[], str],
        transport: VercelDomainTransport | None = None,
    ) -> None:
        if not team_id.strip() or not project_id.strip():
            raise ValueError("Vercel team and project identifiers are required")
        self._team_id = team_id.strip()
        self._project_id = project_id.strip()
        self._credential_provider = credential_provider
        self._transport = transport or RequestsVercelDomainTransport()

    def request_binding(
        self,
        domain: str,
        *,
        authorization_proven: bool,
    ) -> DomainBindingResult:
        if authorization_proven is not True:
            raise WebPublishError("custom-domain mutation authorization is not proven")
        normalized = _domain(domain)
        token = self._credential()
        status, value = self._transport.api(
            "POST",
            f"/v9/projects/{self._project_id}/domains",
            token=token,
            team_id=self._team_id,
            json_body={"name": normalized},
        )
        if status not in {200, 201}:
            raise WebPublishError(f"Vercel project-domain binding failed with HTTP {status}")
        return _vercel_result(value, normalized)

    def verify_binding(
        self,
        domain: str,
        *,
        authorization_proven: bool,
    ) -> DomainBindingResult:
        if authorization_proven is not True:
            raise WebPublishError("custom-domain verification authorization is not proven")
        normalized = _domain(domain)
        token = self._credential()
        status, value = self._transport.api(
            "POST",
            f"/v9/projects/{self._project_id}/domains/{normalized}/verify",
            token=token,
            team_id=self._team_id,
        )
        if status != 200:
            raise WebPublishError(f"Vercel project-domain verification failed with HTTP {status}")
        return _vercel_result(value, normalized)

    def _credential(self) -> str:
        token = self._credential_provider().strip()
        if not token:
            raise WebPublishError("Vercel domain credential is unavailable")
        return token


class CloudflareDNSTransport(Protocol):
    def api(
        self,
        method: str,
        path: str,
        *,
        token: str,
        json_body: Mapping[str, object] | None = None,
    ) -> tuple[int, Mapping[str, object]]: ...


class RequestsCloudflareDNSTransport:
    def __init__(self, *, timeout_seconds: float = 30.0) -> None:
        if timeout_seconds <= 0:
            raise ValueError("Cloudflare DNS timeout must be positive")
        self._timeout_seconds = timeout_seconds

    def api(
        self,
        method: str,
        path: str,
        *,
        token: str,
        json_body: Mapping[str, object] | None = None,
    ) -> tuple[int, Mapping[str, object]]:
        response = requests.request(
            method,
            f"https://api.cloudflare.com/client/v4{path}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=None if json_body is None else dict(json_body),
            timeout=self._timeout_seconds,
        )
        try:
            value = response.json()
        except ValueError:
            value = {}
        if not isinstance(value, dict):
            value = {"payload": value}
        return response.status_code, cast(dict[str, object], value)


class CloudflareDNSAdapter:
    """Create exact CNAME/TXT records in one pre-authorized Cloudflare zone."""

    provider_id = "cloudflare.dns.v1"

    def __init__(
        self,
        *,
        zone_id: str,
        credential_provider: Callable[[], str],
        transport: CloudflareDNSTransport | None = None,
    ) -> None:
        if not zone_id.strip():
            raise ValueError("Cloudflare zone identifier is required")
        self._zone_id = zone_id.strip()
        self._credential_provider = credential_provider
        self._transport = transport or RequestsCloudflareDNSTransport()

    def create_records(
        self,
        records: tuple[DNSRecordInstruction, ...],
        *,
        zone_name: str,
        authorization_proven: bool,
    ) -> tuple[str, ...]:
        if authorization_proven is not True:
            raise WebPublishError("DNS mutation authorization is not proven")
        if not records:
            raise WebPublishError("DNS record set cannot be empty")
        zone = _domain(zone_name)
        token = self._credential()
        created: list[str] = []
        for record in records:
            if record.record_type not in {"CNAME", "TXT"}:
                raise WebPublishError("unsupported DNS record type")
            name = _record_name(record.name, zone)
            body: dict[str, object] = {
                "type": record.record_type,
                "name": name,
                "content": record.value,
                "ttl": 1,
            }
            if record.record_type == "CNAME":
                body["proxied"] = False
            status, value = self._transport.api(
                "POST",
                f"/zones/{self._zone_id}/dns_records",
                token=token,
                json_body=body,
            )
            if status not in {200, 201} or value.get("success") is not True:
                raise WebPublishError(
                    f"Cloudflare DNS record creation failed with HTTP {status}"
                )
            result = value.get("result")
            if not isinstance(result, dict) or not isinstance(result.get("id"), str):
                raise WebPublishError("Cloudflare DNS response is missing record identity")
            created.append(str(result["id"]))
        return tuple(created)

    def _credential(self) -> str:
        token = self._credential_provider().strip()
        if not token:
            raise WebPublishError("Cloudflare DNS credential is unavailable")
        return token


def _vercel_result(value: Mapping[str, object], domain: str) -> DomainBindingResult:
    name = value.get("name")
    if name != domain:
        raise WebPublishError("Vercel project-domain identity mismatch")
    records: list[DNSRecordInstruction] = []
    raw = value.get("verification")
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            record_type = str(item.get("type", "")).upper()
            record_domain = str(item.get("domain", "")).strip()
            value_text = str(item.get("value", "")).strip()
            if record_type not in {"TXT", "CNAME"} or not record_domain or not value_text:
                continue
            records.append(
                DNSRecordInstruction(
                    record_type,
                    record_domain,
                    value_text,
                    "verify custom domain for Vercel project",
                )
            )
    return DomainBindingResult(
        provider=VercelProjectDomainAdapter.provider_id,
        domain=domain,
        verified=value.get("verified") is True,
        verification_records=tuple(records),
    )


def _record_name(name: str, zone: str) -> str:
    value = name.strip().lower().rstrip(".")
    if value == "@":
        return zone
    if value.endswith(f".{zone}") or value == zone:
        return value
    return f"{value}.{zone}"


def _domain(value: str) -> str:
    normalized = value.strip().lower().rstrip(".")
    if not normalized or "/" in normalized or ":" in normalized or "." not in normalized:
        raise WebPublishError("domain name is invalid")
    return normalized


__all__ = [
    "CloudflareDNSAdapter",
    "CloudflareDNSTransport",
    "DomainBindingResult",
    "RequestsCloudflareDNSTransport",
    "RequestsVercelDomainTransport",
    "VercelDomainTransport",
    "VercelProjectDomainAdapter",
]
