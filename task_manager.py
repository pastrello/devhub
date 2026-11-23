"""Task Manager phase 1: explicit local inference and static-only quality screening.

Never executes generated code, writes to Git, invokes shells or reaches cloud providers.
"""
import ast
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from urllib.parse import urlsplit

class TaskError(Exception):
    pass

PROFILE = "worker-id-validator-v1"
TASK_ID = re.compile(r'^[a-z0-9][a-z0-9-]{0,62}$')
TAG = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,95}:[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$')
PROMPT = ('Escreva uma função Python 3.12 que valide IDs de workers. Aceite somente '
          'letras minúsculas, números e hífens, com até 63 caracteres. '
          'Inclua três testes unittest. Retorne apenas o código.')
MAX_TOKENS = 512
MAX_BYTES = 16384
MAX_FILE_BYTES = 32768
VALID_PATTERNS = frozenset({r'[a-z0-9][a-z0-9-]{0,62}', r'^[a-z0-9][a-z0-9-]{0,62}$'})

def _key(task_id):
    if not isinstance(task_id,str) or not TASK_ID.fullmatch(task_id):
        raise TaskError('Task ID must be 1..63 lowercase letters, digits or hyphens')
    return 'task:' + task_id

def _now():
    return datetime.now(timezone.utc).isoformat()

def _summary(record):
    return {k:record[k] for k in ('id','profile','model','provider','provider_status',
              'task_status','acceptance_status','human_review_required',
              'generated_code_executed','attempt')}

def create(state, task_id, *, model, profile=PROFILE):
    key=_key(task_id)
    if profile != PROFILE:
        raise TaskError('Only reviewed Task #001 profile supported in phase 1')
    if not isinstance(model,str) or not TAG.fullmatch(model) or 'cloud' in model.lower():
        raise TaskError('Explicit local Ollama model:tag required')
    if state.snapshot(key) is not None:
        raise TaskError('Task already registered; no implicit replacement')
    record={'schema':1,'id':task_id,'profile':profile,'model':model,'provider':'ollama',
            'prompt':PROMPT,'created_at':_now(),'updated_at':_now(),
            'provider_status':'not_checked','task_status':'created',
            'acceptance_status':'not_evaluated','human_review_required':True,
            'generated_code_executed':False,'acceptance_method':'static_ast_v1',
            'limits':{'max_output_tokens':MAX_TOKENS,'max_output_bytes':MAX_BYTES,
                      'ollama_timeout_seconds':180},
            'attempt':0,'result':None}
    state.save(key,record)
    return {'status':'created','task':_summary(record)}

def load(state, task_id):
    record=state.snapshot(_key(task_id))
    if not isinstance(record,dict) or record.get('schema')!=1 or record.get('id')!=task_id:
        raise TaskError('Task not found or incompatible record')
    return record

def list_tasks(state):
    records=[]
    for key,item in sorted(state.catalog().items()):
        if key.startswith('task:') and isinstance(item,dict) and item.get('schema')==1 and item.get('id')==key[5:]:
            records.append(_summary(item))
    return {'status':'ok','tasks':records}

def show(state,task_id):
    return {'status':'ok','task':load(state,task_id)}

def read_response_file(path):
    file=Path(path)
    if not file.is_absolute() or file.is_symlink() or not file.is_file():
        raise TaskError('Response requires an absolute regular non-symlink file')
    if file.stat().st_size>MAX_FILE_BYTES:
        raise TaskError('Response file too large')
    try:
        with file.open('rb') as f:
            raw=f.read(MAX_FILE_BYTES+1)
        if len(raw)>MAX_FILE_BYTES:
            raise TaskError('Response file too large')
        raw=raw.decode('utf-8')
    except (OSError,UnicodeError) as exc:
        raise TaskError('Response must be readable UTF-8') from exc
    try: payload=json.loads(raw)
    except ValueError: payload=raw
    if isinstance(payload,dict):
        if not isinstance(payload.get('response'),str):
            raise TaskError('JSON must contain a string response')
        return payload['response'],payload.get('model')
    if not isinstance(payload,str):
        raise TaskError('Response must be Python text or DevHub JSON')
    return payload,None

def _source(raw):
    if not isinstance(raw,str) or not raw.strip():
        raise TaskError('Empty or non-text response')
    if len(raw.encode('utf-8'))>MAX_BYTES:
        raise TaskError('Response exceeds 16KiB limit')
    code=raw.strip()
    fence='\x60'*3
    if code.startswith(fence):
        expression=r'\x60{3}(?:python|py)?\s*\n([\s\S]*?)\n\x60{3}\s*'
        match=re.fullmatch(expression,code,flags=re.I)
        if not match:
            raise TaskError('Expected exactly one complete Python code block')
        code=match.group(1).strip()
    if fence in code:
        raise TaskError('Nested or multiple code blocks rejected')
    return code

def static_screen(raw):
    """Only a conservative AST screen. It never executes output Python."""
    try: code=_source(raw)
    except TaskError as exc:
        return {'static_status':'failed','checks':[{'criterion':'format','passed':False,
                'reason':str(exc)}],'code_sha256':None,'tests_executed':False}
    digest=hashlib.sha256(code.encode('utf-8')).hexdigest()
    try: tree=ast.parse(code)
    except (SyntaxError,ValueError) as exc:
        return {'static_status':'failed','checks':[{'criterion':'python_syntax','passed':False,
                'reason':type(exc).__name__}],'code_sha256':digest,'tests_executed':False}
    nodes=list(ast.walk(tree))
    if len(nodes)>600:
        return {'static_status':'failed','checks':[{'criterion':'ast_limit','passed':False,
                'reason':'AST exceeds 600 nodes'}],'code_sha256':digest,'tests_executed':False}
    functions=[n for n in tree.body if isinstance(n,ast.FunctionDef)
               and n.name=='validate_worker_id']
    proper=(len(functions)==1 and len(functions[0].args.args)==1
            and functions[0].args.vararg is None and functions[0].args.kwarg is None
            and not functions[0].args.kwonlyargs)
    count=0
    for cls in tree.body:
        if not isinstance(cls,ast.ClassDef): continue
        if not any((isinstance(b,ast.Attribute) and b.attr=='TestCase'
                    and isinstance(b.value,ast.Name) and b.value.id=='unittest')
                   or (isinstance(b,ast.Name) and b.id=='TestCase')
                   for b in cls.bases): continue
        count += sum(isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))
                     and n.name.startswith('test_') for n in cls.body)
    pattern=any(isinstance(n,ast.Constant) and isinstance(n.value,str)
                and n.value in VALID_PATTERNS for n in nodes)
    fullmatch=bool(functions) and any(isinstance(n,ast.Call)
                 and ((isinstance(n.func,ast.Attribute) and n.func.attr=='fullmatch')
                      or (isinstance(n.func,ast.Name) and n.func.id=='fullmatch'))
                 for n in ast.walk(functions[0]))
    checks=[
       {'criterion':'function_signature','passed':proper,'reason':None if proper else 'Expected validate_worker_id(worker_id)'},
       {'criterion':'independent_test_structure','passed':count>=3,'reason':None if count>=3 else f'Only {count} unittest methods; 3 requested'},
       {'criterion':'approved_id_regex','passed':pattern,'reason':None if pattern else 'Registry pattern not found'},
       {'criterion':'fullmatch_in_validator','passed':fullmatch,'reason':None if fullmatch else 'Use fullmatch rather than isalnum/count'}]
    return {'static_status':'passed_pending_review' if all(c['passed'] for c in checks) else 'failed',
            'checks':checks,'code_sha256':digest,'tests_executed':False,
            'note':'AST is only a conservative screen; no semantic or sandbox test was run.'}

