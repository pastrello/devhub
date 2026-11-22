import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import devhub
import engine_manager as em

class TestEngineManager(unittest.TestCase):
    def test_local_tag(self):
        self.assertTrue(em.valid_local_tag('qwen3:4b'))
        self.assertFalse(em.valid_local_tag('qwen3:cloud'))
        self.assertFalse(em.valid_local_tag('someone/qwen:4b'))
        self.assertFalse(em.valid_local_tag('http://example.org'))
    def test_search(self):
        results=em.search_models('coder', task='coding', vram_mib=8192, installed=['qwen2.5-coder:7b'])
        self.assertEqual(len(results),2)
        self.assertTrue(next(m for m in results if m['tag']=='qwen2.5-coder:7b')['installed'])
        self.assertEqual(results[0]['weights_vs_vram'],'weights_below_vram_not_guaranteed')
    def test_gpu_absent(self):
        with patch('engine_manager.shutil.which', return_value=None):
            self.assertEqual(em.gpu_inventory()['status'],'unavailable')
    def test_gpu_parsing(self):
        class R: stdout='0, NVIDIA GeForce RTX 3060 Ti, 8192, 4985, 620.73.04\n'
        with patch('engine_manager.shutil.which', return_value='/usr/bin/nvidia-smi'), patch('engine_manager.subprocess.run',return_value=R()):
            self.assertEqual(em.gpu_inventory()['gpus'][0]['memory_total_mib'],8192)
    def test_engines_catalog(self):
        out=em.engines_catalog()
        self.assertEqual(next(x for x in out if x['id']=='ollama')['availability'],'supported')
    def test_insufficient_disk(self):
        class R: free=100_000_000
        with tempfile.TemporaryDirectory() as d, patch('engine_manager.shutil.disk_usage', return_value=R()):
            self.assertEqual(em.estimated_download_check('qwen3:4b',d)['space'],'insufficient_estimate')
    def test_models_list_no_generation(self):
        with tempfile.TemporaryDirectory() as d,patch.object(devhub.Ollama,'inventory',return_value=[]),patch.object(devhub.Ollama,'generate') as generate:
            self.assertEqual(devhub.main(['--state',d,'models','search','coding']),0)
            generate.assert_not_called()
    def test_model_pull_both_approvals(self):
        with tempfile.TemporaryDirectory() as d,patch.object(devhub.Ollama,'pull') as pull:
            self.assertEqual(devhub.main(['--state',d,'models','pull','qwen3:4b','--confirm-download']),2)
            pull.assert_not_called()
    def test_model_pull_allowlisted(self):
        with tempfile.TemporaryDirectory() as d,patch.object(devhub.Ollama,'pull',return_value={'status':'success'}) as pull:
            self.assertEqual(devhub.main(['--state',d,'models','pull','qwen3:4b','--confirm-download','--trust-local-endpoint']),0)
            pull.assert_called_once_with('qwen3:4b')
    def test_model_unknown_blocked(self):
        with tempfile.TemporaryDirectory() as d,patch.object(devhub.Ollama,'pull') as pull:
            self.assertEqual(devhub.main(['--state',d,'models','pull','random:100b','--confirm-download','--trust-local-endpoint']),2)
            pull.assert_not_called()
    def test_model_delete_confirmation(self):
        with tempfile.TemporaryDirectory() as d,patch.object(devhub.Ollama,'delete') as delete:
            self.assertEqual(devhub.main(['--state',d,'models','delete','qwen3:4b','--trust-local-endpoint']),2)
            delete.assert_not_called()
    def test_model_delete_exact(self):
        with tempfile.TemporaryDirectory() as d,patch.object(devhub.Ollama,'inventory',return_value=[{'name':'qwen3:4b'}]),patch.object(devhub.Ollama,'delete') as delete:
            self.assertEqual(devhub.main(['--state',d,'models','delete','qwen3:4b','--confirm-delete','--trust-local-endpoint']),0)
            delete.assert_called_once_with('qwen3:4b')
    def test_model_test_requires_trust(self):
        with tempfile.TemporaryDirectory() as d, patch.object(devhub.Ollama,'generate') as gen:
            self.assertEqual(devhub.main(['--state',d,'models','test','qwen3:4b']),2)
            gen.assert_not_called()
    def test_model_test_local(self):
        with tempfile.TemporaryDirectory() as d,patch.object(devhub.Ollama,'inventory',return_value=[{'name':'qwen3:4b'}]),patch.object(devhub.Ollama,'generate',return_value='OK') as gen,patch.object(devhub.Ollama,'running',return_value=[{'name':'qwen3:4b','size_vram':3145728000}]):
            self.assertEqual(devhub.main(['--state',d,'models','test','qwen3:4b','--trust-local-endpoint']),0)
            gen.assert_called_once()
    def test_install_guidance_only(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(devhub.main(['--state',d,'engines','install','ollama']),0)
    def test_api_empty_delete_response(self):
        class R:
            def __enter__(self): return self
            def __exit__(self, *args): return None
            def read(self,n): return b''
        h=devhub.HTTP('http://127.0.0.1:11434')
        with patch.object(h.client,'open',return_value=R()) as call:
            self.assertEqual(h.call('/api/delete',{'model':'qwen3:4b'},method='DELETE'),{})
            self.assertEqual(call.call_args.args[0].get_method(),'DELETE')

if __name__ == '__main__': unittest.main()
