"""Mutual TLS worker identity policy — no listener, client, or remote execution.

A future transport MUST establish a validated mTLS handshake with the contexts
below before calling verify_worker_peer. A registered metadata snapshot alone
never grants access. Certificates/keys are provisioned outside DevHub.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import stat
import ssl
from pathlib import Path

from worker_registry import valid_id

PIN = re.compile(r'^[a-f0-9]{64}$')
WORKER_DOMAIN = 'worker.devhub.internal'


class WorkerTLSError(Exception):
    pass


def _require_file(path, name):
    """Refuse ambiguous/relative paths or symlinks in sensitive TLS configuration."""
    if not isinstance(path, (str, Path)):
        raise WorkerTLSError(f'{name}: invalid file path')
    file = Path(path)
    if not file.is_absolute() or file.is_symlink() or not file.is_file():
        raise WorkerTLSError(f'{name}: must be an existing absolute regular file')
    if name == 'key_file' and (stat.S_IMODE(file.stat().st_mode) & 0o077):
        raise WorkerTLSError('key_file: private key permissions must be 0600 or stricter')
    return str(file)


def server_tls_context(ca_file, cert_file, key_file):
    """Future worker listener: require a CA-validated client certificate."""
    ca = _require_file(ca_file, 'ca_file')
    cert = _require_file(cert_file, 'cert_file')
    key = _require_file(key_file, 'key_file')
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_3
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.load_verify_locations(cafile=ca)
    ctx.load_cert_chain(certfile=cert, keyfile=key)
    return ctx


def client_tls_context(ca_file, cert_file, key_file):
    """Future core connector: verify server hostname and present client cert."""
    ca = _require_file(ca_file, 'ca_file')
    cert = _require_file(cert_file, 'cert_file')
    key = _require_file(key_file, 'key_file')
    ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=ca)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_3
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.check_hostname = True
    ctx.load_cert_chain(certfile=cert, keyfile=key)
    return ctx


def verify_worker_identity(certificate, der, worker_id, allowlist):
    """Post-handshake policy: validate a worker's DNS SAN and pinned DER hash.

    This does NOT perform a TLS handshake or verify the certificate chain by
    itself. The caller must already have authenticated the peer using mTLS.
    """
    if not valid_id(worker_id):
        raise WorkerTLSError('Invalid worker ID')
    if not isinstance(allowlist, dict) or worker_id not in allowlist:
        raise WorkerTLSError('Worker not explicitly approved')
    pin = allowlist[worker_id]
    if not isinstance(pin, str) or not PIN.fullmatch(pin):
        raise WorkerTLSError('Unusable worker certificate fingerprint')
    if not isinstance(der, bytes) or not der:
        raise WorkerTLSError('Peer certificate missing')
    if not isinstance(certificate, dict):
        raise WorkerTLSError('Peer certificate details missing')

    expected_san = worker_id + '.' + WORKER_DOMAIN
    sans = certificate.get('subjectAltName')
    if not isinstance(sans, (tuple, list)):
        raise WorkerTLSError('Peer DNS SAN missing')
    if ('DNS', expected_san) not in sans:
        raise WorkerTLSError('Certificate DNS SAN does not match approved worker')
    digest = hashlib.sha256(der).hexdigest()
    if not hmac.compare_digest(digest, pin):
        raise WorkerTLSError('Worker certificate fingerprint mismatch')
    return {'worker_id': worker_id, 'identity': 'mtls_san_and_pinned_cert',
            'fingerprint_sha256': digest, 'scope': 'inventory_read_only',
            'remote_execution': False}


def verify_worker_peer(tls_socket, worker_id, allowlist):
    """Only call with a socket from server_tls_context after a successful handshake."""
    if tls_socket.version() != 'TLSv1.3':
        raise WorkerTLSError('TLS 1.3 required')
    certificate = tls_socket.getpeercert(binary_form=False)
    der = tls_socket.getpeercert(binary_form=True)
    return verify_worker_identity(certificate, der, worker_id, allowlist)


def authorized_action(identity, action):
    """Inventory-only in this preview; all control-plane actions fail closed."""
    if not isinstance(identity, dict) or identity.get('identity') != 'mtls_san_and_pinned_cert':
        return False
    if identity.get('scope') != 'inventory_read_only' or identity.get('remote_execution') is not False:
        return False
    return action in ('inventory.read', 'health.read')
