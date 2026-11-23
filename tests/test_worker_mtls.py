import hashlib
import ssl
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import worker_mtls as auth


class MTLSWorkerPolicyTests(unittest.TestCase):
    def setUp(self):
        self.worker = 'ia-01'
        self.der = b'dummy-DER-for-policy-test'
        self.pin = hashlib.sha256(self.der).hexdigest()
        self.cert = {'subjectAltName': (('DNS', 'ia-01.worker.devhub.internal'),)}

    def test_valid_pinned_identity_only_allows_inventory(self):
        result = auth.verify_worker_identity(self.cert, self.der, self.worker, {'ia-01':self.pin})
        self.assertEqual(result['scope'], 'inventory_read_only')
        self.assertIs(result['remote_execution'], False)
        self.assertTrue(auth.authorized_action(result, 'inventory.read'))
        self.assertTrue(auth.authorized_action(result, 'health.read'))
        for action in ('models.pull','models.delete','inference.run','system.exec','jobs.submit', ''):
            self.assertFalse(auth.authorized_action(result, action))

    def test_string_disabled_is_not_a_boolean_permission(self):
        """Untrusted metadata string must not bypass strict boolean authorization."""
        identity = auth.verify_worker_identity(self.cert, self.der, self.worker, {'ia-01':self.pin})
        self.assertIs(identity['remote_execution'], False)
        self.assertFalse(auth.authorized_action({**identity, 'remote_execution': 'disabled'}, 'inventory.read'))
        self.assertFalse(auth.authorized_action({**identity, 'remote_execution': 0}, 'health.read'))
        self.assertFalse(auth.authorized_action({**identity, 'remote_execution': True}, 'inventory.read'))

    def test_unknown_id_rejected(self):
        with self.assertRaises(auth.WorkerTLSError):
            auth.verify_worker_identity(self.cert, self.der, 'ia-02', {'ia-01': self.pin})

    def test_bad_worker_id_rejected(self):
        with self.assertRaises(auth.WorkerTLSError):
            auth.verify_worker_identity(self.cert, self.der, '../ia-01', {'ia-01': self.pin})

    def test_invalid_fingerprint_rejected(self):
        for pin in ('0'*63, 'G'*64, '0'*65, '', None):
            with self.assertRaises(auth.WorkerTLSError):
                auth.verify_worker_identity(self.cert, self.der, self.worker, {'ia-01': pin})

    def test_wrong_certificate_rejected(self):
        with self.assertRaises(auth.WorkerTLSError):
            auth.verify_worker_identity(self.cert, b'other-cert', self.worker, {'ia-01': self.pin})

    def test_missing_san_rejected(self):
        for cert in ({}, {'subjectAltName':(('DNS','wrong.worker.devhub.internal'),)},
                     {'subject':((('commonName','ia-01.worker.devhub.internal'),),)}):
            with self.assertRaises(auth.WorkerTLSError):
                auth.verify_worker_identity(cert, self.der, self.worker, {'ia-01': self.pin})

    def test_missing_peer_certificate_rejected(self):
        with self.assertRaises(auth.WorkerTLSError):
            auth.verify_worker_identity(self.cert, None, self.worker, {'ia-01': self.pin})

    def test_peer_tls_version_rejected(self):
        conn = MagicMock()
        conn.version.return_value = 'TLSv1.2'
        with self.assertRaises(auth.WorkerTLSError):
            auth.verify_worker_peer(conn, self.worker, {'ia-01': self.pin})
        conn.getpeercert.assert_not_called()

    def test_post_handshake_peer(self):
        conn = MagicMock()
        conn.version.return_value = 'TLSv1.3'
        conn.getpeercert.side_effect = lambda binary_form=False: self.der if binary_form else self.cert
        out = auth.verify_worker_peer(conn,self.worker,{'ia-01':self.pin})
        self.assertEqual(out['worker_id'],'ia-01')
        self.assertFalse(out['remote_execution'])

    def test_no_authz_for_untrusted_metadata_record(self):
        snapshot = {'trust':'metadata_only_unverified','remote_execution':'disabled'}
        self.assertFalse(auth.authorized_action(snapshot,'inventory.read'))

    def test_tls_contexts_force_tls13_and_cert_required(self):
        with tempfile.TemporaryDirectory() as td:
            paths=[Path(td)/n for n in ('ca.pem','cert.pem','key.pem')]
            for p in paths: p.write_text('test placeholder')
            paths[2].chmod(0o600)
            with patch('worker_mtls.ssl.SSLContext') as constructor:
                ctx=constructor.return_value
                ctx.minimum_version=None
                ctx.verify_mode=None
                auth.server_tls_context(*paths)
                constructor.assert_called_once_with(ssl.PROTOCOL_TLS_SERVER)
                self.assertEqual(ctx.minimum_version,ssl.TLSVersion.TLSv1_3)
                self.assertEqual(ctx.verify_mode,ssl.CERT_REQUIRED)
                ctx.load_verify_locations.assert_called_once_with(cafile=str(paths[0]))
                ctx.load_cert_chain.assert_called_once_with(certfile=str(paths[1]),keyfile=str(paths[2]))

    def test_tls_client_verifies_server_identity(self):
        with tempfile.TemporaryDirectory() as td:
            paths=[Path(td)/n for n in ('ca.pem','cert.pem','key.pem')]
            for p in paths: p.write_text('test placeholder')
            paths[2].chmod(0o600)
            with patch('worker_mtls.ssl.create_default_context') as factory:
                ctx=factory.return_value
                auth.client_tls_context(*paths)
                factory.assert_called_once_with(ssl.Purpose.SERVER_AUTH,cafile=str(paths[0]))
                self.assertEqual(ctx.minimum_version,ssl.TLSVersion.TLSv1_3)
                self.assertEqual(ctx.verify_mode,ssl.CERT_REQUIRED)
                self.assertTrue(ctx.check_hostname)

    def test_insecure_private_key_mode_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            paths=[Path(td)/n for n in ('ca.pem','cert.pem','key.pem')]
            for p in paths: p.write_text('test placeholder')
            paths[2].chmod(0o644)
            with self.assertRaises(auth.WorkerTLSError):
                auth.client_tls_context(*paths)

    def test_relative_and_symlink_paths_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'regular.pem'
            p.write_text('placeholder')
            symlink=Path(td)/'link.pem';symlink.symlink_to(p)
            for invalid in ('ca.pem', str(symlink), str(Path(td)/'not-existent')):
                with self.assertRaises(auth.WorkerTLSError):
                    auth.client_tls_context(invalid,p,p)


if __name__ == '__main__':
    unittest.main()
