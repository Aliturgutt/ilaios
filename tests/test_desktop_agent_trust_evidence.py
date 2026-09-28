from dataclasses import replace
from datetime import datetime, timedelta, timezone
import pytest
from services.desktop_agent_trust_evidence import (
    LiveEvidence, AgentAdapterEvidence, validate_live, validate_adapter,
)

NOW = datetime(2026, 9, 28, tzinfo=timezone.utc)
TRUSTED = frozenset({'desktop-trusted-provider'})
LIVE = LiveEvidence('agent-a', 'desktop-trusted-provider', NOW,
                    NOW + timedelta(seconds=30), 'idle', True)
ADAPTER = AgentAdapterEvidence('agent-a', 'adapter-a', 'desktop-trusted-provider',
                                NOW, NOW + timedelta(minutes=5), True, True)

def live(e, agent='agent-a'):
    return validate_live(e, agent_id=agent, now=NOW, trusted_producers=TRUSTED)

def adapter(e, agent='agent-a'):
    return validate_adapter(e, agent_id=agent, adapter_id='adapter-a',
                            now=NOW, trusted_producers=TRUSTED)

def test_complete_trusted_evidence():
    assert live(LIVE) and adapter(ADAPTER)

@pytest.mark.parametrize('e', [None, replace(LIVE, agent_id='agent-b'),
    replace(LIVE, producer_id='unknown'), replace(LIVE, authenticated=False),
    replace(LIVE, status='offline'), replace(LIVE, status='busy'),
    replace(LIVE, observed_at=NOW - timedelta(seconds=31)),
    replace(LIVE, expires_at=NOW - timedelta(seconds=1)),
    replace(LIVE, observed_at=NOW + timedelta(seconds=1)),
    replace(LIVE, observed_at=datetime(2026, 9, 28)),
    replace(LIVE, expires_at=NOW),
])
def test_untrusted_or_stale_live_rejected(e):
    assert not live(e)

@pytest.mark.parametrize('e', [None, replace(ADAPTER, agent_id='agent-b'),
    replace(ADAPTER, adapter_id='adapter-b'),
    replace(ADAPTER, producer_id='unknown'),
    replace(ADAPTER, verified=False), replace(ADAPTER, agent_bound=False),
    replace(ADAPTER, verified_at=NOW - timedelta(minutes=6)),
    replace(ADAPTER, expires_at=NOW - timedelta(seconds=1)),
    replace(ADAPTER, verified_at=NOW + timedelta(seconds=1)),
    replace(ADAPTER, verified_at=datetime(2026, 9, 28)),
    replace(ADAPTER, expires_at=NOW),
])
def test_untrusted_or_stale_adapter_rejected(e):
    assert not adapter(e)

def test_empty_trust_list_rejects_both():
    assert not validate_live(LIVE, agent_id='agent-a', now=NOW,
                             trusted_producers=frozenset())
    assert not validate_adapter(ADAPTER, agent_id='agent-a', adapter_id='adapter-a',
                                now=NOW, trusted_producers=frozenset())
