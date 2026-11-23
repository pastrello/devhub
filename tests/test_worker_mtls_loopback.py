"""Real TLS 1.3/mTLS loopback tests with ephemeral OpenSSL test identities.

No persistent daemon, external ports or Ollama access. Disposable certificates
and keys are created in a temporary directory and removed after the suite.
"""
import hashlib
import shutil
import socket
import ssl
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from queue import Queue

import worker_mtls as mtls

SERVER_DNS = 'core.worker.devhub.internal'
WORKER_DNS = 'ia-01.worker.devhub.internal'


def run_openssl(*args):
    subprocess.run(['openssl', *map(str, args)], check=True, timeout=10,
                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def issue_ca(root, prefix):
    key, crt = root / (prefix + '.key'), root / (prefix + '.crt')
    run_openssl('ecparam', '-name', 'prime256v1', '-genkey', '-noout', '-out', key)
    key.chmod(0o600)
    run_openssl('req', '-new', '-x509', '-sha256', '-days', '1', '-key', key,
                '-subj', '/CN=DevHub Ephemeral Test CA ' + prefix, '-out', crt,
                '-addext', 'basicConstraints=critical,CA:TRUE',
                '-addext', 'keyUsage=critical,keyCertSign,cRLSign')
    return key, crt


def issue_cert(root, prefix, ca, *, dns, usage):
    key, csr, crt, ext = [root / (prefix + x) for x in ('.key', '.csr', '.crt', '.ext')]
    run_openssl('ecparam', '-name', 'prime256v1', '-genkey', '-noout', '-out', key)
    key.chmod(0o600)
    run_openssl('req', '-new', '-sha256', '-key', key, '-subj', '/CN=' + dns, '-out', csr)
    ext.write_text('basicConstraints=critical,CA:FALSE\n'
                   'keyUsage=critical,digitalSignature\n'
                   'extendedKeyUsage=' + usage + '\n'
                   'subjectAltName=DNS:' + dns + '\n', encoding='ascii')
    run_openssl('x509', '-req', '-sha256', '-days', '1', '-in', csr,
                '-CA', ca[1], '-CAkey', ca[0], '-CAcreateserial',
                '-extfile', ext, '-out', crt)
    return key, crt


class LiveWorkerMTLSTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('openssl'):
            raise unittest.SkipTest('OpenSSL CLI unavailable: real TLS integration tests skipped')
        cls.temporary = tempfile.TemporaryDirectory(prefix='devhub-mtls-loopback-')
        cls.root = Path(cls.temporary.name)
        cls.ca = issue_ca(cls.root, 'lab-ca')
        cls.other_ca = issue_ca(cls.root, 'other-ca')
        cls.server = issue_cert(cls.root, 'core-server', cls.ca, dns=SERVER_DNS, usage='serverAuth')
        cls.worker = issue_cert(cls.root, 'worker-good', cls.ca, dns=WORKER_DNS, usage='clientAuth')
        cls.wrong_san = issue_cert(cls.root, 'worker-other', cls.ca,
                                   dns='ia-02.worker.devhub.internal', usage='clientAuth')
        cls.unknown_ca_worker = issue_cert(cls.root, 'worker-untrusted', cls.other_ca,
                                            dns=WORKER_DNS, usage='clientAuth')
        der = ssl.PEM_cert_to_DER_cert(cls.worker[1].read_text('ascii'))
        cls.correct_pin = hashlib.sha256(der).hexdigest()

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'temporary'):
            cls.temporary.cleanup()

    def exchange(self, *, worker_cert=None, server_hostname=SERVER_DNS, pin=None,
                 client_ca=None, force_tls12=False):
        server_ctx = mtls.server_tls_context(self.ca[1], self.server[1], self.server[0])
        if worker_cert is False:
            client_ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH,
                                                    cafile=str(client_ca or self.ca[1]))
            client_ctx.minimum_version = ssl.TLSVersion.TLSv1_3
        else:
            key, cert = worker_cert if worker_cert is not None else self.worker
            client_ctx = mtls.client_tls_context(client_ca or self.ca[1], cert, key)
        if force_tls12:
            client_ctx.minimum_version = ssl.TLSVersion.TLSv1_2
            client_ctx.maximum_version = ssl.TLSVersion.TLSv1_2
        expected_pin = pin if pin is not None else self.correct_pin
        events = Queue(maxsize=1)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.settimeout(5)
            listener.bind(('127.0.0.1', 0))
            listener.listen(1)
            port = listener.getsockname()[1]

            def serve():
                try:
                    conn, _ = listener.accept()
                    conn.settimeout(5)
                    with conn, server_ctx.wrap_socket(conn, server_side=True) as tls:
                        identity = mtls.verify_worker_peer(tls, 'ia-01', {'ia-01': expected_pin})
                        if not mtls.authorized_action(identity, 'inventory.read'):
                            raise mtls.WorkerTLSError('Read-only inventory not authorized')
                        if mtls.authorized_action(identity, 'models.pull'):
                            raise mtls.WorkerTLSError('Unexpected mutation authorization')
                        tls.sendall(b'OK')
                        events.put(('accepted', tls.version()))
                except (OSError, ssl.SSLError, mtls.WorkerTLSError) as exc:
                    events.put(('rejected', type(exc).__name__))

            thread = threading.Thread(target=serve, name='devhub-test-loopback', daemon=True)
            thread.start()
            try:
                with socket.create_connection(('127.0.0.1', port), timeout=5) as sock:
                    with client_ctx.wrap_socket(sock, server_hostname=server_hostname) as tls:
                        tls.settimeout(5)
                        received = tls.recv(16)
            except (OSError, ssl.SSLError):
                received = b''
            thread.join(timeout=7)
            self.assertFalse(thread.is_alive(), 'Loopback server did not shut down')
            self.assertEqual(events.qsize(), 1)
            verdict, detail = events.get_nowait()
            return {'server': verdict, 'detail': detail, 'received': received}

    def test_real_mutual_tls_13_success_and_no_execution(self):
        out = self.exchange()
        self.assertEqual(out, {'server': 'accepted', 'detail': 'TLSv1.3', 'received': b'OK'})

    def test_missing_client_certificate_rejected(self):
        out = self.exchange(worker_cert=False)
        self.assertEqual(out['server'], 'rejected')
        self.assertEqual(out['received'], b'')

    def test_wrong_worker_san_rejected(self):
        out = self.exchange(worker_cert=self.wrong_san)
        self.assertEqual(out['server'], 'rejected')
        self.assertEqual(out['detail'], 'WorkerTLSError')
        self.assertEqual(out['received'], b'')

    def test_unknown_ca_worker_rejected_in_handshake(self):
        out = self.exchange(worker_cert=self.unknown_ca_worker)
        self.assertEqual(out['server'], 'rejected')
        self.assertEqual(out['received'], b'')

    def test_unapproved_pinned_worker_rejected(self):
        out = self.exchange(pin='f' * 64)
        self.assertEqual(out['server'], 'rejected')
        self.assertEqual(out['detail'], 'WorkerTLSError')
        self.assertEqual(out['received'], b'')

    def test_client_rejects_unexpected_server_name(self):
        out = self.exchange(server_hostname='unexpected.worker.devhub.internal')
        self.assertEqual(out['server'], 'rejected')
        self.assertEqual(out['received'], b'')

    def test_tls12_only_client_rejected(self):
        out = self.exchange(force_tls12=True)
        self.assertEqual(out['server'], 'rejected')
        self.assertEqual(out['received'], b'')

    def test_client_rejects_untrusted_server_ca(self):
        out = self.exchange(client_ca=self.other_ca[1])
        self.assertEqual(out['server'], 'rejected')
        self.assertEqual(out['received'], b'')


if __name__ == '__main__':
    unittest.main()
