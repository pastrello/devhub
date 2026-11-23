import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import devhub
import task_manager as tm

MODEL = 'qwen2.5-coder:3b'
BAD = """import unittest
def validate_worker_id(worker_id: str) -> bool:
    if not worker_id.isalnum() or worker_id.count('-') > 1:
        return False
    if len(worker_id) > 63: return False
    return True
class TestWorkerIdValidation(unittest.TestCase):
    def test_valid_worker_id(self):
        self.assertTrue(validate_worker_id('john-doe-123'))
        self.assertTrue(validate_worker_id('jane.doe-456'))
    def test_invalid_worker_id(self):
        self.assertFalse(validate_worker_id('123-456-7890'))
"""
GOOD = """import re
import unittest
WORKER_ID = re.compile(r'[a-z0-9][a-z0-9-]{0,62}')
def validate_worker_id(worker_id: str) -> bool:
    return isinstance(worker_id, str) and WORKER_ID.fullmatch(worker_id) is not None
class TestWorkerIdValidation(unittest.TestCase):
    def test_valid(self):
        self.assertTrue(validate_worker_id('ia-01'))
    def test_invalid(self):
        self.assertFalse(validate_worker_id('ABC'))
    def test_length(self):
        self.assertFalse(validate_worker_id('a'*64))
"""

class State:
    def __init__(self): self.db={}
    def save(self,k,v): self.db[k]=json.loads(json.dumps(v))
    def snapshot(self,k): return self.db.get(k)
    def catalog(self): return dict(self.db)

class FakeOllama:
    def __init__(self,base='http://127.0.0.1:11434'):
        self.http=type('HTTP',(),{'base':base})()
        self.called=False
    def inventory(self): return [{'name':MODEL}]
    def generate(self,model,prompt,num_predict=1024):
        assert model==MODEL and num_predict<=512 and '63 caracteres' in prompt
        self.called=True
        return BAD

