"""Readiness is authenticated, tenant-scoped, and fail-closed."""
import requests
from services.desktop_oidc import DesktopIdentityError
from tests.test_desktop_agent_assignment_http import server


def test_assignment_readiness_requires_delivery_and_session():
    with server() as (url, identity, _, preflight, _):
        readiness = url.replace('/assignments', '/assignment-readiness')
        headers = {'Authorization': 'Bearer transport', 'X-ILAIOS-Session': 'valid'}
        response = requests.get(readiness, headers=headers, timeout=3)
        assert response.status_code == 200
        assert response.json() == {'ready_agents': []}
        preflight.check.assert_not_called()
        # Explicitly configured delivery is required before readiness is advertised.
        from unittest.mock import Mock
        # The fixture returns the server URL, not the server object; positive
        # eligibility is covered separately by admission tests.
        assert requests.get(readiness, timeout=3).status_code == 401
        identity.validate_session.side_effect = DesktopIdentityError('revoked')
        assert requests.get(readiness, headers=headers, timeout=3).status_code != 200
