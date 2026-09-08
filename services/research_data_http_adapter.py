"""Governed HTTPS source adapter for the existing Research/Data ToolGateway contract."""

from __future__ import annotations

import hashlib
import ipaddress
import socket
import ssl
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from http.client import HTTPSConnection
from typing import Protocol
from urllib.parse import urlsplit

from services.research_data_factory import FetchedResearchSource, ResearchDataError


class ResearchHandlerGateway(Protocol):
    """Registration surface already provided by the canonical ToolGateway."""

    handlers: dict[str, Callable[..., object]]

    def register_handler(self, name: str, handler: Callable[..., object]) -> None: ...


@dataclass(frozen=True, slots=True)
class _HTTPResult:
    status: int
    content: bytes
    media_type: str


Resolver = Callable[[str, int], list[tuple[int, int, int, str, tuple[str, int]]]]
Transport = Callable[[str, str, int, int], _HTTPResult]


class GovernedResearchHTTPSAdapter:
    """Bounded HTTPS GET adapter registered behind the incumbent ToolGateway.

    The adapter is intentionally read-only, requires an explicit host allowlist,
    rejects non-public DNS answers and redirects, enforces response byte limits,
    and emits a deterministic provider evidence reference for ingestion provenance.
    """

    def __init__(
        self,
        *,
        allowed_hosts: tuple[str, ...],
        timeout_seconds: int = 20,
        resolver: Resolver | None = None,
        transport: Transport | None = None,
    ) -> None:
        normalized = tuple(sorted({host.strip().lower().rstrip(".") for host in allowed_hosts}))
        if not normalized or any(not host for host in normalized):
            raise ResearchDataError("research HTTPS adapter requires allowed_hosts")
        if timeout_seconds < 1 or timeout_seconds > 60:
            raise ResearchDataError("research HTTPS timeout is outside bounded limits")
        self._allowed_hosts = frozenset(normalized)
        self._timeout_seconds = timeout_seconds
        self._resolver = resolver or _resolve_host
        self._transport = transport or self._https_get

    def fetch_source(
        self,
        *,
        locator: str,
        tenant_id: str,
        max_bytes: int,
    ) -> FetchedResearchSource:
        """Fetch one allowlisted public HTTPS JSON/CSV source and return provenance."""

        tenant = tenant_id.strip()
        if not tenant:
            raise ResearchDataError("research HTTPS fetch requires tenant_id")
        if max_bytes < 1 or max_bytes > 25_000_000:
            raise ResearchDataError("research HTTPS max_bytes is outside bounded limits")
        parsed = urlsplit(locator)
        if (
            parsed.scheme.lower() != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
        ):
            raise ResearchDataError("research HTTPS locator must be credential-free HTTPS")
        if parsed.port not in {None, 443}:
            raise ResearchDataError("research HTTPS locator must use port 443")
        host = parsed.hostname.lower().rstrip(".")
        if host not in self._allowed_hosts:
            raise ResearchDataError("research HTTPS host is not allowlisted")
        _require_public_dns(host, self._resolver)

        target = parsed.path or "/"
        if parsed.query:
            target = f"{target}?{parsed.query}"
        result = self._transport(host, target, max_bytes, self._timeout_seconds)
        if result.status != 200:
            raise ResearchDataError("research HTTPS source returned non-200 status")
        if not result.content:
            raise ResearchDataError("research HTTPS source returned empty content")
        if len(result.content) > max_bytes:
            raise ResearchDataError("research HTTPS source exceeds bounded ingestion limit")
        media_type = result.media_type.split(";", 1)[0].strip().lower()
        if media_type not in {
            "application/json",
            "text/json",
            "text/csv",
            "application/csv",
            "application/vnd.api+json",
        }:
            raise ResearchDataError("research HTTPS source media type is not allowed")

        retrieved_at = datetime.now(UTC).isoformat()
        content_sha256 = hashlib.sha256(result.content).hexdigest()
        evidence_ref = "research-https:" + hashlib.sha256(
            f"{locator}\n{retrieved_at}\n{content_sha256}".encode("utf-8")
        ).hexdigest()
        return FetchedResearchSource(
            final_locator=locator,
            content=result.content,
            retrieved_at=retrieved_at,
            media_type=media_type,
            provider_evidence_ref=evidence_ref,
            tenant_id=tenant,
        )

    @staticmethod
    def _https_get(host: str, target: str, max_bytes: int, timeout_seconds: int) -> _HTTPResult:
        context = ssl.create_default_context()
        connection = HTTPSConnection(host, 443, timeout=timeout_seconds, context=context)
        try:
            connection.request(
                "GET",
                target,
                headers={
                    "Accept": "application/json, text/csv;q=0.9",
                    "User-Agent": "ILAIOS-ResearchData/1",
                    "Connection": "close",
                },
            )
            response = connection.getresponse()
            if 300 <= response.status < 400:
                raise ResearchDataError("research HTTPS redirects are denied")
            content_length = response.getheader("Content-Length")
            if content_length is not None:
                try:
                    declared_length = int(content_length)
                except ValueError as exc:
                    raise ResearchDataError("research HTTPS Content-Length is invalid") from exc
                if declared_length < 0 or declared_length > max_bytes:
                    raise ResearchDataError("research HTTPS source exceeds bounded ingestion limit")
            content = response.read(max_bytes + 1)
            media_type = response.getheader("Content-Type", "")
            return _HTTPResult(response.status, content, media_type)
        except (OSError, ssl.SSLError) as exc:
            raise ResearchDataError("research HTTPS transport failed closed") from exc
        finally:
            connection.close()


def register_research_https_source_handler(
    gateway: ResearchHandlerGateway,
    adapter: GovernedResearchHTTPSAdapter,
) -> None:
    """Install the Research/Data read adapter without replacing an existing authority."""

    tool_name = "research.fetch_source"
    if tool_name in gateway.handlers:
        raise ResearchDataError("research source handler is already registered")
    gateway.register_handler(tool_name, adapter.fetch_source)


def _resolve_host(host: str, port: int) -> list[tuple[int, int, int, str, tuple[str, int]]]:
    return socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)


def _require_public_dns(host: str, resolver: Resolver) -> None:
    try:
        answers = resolver(host, 443)
    except OSError as exc:
        raise ResearchDataError("research HTTPS DNS resolution failed closed") from exc
    if not answers:
        raise ResearchDataError("research HTTPS DNS returned no addresses")
    for answer in answers:
        sockaddr = answer[4]
        if not sockaddr:
            raise ResearchDataError("research HTTPS DNS answer is invalid")
        try:
            address = ipaddress.ip_address(sockaddr[0])
        except ValueError as exc:
            raise ResearchDataError("research HTTPS DNS answer is invalid") from exc
        if not address.is_global:
            raise ResearchDataError("research HTTPS DNS resolved to a non-public address")
