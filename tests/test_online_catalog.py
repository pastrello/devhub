import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import devhub
import online_catalog as oc


class OnlineCatalogTests(unittest.TestCase):
    def test_fixed_hosts_and_path(self):
        for url in ('http://huggingface.co/api/models', 'https://evil.example/api/models',
                    'https://api.github.com/evil', 'https://u:p@huggingface.co/api/models'):
            with self.assertRaises(oc.CatalogError):
                oc.get_json(url)

    def test_huggingface_search_is_metadata_only(self):
        response = [{'id': 'Qwen/Qwen3-4B', 'downloads': 42, 'pipeline_tag': 'text-generation',
                     'tags': ['gguf', 'license:apache-2.0'], 'gated': False},
                    {'id': '../../../etc/passwd', 'downloads': 4},
                    {'id': 'other/blocked', 'gated': 'manual'}]
        with patch('online_catalog.get_json', return_value=response) as get:
            out = oc.search_huggingface('qwen', 10)
        self.assertEqual(out['count'], 2)
        self.assertTrue(out['models'][0]['gguf_hint'])
        self.assertEqual(out['models'][0]['license'], 'apache-2.0')
        self.assertFalse(out['models'][0]['installable_by_devhub'])
        self.assertIsNone(out['models'][0]['ollama_tag'])
        self.assertIn('huggingface.co/api/models?', get.call_args.args[0])

    def test_search_bounds(self):
        for q, limit in [('x', 10), ('x'*101, 10), ('qwen', 0), ('qwen', 31)]:
            with self.assertRaises(oc.CatalogError):
                oc.search_huggingface(q, limit)

    def test_engine_release_metadata(self):
        with patch('online_catalog.get_json', return_value={'tag_name': 'v0.40.17', 'published_at': '2026-11-21'}) as get:
            out = oc.official_engine_release('ollama')
        self.assertEqual(out['latest_tag'], 'v0.40.17')
        self.assertIn('/repos/ollama/ollama/releases/latest', get.call_args.args[0])
        self.assertEqual(out['action'], 'informational_only')

    def test_engine_release_unknown(self):
        with self.assertRaises(oc.CatalogError):
            oc.official_engine_release('unknown')

    def test_cli_online_persists_snapshot(self):
        with tempfile.TemporaryDirectory() as d, patch('online_catalog.search_huggingface',
                return_value={'source': 'huggingface', 'models': [], 'count': 0}), patch.object(devhub.Ollama, 'pull') as pull:
            self.assertEqual(devhub.main(['--state', d, 'models', 'online', 'Qwen', '--limit', '3']), 0)
            state = devhub.State(Path(d))
            self.assertIn('huggingface:qwen', state.catalog())
            state.db.close()
            pull.assert_not_called()

    def test_cli_release_does_not_install(self):
        with tempfile.TemporaryDirectory() as d, patch('online_catalog.official_engine_release',
                return_value={'engine': 'ollama', 'latest_tag': 'v0.40.17'}):
            with patch.object(devhub.Ollama, 'version', return_value='0.40.17'):
                self.assertEqual(devhub.main(['--state', d, 'engines', 'releases', '--engine', 'ollama']), 0)

    def test_cli_fit_is_non_mutating(self):
        gpu = {'status': 'ok', 'gpus': [{'name': 'NVIDIA GeForce RTX 3060 Ti', 'memory_free_mib': 6000}]}
        with tempfile.TemporaryDirectory() as d, patch('engine_manager.gpu_inventory', return_value=gpu), patch.object(devhub.Ollama, 'pull') as pull:
            self.assertEqual(devhub.main(['--state', d, 'models', 'fit', 'qwen3:4b']), 0)
            pull.assert_not_called()

    def test_cli_fit_unknown_refused(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(devhub.main(['--state', d, 'models', 'fit', 'not-in-list:4b']), 2)

    def test_online_error_no_billing(self):
        with tempfile.TemporaryDirectory() as d, patch('online_catalog.search_huggingface',
                side_effect=oc.CatalogError('rate limited')):
            self.assertEqual(devhub.main(['--state', d, 'models', 'online', 'Qwen']), 2)

    def test_response_size_limit(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, n): return b'x'*(oc.MAX_BYTES + 1)
        with patch('online_catalog.request.build_opener') as build:
            build.return_value.open.return_value = Response()
            with self.assertRaises(oc.CatalogError):
                oc.get_json('https://huggingface.co/api/models?search=qwen')

    def test_git_release_does_not_construct_download_url(self):
        with patch('online_catalog.get_json', return_value={'tag_name': 'v1', 'assets': [{'url': 'https://evil'}]}):
            release = oc.official_engine_release('llama.cpp')
        self.assertEqual(release['url'], 'https://github.com/ggml-org/llama.cpp/releases')
        self.assertNotIn('assets', release)


if __name__ == '__main__':
    unittest.main()
