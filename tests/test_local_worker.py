import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import devhub
import local_worker as lw


class FakeOllama:
    def inventory(self):
        return [{'name': 'qwen2.5-coder:3b'}]
    def version(self):
        return '0.40.17'
    def running(self):
        return [{'name': 'qwen2.5-coder:3b', 'size': 2350000000,
                 'size_vram': 2163568803, 'expires_at': '2026-11-22T22:58:00Z'}]
    def generate_report(self, model, prompt, *, keep_alive, max_tokens):
        assert model == 'qwen2.5-coder:3b'
        assert keep_alive == '5m'
        assert max_tokens == 64
        return {'response': 'OK', 'done': True, 'total_duration': 3_000_000_000,
                'load_duration': 1_000_000_000, 'prompt_eval_count': 24,
                'prompt_eval_duration': 200_000_000, 'eval_count': 40,
                'eval_duration': 2_000_000_000}

def gpu():
    return {'status':'ok','gpus':[{'name':'NVIDIA GeForce RTX 3060 Ti',
                                   'memory_total_mib':8192,'memory_free_mib':5615}]}


class LocalWorkerTests(unittest.TestCase):
    def test_metrics(self):
        result = lw.benchmark(FakeOllama(), 'qwen2.5-coder:3b', gpu)
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['output_tokens'], 40)
        self.assertEqual(result['generation_tokens_per_second'], 20.0)
        self.assertEqual(result['prompt_tokens_per_second'], 120.0)
        self.assertEqual(result['model_load_seconds'], 1.0)
        self.assertEqual(result['residency']['vram_bytes'], 2163568803)
        self.assertTrue(result['residency']['currently_loaded'])
    def test_metric_absence_is_not_zero(self):
        result = lw.summarise({'response':'OK','done':True}, [], 'qwen:3b', gpu())
        self.assertIsNone(result['generation_tokens_per_second'])
        self.assertFalse(result['residency']['currently_loaded'])
    def test_no_tps_division_by_zero(self):
        self.assertIsNone(lw.tokens_per_second(12,0))
        self.assertIsNone(lw.tokens_per_second(None,100))
    def test_invalid_tag_rejected(self):
        for model in ('Qwen/3b:latest','x:cloud','https://evil:443','qwen','../other:3b'):
            with self.assertRaises(lw.WorkerError):
                lw.benchmark(FakeOllama(),model,gpu)
    def test_keep_alive_constrained(self):
        for setting in ('-1','forever','24h','100m'):
            with self.assertRaises(lw.WorkerError):
                lw.benchmark(FakeOllama(),'qwen2.5-coder:3b',gpu,keep_alive=setting)
    def test_unavailable_model(self):
        with self.assertRaises(lw.WorkerError):
            lw.benchmark(FakeOllama(),'missing:3b',gpu)
    def test_worker_status(self):
        result=lw.local_worker(FakeOllama(),gpu)
        self.assertEqual(result['ollama']['status'],'reachable')
        self.assertEqual(result['remote_enrollment'],'disabled')
        self.assertIn('qwen2.5-coder:3b',result['ollama']['installed'])
    def test_cli_benchmark_denies_without_trust(self):
        with tempfile.TemporaryDirectory() as d, patch('local_worker.benchmark') as bench:
            self.assertEqual(devhub.main(['--state',d,'models','benchmark','qwen2.5-coder:3b']),2)
            bench.assert_not_called()
    def test_cli_benchmark_denies_remote_endpoint(self):
        with tempfile.TemporaryDirectory() as d, patch('local_worker.benchmark') as bench:
            self.assertEqual(devhub.main(['--state',d,'--ollama','http://192.168.0.8:11434',
                'models','benchmark','qwen2.5-coder:3b','--trust-local-endpoint']),2)
            bench.assert_not_called()
    def test_cli_benchmark_stores_telemetry(self):
        with tempfile.TemporaryDirectory() as d, patch('local_worker.benchmark',return_value={'status':'ok','output_tokens':40}) as bench:
            self.assertEqual(devhub.main(['--state',d,'models','benchmark',
                'qwen2.5-coder:3b','--trust-local-endpoint']),0)
            self.assertIsNotNone(devhub.State(Path(d)).snapshot('benchmark:qwen2.5-coder:3b'))
            bench.assert_called_once()
    def test_cli_worker_local_no_remote_registration(self):
        with tempfile.TemporaryDirectory() as d, patch('local_worker.local_worker',
            return_value={'type':'local-only','remote_enrollment':'disabled'}) as local:
            self.assertEqual(devhub.main(['--state',d,'workers','local']),0)
            local.assert_called_once()
    def test_wizard_requires_terminal(self):
        with tempfile.TemporaryDirectory() as d, patch('sys.stdin.isatty',return_value=False):
            self.assertEqual(devhub.main(['--state',d,'wizard']),2)
    def test_wizard_exit_safe(self):
        with tempfile.TemporaryDirectory() as d, patch('sys.stdin.isatty',return_value=True),patch('builtins.input',return_value='0'),patch.object(devhub.Ollama,'pull') as pull:
            self.assertEqual(devhub.main(['--state',d,'wizard']),0)
            pull.assert_not_called()
    def test_wizard_preflight_never_pulls(self):
        with tempfile.TemporaryDirectory() as d, patch('sys.stdin.isatty',return_value=True),patch('builtins.input',side_effect=['4','qwen3:4b','/var/lib','0']),patch('ollama_registry.preflight',
            return_value={'model':'qwen3:4b','status':'ready_for_review','disk':{'enough_by_estimate':True}}),patch.object(devhub.Ollama,'pull') as pull:
            self.assertEqual(devhub.main(['--state',d,'wizard']),0)
            pull.assert_not_called()

if __name__ == '__main__':
    unittest.main()
