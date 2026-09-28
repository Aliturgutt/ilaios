"""mTLS transport and per-agent certificate pinning for remote delivery."""
import hashlib
import ipaddress
import ssl
from datetime import datetime, timedelta, timezone
from threading import Thread

import pytest
import requests
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from services.desktop_agent_delivery import AgentDelivery
from services.desktop_agent_delivery_http import AgentDeliveryHTTPServer
from services.desktop_agent_assignment_store import record_agent_assignment
from tests.test_execution_coordinator import _coordinator


def certs(tmp_path):
    now = datetime.now(timezone.utc)
    def key(): return rsa.generate_private_key(public_exponent=65537, key_size=2048)
    def name(s): return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, s)])
    ca_key = key()
    ca = (x509.CertificateBuilder().subject_name(name('test-ca'))
        .issuer_name(name('test-ca')).public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(days=1))
        .not_valid_after(now+timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(ca_key, hashes.SHA256()))
    (tmp_path/'ca.pem').write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    result = {}
    for subject in ('server', 'agent'):
        private = key()
        builder = (x509.CertificateBuilder().subject_name(name(subject))
            .issuer_name(ca.subject).public_key(private.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now-timedelta(days=1)).not_valid_after(now+timedelta(days=1))
            .add_extension(x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH if subject=='server'
                else x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH]), critical=False))
        if subject == 'server':
            builder = builder.add_extension(x509.SubjectAlternativeName(
                [x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]), critical=False)
        certificate = builder.sign(ca_key, hashes.SHA256())
        (tmp_path/f'{subject}.pem').write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
        (tmp_path/f'{subject}.key').write_bytes(private.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption()))
        result[subject] = certificate
    return result


def test_tls_client_certificate_and_agent_identity(tmp_path):
    identities = certs(tmp_path)
    coordinator, *_ = _coordinator(tmp_path)
    request = 'agentexec-remote-tls'
    coordinator.prepare(request, 'Create a launch video and final MP4',
        token='token', principal_id='owner', tenant_id='tenant-a',
        now=datetime.now(timezone.utc))
    record_agent_assignment(coordinator._database_path, request_id=request,
        agent_id='agent-a', principal_id='owner', tenant_id='tenant-a')
    delivery = AgentDelivery(coordinator._database_path, {'agent-a':'credential-a'})
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(str(tmp_path/'server.pem'), str(tmp_path/'server.key'))
    ctx.load_verify_locations(cafile=str(tmp_path/'ca.pem'))
    ctx.verify_mode = ssl.CERT_REQUIRED
    pin = hashlib.sha256(identities['agent'].public_bytes(serialization.Encoding.DER)).hexdigest()
    server = AgentDeliveryHTTPServer(('127.0.0.1',0), delivery, tls_context=ctx,
                                      agent_cert_fingerprints={'agent-a':pin})
    thread = Thread(target=server.serve_forever, daemon=True); thread.start()
    url = f'https://127.0.0.1:{server.server_address[1]}/v1/agents/delivery/claim'
    payload = {'request_id':request,'agent_id':'agent-a'}
    headers = {'Authorization':'Bearer credential-a'}
    try:
        with pytest.raises(requests.exceptions.RequestException):
            requests.post(url, json=payload, headers=headers,
                verify=str(tmp_path/'ca.pem'), timeout=3)
        wrong = requests.post(url, json={**payload, 'agent_id':'other-agent'},
            headers=headers, verify=str(tmp_path/'ca.pem'),
            cert=(str(tmp_path/'agent.pem'),str(tmp_path/'agent.key')), timeout=3)
        assert wrong.status_code == 403
        correct = requests.post(url, json=payload, headers=headers,
            verify=str(tmp_path/'ca.pem'),
            cert=(str(tmp_path/'agent.pem'),str(tmp_path/'agent.key')), timeout=3)
        assert correct.status_code == 200 and correct.json()['lease']
    finally:
        server.shutdown(); thread.join(timeout=3); server.server_close()
