from collections.abc import Mapping

import pytest

from services.integrations.web_domain_adapters import (
    CloudflareDNSAdapter,
    VercelProjectDomainAdapter,
)
from services.integrations.web_publish_runtime import DNSRecordInstruction, WebPublishError


class _VercelTransport:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, object]] = []

    def api(
        self,
        method: str,
        path: str,
        *,
        token: str,
        team_id: str,
        json_body: Mapping[str, object] | None = None,
    ) -> tuple[int, Mapping[str, object]]:
        self.calls.append((method, path, json_body))
        if path.endswith("/verify"):
            return 200, {"name": "www.ornek.com", "verified": True}
        return 200, {
            "name": "www.ornek.com",
            "verified": False,
            "verification": [
                {
                    "type": "TXT",
                    "domain": "_vercel.www.ornek.com",
                    "value": "challenge-123",
                }
            ],
        }


class _CloudflareTransport:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, object]] = []
        self.counter = 0

    def api(
        self,
        method: str,
        path: str,
        *,
        token: str,
        json_body: Mapping[str, object] | None = None,
    ) -> tuple[int, Mapping[str, object]]:
        self.calls.append((method, path, json_body))
        self.counter += 1
        return 200, {"success": True, "result": {"id": f"dns-{self.counter}"}}


def test_vercel_project_domain_binding_is_authority_gated() -> None:
    transport = _VercelTransport()
    adapter = VercelProjectDomainAdapter(
        team_id="team_test",
        project_id="prj_test",
        credential_provider=lambda: "secret-token",
        transport=transport,
    )
    with pytest.raises(WebPublishError, match="authorization"):
        adapter.request_binding("www.ornek.com", authorization_proven=False)
    assert transport.calls == []

    pending = adapter.request_binding("www.ornek.com", authorization_proven=True)
    assert pending.verified is False
    assert pending.verification_records[0].record_type == "TXT"
    assert transport.calls[0][1] == "/v9/projects/prj_test/domains"

    verified = adapter.verify_binding("www.ornek.com", authorization_proven=True)
    assert verified.verified is True
    assert transport.calls[1][1].endswith("/www.ornek.com/verify")


def test_vercel_project_domain_rejects_identity_mismatch() -> None:
    class _Wrong(_VercelTransport):
        def api(self, *args: object, **kwargs: object) -> tuple[int, Mapping[str, object]]:
            return 200, {"name": "attacker.example", "verified": True}

    adapter = VercelProjectDomainAdapter(
        team_id="team_test",
        project_id="prj_test",
        credential_provider=lambda: "secret-token",
        transport=_Wrong(),
    )
    with pytest.raises(WebPublishError, match="identity mismatch"):
        adapter.request_binding("www.ornek.com", authorization_proven=True)


def test_cloudflare_dns_creates_only_exact_authorized_records() -> None:
    transport = _CloudflareTransport()
    adapter = CloudflareDNSAdapter(
        zone_id="zone_test",
        credential_provider=lambda: "cloudflare-token",
        transport=transport,
    )
    records = (
        DNSRecordInstruction("CNAME", "www", "target.example", "route"),
        DNSRecordInstruction("TXT", "_verify", "token-123", "ownership"),
    )
    ids = adapter.create_records(
        records,
        zone_name="ornek.com",
        authorization_proven=True,
    )
    assert ids == ("dns-1", "dns-2")
    assert transport.calls[0][1] == "/zones/zone_test/dns_records"
    first = transport.calls[0][2]
    assert isinstance(first, dict)
    assert first["name"] == "www.ornek.com"
    assert first["content"] == "target.example"
    assert first["proxied"] is False


def test_cloudflare_dns_never_mutates_without_authority() -> None:
    transport = _CloudflareTransport()
    adapter = CloudflareDNSAdapter(
        zone_id="zone_test",
        credential_provider=lambda: "cloudflare-token",
        transport=transport,
    )
    with pytest.raises(WebPublishError, match="authorization"):
        adapter.create_records(
            (DNSRecordInstruction("TXT", "_verify", "token", "ownership"),),
            zone_name="ornek.com",
            authorization_proven=False,
        )
    assert transport.calls == []
