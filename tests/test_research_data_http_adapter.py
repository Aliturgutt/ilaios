from __future__ import annotations

import socket

import pytest

from services.research_data_factory import ResearchDataError
from services.research_data_http_adapter import (
    GovernedResearchHTTPSAdapter,
    _HTTPResult,
    register_research_https_source_handler,
)

ResolverResult = list[
    tuple[
        socket.AddressFamily,
        socket.SocketKind,
        int,
        str,
        tuple[str, int] | tuple[str, int, int, int],
    ]
]


def _public_resolver(host: str, port: int) -> ResolverResult:
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]


def test_fetch_source_returns_bounded_provenance_receipt() -> None:
    def transport(host: str, target: str, max_bytes: int, timeout: int) -> _HTTPResult:
        assert host == "data.example.com"
        assert target == "/dataset.json?year=2026"
        assert max_bytes == 1024
        assert timeout == 20
        return _HTTPResult(200, b'{"value": 7}', "application/json; charset=utf-8")

    adapter = GovernedResearchHTTPSAdapter(
        allowed_hosts=("data.example.com",),
        resolver=_public_resolver,
        transport=transport,
    )
    fetched = adapter.fetch_source(
        locator="https://data.example.com/dataset.json?year=2026",
        tenant_id="tenant-a",
        max_bytes=1024,
    )

    assert fetched.content == b'{"value": 7}'
    assert fetched.media_type == "application/json"
    assert fetched.tenant_id == "tenant-a"
    assert fetched.provider_evidence_ref.startswith("research-https:")


def test_fetch_source_denies_unallowlisted_host_before_transport() -> None:
    called = False

    def transport(host: str, target: str, max_bytes: int, timeout: int) -> _HTTPResult:
        nonlocal called
        called = True
        return _HTTPResult(200, b"{}", "application/json")

    adapter = GovernedResearchHTTPSAdapter(
        allowed_hosts=("data.example.com",),
        resolver=_public_resolver,
        transport=transport,
    )

    with pytest.raises(ResearchDataError, match="not allowlisted"):
        adapter.fetch_source(
            locator="https://evil.example.net/data.json",
            tenant_id="tenant-a",
            max_bytes=1024,
        )
    assert called is False


def test_fetch_source_denies_private_dns_answer() -> None:
    def private_resolver(host: str, port: int) -> ResolverResult:
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", port))]

    adapter = GovernedResearchHTTPSAdapter(
        allowed_hosts=("data.example.com",),
        resolver=private_resolver,
        transport=lambda host, target, max_bytes, timeout: _HTTPResult(
            200, b"{}", "application/json"
        ),
    )

    with pytest.raises(ResearchDataError, match="non-public"):
        adapter.fetch_source(
            locator="https://data.example.com/data.json",
            tenant_id="tenant-a",
            max_bytes=1024,
        )


def test_fetch_source_denies_redirect_status_and_oversize() -> None:
    adapter = GovernedResearchHTTPSAdapter(
        allowed_hosts=("data.example.com",),
        resolver=_public_resolver,
        transport=lambda host, target, max_bytes, timeout: _HTTPResult(
            302, b"redirect", "application/json"
        ),
    )
    with pytest.raises(ResearchDataError, match="non-200"):
        adapter.fetch_source(
            locator="https://data.example.com/data.json",
            tenant_id="tenant-a",
            max_bytes=1024,
        )

    oversize = GovernedResearchHTTPSAdapter(
        allowed_hosts=("data.example.com",),
        resolver=_public_resolver,
        transport=lambda host, target, max_bytes, timeout: _HTTPResult(
            200, b"x" * 11, "application/json"
        ),
    )
    with pytest.raises(ResearchDataError, match="exceeds bounded"):
        oversize.fetch_source(
            locator="https://data.example.com/data.json",
            tenant_id="tenant-a",
            max_bytes=10,
        )


def test_registration_uses_existing_gateway_and_refuses_duplicate() -> None:
    class Gateway:
        def __init__(self) -> None:
            self.handlers: dict[str, object] = {}

        def register_handler(self, name: str, handler: object) -> None:
            self.handlers[name] = handler

    gateway = Gateway()
    adapter = GovernedResearchHTTPSAdapter(
        allowed_hosts=("data.example.com",),
        resolver=_public_resolver,
        transport=lambda host, target, max_bytes, timeout: _HTTPResult(
            200, b"{}", "application/json"
        ),
    )

    register_research_https_source_handler(gateway, adapter)  # type: ignore[arg-type]
    assert "research.fetch_source" in gateway.handlers
    with pytest.raises(ResearchDataError, match="already registered"):
        register_research_https_source_handler(gateway, adapter)  # type: ignore[arg-type]
