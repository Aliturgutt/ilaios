"""Trusted evidence integration must fail closed without server-owned providers."""
from datetime import datetime, timezone
from unittest.mock import Mock
from services.desktop_agent_evidence_provider import server_agent_evidence

NOW = datetime(2026, 9, 28, tzinfo=timezone.utc)


def test_missing_provider_never_creates_trusted_evidence():
    snapshot = server_agent_evidence(agent_id='agent-a', adapter_id='adapter-a', now=NOW)
    assert snapshot.live is None and snapshot.adapter is None
    assert not snapshot.trusted_producers


def test_unapproved_provider_is_never_invoked():
    provider = Mock(producer_id='unknown')
    snapshot = server_agent_evidence(agent_id='agent-a', adapter_id='adapter-a',
        now=NOW, provider=provider, approved_producers=frozenset({'approved'}))
    provider.live.assert_not_called()
    provider.adapter.assert_not_called()
    assert not snapshot.trusted_producers


def test_approved_provider_receives_server_selected_identity_only():
    provider = Mock(producer_id='approved')
    snapshot = server_agent_evidence(agent_id='agent-a', adapter_id='adapter-a',
        now=NOW, provider=provider, approved_producers=frozenset({'approved'}))
    provider.live.assert_called_once_with(agent_id='agent-a', now=NOW)
    provider.adapter.assert_called_once_with(agent_id='agent-a', adapter_id='adapter-a', now=NOW)
    assert snapshot.trusted_producers == frozenset({'approved'})