class TaskManagerTests(unittest.TestCase):
    def setUp(self):
        self.state=State()
        tm.create(self.state,'task-001',model=MODEL)

    def test_original_bad_answer_fails(self):
        report=tm.static_screen(BAD)
        self.assertEqual(report['static_status'],'failed')
        failures={x['criterion'] for x in report['checks'] if not x['passed']}
        self.assertIn('independent_test_structure',failures)
        self.assertIn('approved_id_regex',failures)
        self.assertIn('fullmatch_in_validator',failures)
        self.assertFalse(report['tests_executed'])

    def test_correct_regex_is_only_static_passed(self):
        report=tm.static_screen(GOOD)
        self.assertEqual(report['static_status'],'passed_pending_review')
        self.assertFalse(report['tests_executed'])

    def test_invalid_syntax_fails(self):
        self.assertEqual(tm.static_screen('def validate_worker_id(:')['static_status'],'failed')

    def test_oversized_response_fails(self):
        self.assertEqual(tm.static_screen('a'*16385)['static_status'],'failed')

    def test_multi_codeblocks_fail(self):
        fence=chr(96)*3
        code=fence+'python\n'+GOOD+'\n'+fence+'\n'+fence+'python\n'+GOOD+'\n'+fence
        self.assertEqual(tm.static_screen(code)['static_status'],'failed')

    def test_no_implicit_task_overwrite(self):
        with self.assertRaises(tm.TaskError):
            tm.create(self.state,'task-001',model=MODEL)

    def test_remote_and_cloud_model_tags_blocked(self):
        for model in ('qwen:cloud','qwen','foo/qwen:3b','../qwen:3b'):
            with self.assertRaises(tm.TaskError):
                tm.create(self.state,'task-002',model=model)

    def test_requires_explicit_model_approval(self):
        cli=FakeOllama()
        with self.assertRaises(tm.TaskError):
            tm.run(self.state,cli,'task-001',approved=[],trust_local_endpoint=True)
        with self.assertRaises(tm.TaskError):
            tm.run(self.state,cli,'task-001',approved=[MODEL],trust_local_endpoint=False)
        self.assertFalse(cli.called)

    def test_no_remote_model_endpoint(self):
        for url in ('http://192.0.2.1:11434','https://127.0.0.1:11434'):
            with self.assertRaises(tm.TaskError):
                tm.run(self.state,FakeOllama(url),'task-001',approved=[MODEL],
                       trust_local_endpoint=True)

    def test_local_inference_does_not_execute_generated_code(self):
        cli=FakeOllama()
        with patch('builtins.exec',side_effect=AssertionError('unsafe')):
            result=tm.run(self.state,cli,'task-001',approved=[MODEL],
                          trust_local_endpoint=True)
        self.assertTrue(cli.called)
        self.assertEqual(result['task']['acceptance_status'],'acceptance_failed')
        self.assertEqual(result['task']['provider_status'],'ready')
        self.assertFalse(result['task']['generated_code_executed'])

    def test_good_answer_never_auto_approved(self):
        result=tm.evaluate(self.state,'task-001',GOOD,source='test')
        self.assertEqual(result['task']['acceptance_status'],'static_passed_review_required')
        self.assertTrue(result['task']['human_review_required'])

    def test_imported_json_is_unverified(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'response.json'
            p.write_text(json.dumps({'model':MODEL,'response':BAD}))
            tm.evaluate_file(self.state,'task-001',str(p))
            self.assertEqual(tm.load(self.state,'task-001')['result']['source'],
                             'operator_imported_unverified')

    def test_wrong_claimed_model_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'response.json'
            p.write_text(json.dumps({'model':'qwen3:4b','response':BAD}))
            with self.assertRaises(tm.TaskError):
                tm.evaluate_file(self.state,'task-001',str(p))

    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'answer.py';p.write_text(BAD)
            q=Path(d)/'alias';q.symlink_to(p)
            with self.assertRaises(tm.TaskError):
                tm.evaluate_file(self.state,'task-001',str(q))

    def test_five_attempt_limit(self):
        for i in range(5): tm.evaluate(self.state,'task-001',BAD,source='test')
        with self.assertRaises(tm.TaskError):
            tm.evaluate(self.state,'task-001',BAD,source='test')

    def test_list_excludes_prompt(self):
        records=tm.list_tasks(self.state)['tasks']
        self.assertEqual(len(records),1)
        self.assertNotIn('prompt',records[0])

    def test_cli_create_show_with_sqlite(self):
        with tempfile.TemporaryDirectory() as d, patch('sys.stdout',io.StringIO()):
            self.assertEqual(devhub.main(['--state',d,'tasks','create',
                                          '--id','task-001','--model',MODEL]),0)
            self.assertEqual(devhub.main(['--state',d,'tasks','show','task-001']),0)
            state=devhub.State(Path(d))
            self.assertEqual(tm.load(state,'task-001')['task_status'],'created')
            state.db.close()

    def test_cli_run_without_approval_denied(self):
        with tempfile.TemporaryDirectory() as d, patch('sys.stdout',io.StringIO()):
            self.assertEqual(devhub.main(['--state',d,'tasks','create',
                                          '--id','task-001','--model',MODEL]),0)
            with patch.object(devhub.Ollama,'generate') as generate:
                self.assertEqual(devhub.main(['--state',d,'tasks','run',
                                              'task-001','--trust-local-endpoint']),2)
                generate.assert_not_called()

    def test_cli_local_mock_records_failed_acceptance(self):
        with tempfile.TemporaryDirectory() as d, patch('sys.stdout',io.StringIO()):
            self.assertEqual(devhub.main(['--state',d,'tasks','create',
                                          '--id','task-001','--model',MODEL]),0)
            with patch.object(devhub.Ollama,'inventory',return_value=[{'name':MODEL}]), \
                 patch.object(devhub.Ollama,'generate',return_value=BAD):
                self.assertEqual(devhub.main(['--state',d,'--approve-local',MODEL,'tasks','run',
                                              'task-001','--trust-local-endpoint']),0)
            state=devhub.State(Path(d))
            self.assertEqual(tm.load(state,'task-001')['acceptance_status'],'acceptance_failed')
            self.assertEqual(state.costs()['events']['tasks.run:evaluated'],1)
            state.db.close()

if __name__=='__main__':
    unittest.main()
