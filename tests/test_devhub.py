import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
import devhub

class Tests(unittest.TestCase):
    def test_default_denial(self):
        self.assertEqual(devhub.plan([{'name':'qwen:7b'}], [])['status'], 'blocked')
    def test_local(self):
        self.assertEqual(devhub.plan([{'name':'qwen:7b'}], ['qwen:7b'])['model'], 'qwen:7b')
    def test_cloud_tag(self):
        self.assertEqual(devhub.plan([{'name':'x:cloud'}], ['x:cloud'])['status'], 'blocked')
    def test_cloud_providers(self):
        for p in [*devhub.CLI,*devhub.CLOUD,'litellm']:
            self.assertEqual(devhub.plan([], [], p)['status'], 'blocked')
    def test_advanced(self):
        self.assertEqual(devhub.plan([{'name':'qwen:7b'}], ['qwen:7b'], complexity='advanced')['status'], 'review')
    def test_credentials_in_url(self):
        with self.assertRaises(devhub.Blocked): devhub.HTTP('http://user:pass@localhost')
    def test_no_redirect(self):
        with self.assertRaises(devhub.Blocked): devhub.NoRedirect().redirect_request()
    def test_pull_cloud(self):
        with self.assertRaises(devhub.Blocked): devhub.Ollama('http://localhost').pull('x:cloud')
    def test_state(self):
        with tempfile.TemporaryDirectory() as d:
            s=devhub.State(Path(d)); s.save('test', {'ok':True}); s.event('plan','ready')
            self.assertEqual(s.catalog()['test'], {'ok':True}); self.assertEqual(s.costs()['events']['plan:ready'],1); s.db.close()
    def test_run_without_trust(self):
        with tempfile.TemporaryDirectory() as d, patch.object(devhub.Ollama,'inventory',return_value=[{'name':'qwen:7b'}]), patch.object(devhub.Ollama,'generate') as gen:
            self.assertEqual(devhub.main(['--state',d,'--approve-local','qwen:7b','run','test']),2); gen.assert_not_called()
    def test_run_with_trust(self):
        with tempfile.TemporaryDirectory() as d, patch.object(devhub.Ollama,'inventory',return_value=[{'name':'qwen:7b'}]), patch.object(devhub.Ollama,'generate',return_value='ok') as gen:
            self.assertEqual(devhub.main(['--state',d,'--approve-local','qwen:7b','run','test','--trust-local-endpoint']),0); gen.assert_called_once_with('qwen:7b','test')
    def test_plan_no_inference(self):
        with tempfile.TemporaryDirectory() as d, patch.object(devhub.Ollama,'inventory',return_value=[{'name':'qwen:7b'}]), patch.object(devhub.Ollama,'generate') as gen:
            self.assertEqual(devhub.main(['--state',d,'--approve-local','qwen:7b','plan','test']),0); gen.assert_not_called()
    def test_pull_confirmation(self):
        with tempfile.TemporaryDirectory() as d, patch.object(devhub.Ollama,'pull') as pull:
            self.assertEqual(devhub.main(['--state',d,'pull','qwen:7b']),2); pull.assert_not_called()

if __name__ == '__main__': unittest.main()
