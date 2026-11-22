import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
import devhub
import ollama_registry as rg

def manifest(tag='qwen3:4b'):
    return rg.parse_manifest(tag, {
        'layers': [
            {'mediaType': 'application/vnd.ollama.image.model',
             'digest': 'sha256:' + 'a' * 64, 'size': 3_000_000_000},
            {'mediaType': 'application/vnd.ollama.image.license',
             'digest': 'sha256:' + 'b' * 64, 'size': 500}
        ]
    })

def save_preflight(state_dir, tag='qwen3:4b', sha=None, endpoint='http://127.0.0.1:11434'):
    state = devhub.State(Path(state_dir))
    m = manifest(tag)
    if sha:
        m['manifest_sha256'] = sha
    state.save('pull-plan:' + tag, {
        'status': 'ready_for_review', 'model': tag, 'manifest': m,
        'ollama_endpoint': endpoint,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'disk': {'path': '/tmp', 'enough_by_estimate': True}
    })
    state.db.close()

class RegistryTests(unittest.TestCase):
    def test_safe_registry_url(self):
        self.assertEqual(rg.manifest_url('qwen3:4b'),
                         'https://registry.ollama.ai/v2/library/qwen3/manifests/4b')
        for tag in ('foo', 'owner/foo:4b', 'x:cloud', 'http://bad/x:4b', '../x:7b'):
            with self.assertRaises(rg.RegistryError):
                rg.manifest_url(tag)

    def test_manifest_validation(self):
        m = manifest()
        self.assertEqual(m['weight_bytes'], 3_000_000_000)
        self.assertEqual(m['license'], 'not_verified')
        for layers in ([], [{'mediaType': 'application/vnd.ollama.image.model', 'digest': 'oops', 'size': 1000}]):
            with self.assertRaises(rg.RegistryError):
                rg.parse_manifest('qwen3:4b', {'layers': layers})

    def test_manifest_list_fails_closed(self):
        with self.assertRaises(rg.RegistryError):
            rg.parse_manifest('qwen3:4b', {'manifests':[{'runner':'mlx'}]})

    def test_manifest_change(self):
        m = manifest()
        altered = dict(m, manifest_sha256='0'*64)
        self.assertFalse(rg.same_manifest(m, altered))

    def test_missing_storage(self):
        with self.assertRaises(rg.RegistryError):
            rg.storage_probe('/not-a-real-directory-173652', 4000)

    def test_preflight_no_download(self):
        with tempfile.TemporaryDirectory() as d, patch('ollama_registry.fetch_manifest',return_value=manifest()), patch('ollama_registry.storage_probe',return_value={'path':'/tmp','enough_by_estimate':True}) as disk, patch.object(devhub.Ollama,'pull') as pull:
            self.assertEqual(devhub.main(['--state',d,'models','preflight','qwen3:4b','--storage-path','/tmp']),0)
            self.assertIsNotNone(devhub.State(Path(d)).snapshot('pull-plan:qwen3:4b'))
            pull.assert_not_called()

    def test_approval_gate(self):
        with tempfile.TemporaryDirectory() as d, patch.object(devhub.Ollama,'pull') as pull:
            save_preflight(d)
            for flags in ([], ['--confirm-download'], ['--confirm-download','--trust-local-endpoint']):
                self.assertEqual(devhub.main(['--state',d,'models','install','qwen3:4b',*flags]), 2)
            pull.assert_not_called()

    def test_preflight_required(self):
        with tempfile.TemporaryDirectory() as d, patch.object(devhub.Ollama,'pull') as pull:
            self.assertEqual(devhub.main(['--state',d,'models','install','qwen3:4b','--confirm-download','--trust-local-endpoint','--license-reviewed']),2)
            pull.assert_not_called()

    def test_remote_install_refused(self):
        with tempfile.TemporaryDirectory() as d, patch.object(devhub.Ollama,'pull') as pull:
            save_preflight(d, endpoint='http://10.0.0.8:11434')
            args=['--state',d,'--ollama','http://10.0.0.8:11434','models','install','qwen3:4b','--confirm-download','--trust-local-endpoint','--license-reviewed']
            self.assertEqual(devhub.main(args),2)
            pull.assert_not_called()

    def test_change_refused(self):
        with tempfile.TemporaryDirectory() as d, patch('ollama_registry.fetch_manifest',return_value=manifest()), patch.object(devhub.Ollama,'pull') as pull:
            save_preflight(d,sha='f'*64)
            self.assertEqual(devhub.main(['--state',d,'models','install','qwen3:4b','--confirm-download','--trust-local-endpoint','--license-reviewed']),2)
            pull.assert_not_called()

    def test_disk_space_refused(self):
        with tempfile.TemporaryDirectory() as d, patch('ollama_registry.fetch_manifest',return_value=manifest()), patch('ollama_registry.storage_probe',return_value={'enough_by_estimate':False}), patch.object(devhub.Ollama,'pull') as pull:
            save_preflight(d)
            self.assertEqual(devhub.main(['--state',d,'models','install','qwen3:4b','--confirm-download','--trust-local-endpoint','--license-reviewed']),2)
            pull.assert_not_called()

    def test_download_approved(self):
        with tempfile.TemporaryDirectory() as d, patch('ollama_registry.fetch_manifest',return_value=manifest()), patch('ollama_registry.storage_probe',return_value={'enough_by_estimate':True}), patch.object(devhub.Ollama,'inventory',return_value=[{'name':'qwen3:4b'}]), patch.object(devhub.Ollama,'pull',return_value={'status':'success'}) as pull:
            save_preflight(d)
            self.assertEqual(devhub.main(['--state',d,'models','install','qwen3:4b','--confirm-download','--trust-local-endpoint','--license-reviewed']),0)
            pull.assert_called_once_with('qwen3:4b')

    def test_download_not_listed(self):
        with tempfile.TemporaryDirectory() as d, patch('ollama_registry.fetch_manifest',return_value=manifest()), patch('ollama_registry.storage_probe',return_value={'enough_by_estimate':True}), patch.object(devhub.Ollama,'inventory',return_value=[]), patch.object(devhub.Ollama,'pull',return_value={'status':'success'}):
            save_preflight(d)
            self.assertEqual(devhub.main(['--state',d,'models','install','qwen3:4b','--confirm-download','--trust-local-endpoint','--license-reviewed']),2)

    def test_expired_plan(self):
        with tempfile.TemporaryDirectory() as d, patch.object(devhub.Ollama,'pull') as pull:
            save_preflight(d)
            s=devhub.State(Path(d)); p=s.snapshot('pull-plan:qwen3:4b')
            p['created_at']=(datetime.now(timezone.utc)-timedelta(hours=3)).isoformat()
            s.save('pull-plan:qwen3:4b',p);s.db.close()
            self.assertEqual(devhub.main(['--state',d,'models','install','qwen3:4b','--confirm-download','--trust-local-endpoint','--license-reviewed']),2)
            pull.assert_not_called()

    def test_layer_bool_size_refused(self):
        with self.assertRaises(rg.RegistryError):
            rg.parse_manifest('qwen3:4b', {'layers':[{'mediaType':rg.WEIGHTS,'digest':'sha256:'+'a'*64,'size':True}]})

if __name__ == '__main__':
    unittest.main()