def evaluate(state,task_id,raw,*,source,duration_seconds=None):
    record=load(state,task_id)
    if record['profile']!=PROFILE:
        raise TaskError('Unsupported acceptance profile')
    if record['attempt']>=5:
        raise TaskError('Maximum 5 attempts per lab task')
    if not isinstance(raw,str):
        raise TaskError('Response must be text')
    report=static_screen(raw)
    record['attempt']+=1
    record['updated_at']=_now()
    record['task_status']='response_received'
    record['acceptance_status']=('static_passed_review_required'
            if report['static_status']=='passed_pending_review' else 'acceptance_failed')
    record['result']={'source':source,'generated_response':raw,
                      'response_sha256':hashlib.sha256(raw.encode('utf-8')).hexdigest(),
                      'duration_seconds':duration_seconds,'assessment':report}
    state.save(_key(task_id),record)
    return {'status':'evaluated','task':_summary(record),'assessment':report,
            'notice':'Generated Python not executed or committed; human review required.'}

def evaluate_file(state,task_id,path):
    record=load(state,task_id)
    raw,claimed=read_response_file(path)
    if claimed is not None and claimed!=record['model']:
        raise TaskError('Imported model differs from registered model')
    return evaluate(state,task_id,raw,source='operator_imported_unverified')

def run(state,ollama,task_id,*,approved,trust_local_endpoint):
    record=load(state,task_id)
    if record['attempt']>=5:
        raise TaskError('Maximum five attempts reached')
    if not trust_local_endpoint:
        raise TaskError('--trust-local-endpoint required')
    url=urlsplit(ollama.http.base)
    if url.scheme!='http' or url.hostname not in ('127.0.0.1','::1') or url.username or url.password:
        raise TaskError('Only local loopback Ollama HTTP is allowed')
    if record['model'] not in approved:
        raise TaskError('Approve model with --approve-local MODEL')
    if record['model'] not in [m.get('name') for m in ollama.inventory()]:
        raise TaskError('Requested model not installed locally')
    record['provider_status']='ready'
    record['updated_at']=_now()
    state.save(_key(task_id),record)
    start=monotonic()
    try:
        raw=ollama.generate(record['model'],record['prompt'],num_predict=MAX_TOKENS)
    except (OSError,ValueError,KeyError,TypeError) as exc:
        record['task_status']='generation_error'
        record['updated_at']=_now()
        record['result']={'error_type':type(exc).__name__}
        state.save(_key(task_id),record)
        raise TaskError('Local inference failed: '+type(exc).__name__) from exc
    if not isinstance(raw,str) or len(raw.encode('utf-8'))>MAX_BYTES:
        raise TaskError('Generated response invalid or too large')
    return evaluate(state,task_id,raw,source='local_ollama',
                    duration_seconds=round(monotonic()-start,4))
