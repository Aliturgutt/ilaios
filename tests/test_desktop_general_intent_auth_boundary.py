"""Desktop general-intent HTTP session and tenant-boundary regression."""
from types import SimpleNamespace
import pytest
import requests
from services.desktop_oidc import DesktopIdentityError
from tests.test_desktop_factory_selection_http import _server

URL_HEADERS = {'Authorization': 'Bearer transport-secret', 'X-ILAIOS-Session': 'valid'}

@pytest.mark.parametrize('headers,expected', [
    ({'Authorization': 'Bearer wrong', 'X-ILAIOS-Session': 'valid'}, 401),
    ({'Authorization': 'Bearer transport-secret'}, 401),
    ({'Authorization': 'Bearer transport-secret', 'X-ILAIOS-Session': ''}, 401),
])
def test_no_general_task_for_missing_transport_or_session(headers, expected):
    with _server() as (url, identity, coordinator, start):
        response = requests.post(url, json={'objective': 'general task'}, headers=headers, timeout=3)
        assert response.status_code == expected
        coordinator.prepare.assert_not_called()
        start.assert_not_called()


def test_expired_or_revoked_session_never_reaches_coordinator():
    with _server() as (url, identity, coordinator, start):
        identity.validate_session.side_effect = DesktopIdentityError('expired or revoked')
        response = requests.post(url, json={'objective': 'general task'}, headers=URL_HEADERS, timeout=3)
        assert response.status_code == 401
        coordinator.prepare.assert_not_called()
        start.assert_not_called()


@pytest.mark.parametrize('actual_tenant,spoofed_tenant', [
    ('tenant-a', 'tenant-b'), ('tenant-b', 'tenant-a'),
])
def test_general_intent_uses_authenticated_tenant_not_client_tenant(actual_tenant, spoofed_tenant):
    with _server() as (url, identity, coordinator, start):
        identity.validate_session.return_value = SimpleNamespace(principal_id='session-user', tenant_id=actual_tenant)
        response = requests.post(url, json={'objective': 'general task',
            'tenant_id': spoofed_tenant, 'principal_id': 'spoofed-user'}, headers=URL_HEADERS, timeout=3)
        assert response.status_code == 201, response.text
        identity.validate_session.assert_called_once_with('valid')
        coordinator.prepare.assert_called_once()
        args, kwargs = coordinator.prepare.call_args
        assert kwargs['tenant_id'] == actual_tenant
        assert kwargs['principal_id'] == 'session-user'
        assert spoofed_tenant not in kwargs.values()
        start.assert_not_called()


def test_general_intent_without_agent_fields_still_admitted_to_coordinator():
    with _server() as (url, identity, coordinator, start):
        response = requests.post(url, json={'objective': 'general task'}, headers=URL_HEADERS, timeout=3)
        assert response.status_code == 201
        coordinator.prepare.assert_called_once()
        start.assert_not_called()
