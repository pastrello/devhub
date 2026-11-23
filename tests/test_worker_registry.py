import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
import devhub
import worker_registry as wr


NOW = datetime(2026, 11, 22, 23, 0, tzinfo=timezone.utc)


def local_report():
    return {
        'worker': 'IA-01',
        'os': 'Linux',
        'architecture': 'x86_64',
        'ollama': {'status': 'reachable', 'version': '0.40.17',
                   'installed': ['qwen3:4b', 'qwen2.5-coder:3b'], 'loaded': []},
        'gpu': {'status': 'ok', 'gpus': [
            {'index': 0, 'name': 'NVIDIA GeForce RTX 3060 Ti',
             'memory_total_mib': 8192, 'memory_free_mib': 5615,
             'driver_version': '620.73.04'}]}
    }


class WorkerRegistryTests(unittest.TestCase):
    def test_local_manifest(self):
        manifest = wr.local_manifest('ia-01', local_report(), now=NOW)
        self.assertEqual(manifest['worker_id'], 'ia-01')
        self.assertEqual(manifest['gpus'][0]['memory_total_mib'], 8192)
        self.assertEqual(len(manifest['ollama']['installed']), 2)
        self.assertNotIn('endpoint', manifest)

    def test_ids_rejected(self):
        for bad in ('IA-01', '../root', 'host/1', 'http://evil', 'x'*64, ''):
            with self.assertRaises(wr.WorkerRegistryError):
                wr.local_manifest(bad, local_report(), now=NOW)

    def test_schema_is_strict(self):
        obj = wr.local_manifest('ia-01', local_report(), now=NOW)
        for addition in ({'endpoint': 'http://127.0.0.1:11434'},
                         {'api_key': 'secret'}, {'shell': '/bin/sh'}):
            with self.assertRaises(wr.WorkerRegistryError):
                wr.validate_manifest({**obj, **addition}, now=NOW)
        with self.assertRaises(wr.WorkerRegistryError):
            wr.validate_manifest({**obj, 'schema': True}, now=NOW)

    def test_model_inventory_rejects_remote(self):
        obj = wr.local_manifest('ia-01', local_report(), now=NOW)
        with self.assertRaises(wr.WorkerRegistryError):
            wr.validate_manifest({**obj, 'ollama': {
                **obj['ollama'], 'installed': ['qwen:cloud']}}, now=NOW)

    def test_gpu_validation(self):
        obj = wr.local_manifest('ia-01', local_report(), now=NOW)
        for gpu in ({**obj['gpus'][0], 'memory_free_mib': 9000},
                    {**obj['gpus'][0], 'memory_total_mib': True}):
            with self.assertRaises(wr.WorkerRegistryError):
                wr.validate_manifest({**obj, 'gpus': [gpu]}, now=NOW)

    def test_future_timestamp_rejected(self):
        obj = wr.local_manifest('ia-01', local_report(), now=NOW)
        with self.assertRaises(wr.WorkerRegistryError):
            wr.validate_manifest({**obj, 'observed_at': (NOW+timedelta(hours=1)).isoformat()}, now=NOW)

    def test_stale_snapshot(self):
        obj = wr.local_manifest('ia-01', local_report(), now=NOW)
        self.assertEqual(wr.status(obj, now=NOW+timedelta(seconds=200))['freshness'], 'recent_snapshot')
        self.assertEqual(wr.status(obj, now=NOW+timedelta(hours=1))['freshness'], 'stale_snapshot')
        self.assertEqual(wr.status(obj, now=NOW)['remote_execution'], 'disabled')

    def test_db_round_trip_duplicate_and_forget(self):
        with tempfile.TemporaryDirectory() as d:
            state = devhub.State(Path(d))
            obj = wr.local_manifest('ia-01', local_report())
            self.assertEqual(wr.enroll(state, obj)['worker_id'], 'ia-01')
            with self.assertRaises(wr.WorkerRegistryError):
                wr.enroll(state, obj)
            self.assertEqual(len(wr.list_workers(state)), 1)
            self.assertEqual(wr.show(state, 'ia-01')['manifest']['hostname'], 'IA-01')
            self.assertEqual(wr.enroll(state, obj, replace=True)['worker_id'], 'ia-01')
            self.assertTrue(wr.forget(state, 'ia-01')['remote_worker_untouched'])
            self.assertEqual(wr.list_workers(state), [])
            state.db.close()

    def test_file_import_and_size(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'worker.json'
            obj = wr.local_manifest('ia-01', local_report())
            path.write_text(json.dumps(obj), encoding='utf-8')
            self.assertEqual(wr.read_manifest(path)['worker_id'], 'ia-01')
            path.write_bytes(b'x' * (wr.MAX_BYTES + 1))
            with self.assertRaises(wr.WorkerRegistryError):
                wr.read_manifest(path)

    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'data.json'
            target.write_text(json.dumps(wr.local_manifest('ia-01',local_report())))
            alias=Path(d)/'shortcut.json'
            alias.symlink_to(target)
            with self.assertRaises(wr.WorkerRegistryError):
                wr.read_manifest(alias)

    def test_import_requires_confirm(self):
        with tempfile.TemporaryDirectory() as d, patch('worker_registry.read_manifest') as reader:
            self.assertEqual(devhub.main(['--state',d,'workers','import-file','some.json']),2)
            reader.assert_not_called()

    def test_enroll_local_requires_confirm(self):
        with tempfile.TemporaryDirectory() as d, patch('local_worker.local_worker') as probe:
            self.assertEqual(devhub.main(['--state',d,'workers','enroll-local','--id','ia-01']),2)
            probe.assert_not_called()

    def test_snapshot_is_not_enrollment(self):
        with tempfile.TemporaryDirectory() as d, patch('local_worker.local_worker',return_value=local_report()):
            self.assertEqual(devhub.main(['--state',d,'workers','snapshot','--id','ia-01']),0)
            state = devhub.State(Path(d))
            self.assertEqual(wr.list_workers(state), [])
            state.db.close()

    def test_enroll_and_list_cli(self):
        with tempfile.TemporaryDirectory() as d, patch('local_worker.local_worker',return_value=local_report()):
            self.assertEqual(devhub.main(['--state',d,'workers','enroll-local','--id','ia-01','--confirm-enroll']),0)
            self.assertEqual(devhub.main(['--state',d,'workers','list']),0)
            state = devhub.State(Path(d))
            self.assertEqual(len(wr.list_workers(state)),1)
            state.db.close()

    def test_forget_requires_confirm(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(devhub.main(['--state',d,'workers','forget','ia-01']),2)

    def test_file_import_cli(self):
        with tempfile.TemporaryDirectory() as d:
            file=Path(d)/'worker.json'
            file.write_text(json.dumps(wr.local_manifest('ia-02',local_report())))
            self.assertEqual(devhub.main(['--state',d,'workers','import-file',str(file),'--confirm-import']),0)
            state=devhub.State(Path(d))
            self.assertEqual(len(wr.list_workers(state)),1)
            state.db.close()

if __name__ == '__main__':
    unittest.main()
