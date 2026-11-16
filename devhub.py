"""DevHub 0.1: local-first, explicit trust, no automatic cloud billing."""
import argparse
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
from urllib import request, error, parse

VERSION = '0.1.0'
CLI = {'codex': 'codex', 'claude': 'claude', 'antigravity': 'agy', 'kiro': 'kiro-cli', 'opencode': 'opencode'}
CLOUD = ('deepseek', 'openrouter', 'openai-api', 'anthropic-api', 'gemini-api')

class Blocked(Exception):
    pass

class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise Blocked('HTTP redirect refused')

class HTTP:
    def __init__(self, base):
        u = parse.urlsplit(base)
        if u.scheme not in ('http', 'https') or not u.hostname or u.username or u.password or u.query or u.fragment:
            raise Blocked('Invalid endpoint; credentials in URL forbidden')
        self.base = base.rstrip('/')
        self.client = request.build_opener(request.ProxyHandler({}), NoRedirect())

    def call(self, path, payload=None, timeout=15):
        data = None if payload is None else json.dumps(payload).encode()
        req = request.Request(self.base + path, data=data, headers={'Content-Type': 'application/json'})
        with self.client.open(req, timeout=timeout) as res:
            raw = res.read(16 * 1024 * 1024 + 1)
        if len(raw) > 16 * 1024 * 1024:
            raise Blocked('Response too large')
        return json.loads(raw)

class Ollama:
    def __init__(self, base):
        self.http = HTTP(base)

    def inventory(self):
        return [m for m in self.http.call('/api/tags')['models'] if isinstance(m.get('name'), str)]

    def generate(self, model, prompt):
        return self.http.call('/api/generate', {'model': model, 'prompt': prompt, 'stream': False, 'options': {'num_predict': 1024}}, timeout=180)['response']

    def pull(self, model):
        if not model or '/' in model or 'cloud' in model.lower() or len(model) > 128:
            raise Blocked('Only explicit, ordinary local catalog tags are supported in 0.1')
        return self.http.call('/api/pull', {'model': model, 'stream': False}, timeout=900)

def local_candidate(name):
    # Conservative: only operator-approved tags, never automatically trust discovery.
    return bool(name) and '/' not in name and 'cloud' not in name.lower()

def plan(models, approved, provider='auto', complexity='simple'):
    eligible = sorted({m['name'] for m in models if local_candidate(m['name']) and m['name'] in approved})
    if provider in CLI or provider in CLOUD or provider == 'litellm':
        return {'status': 'blocked', 'provider': provider, 'reason': 'Cloud execution not homologated; no additional spending authorized'}
    if complexity == 'advanced' and provider == 'auto':
        return {'status': 'review', 'provider': None, 'reason': 'Advanced task requires human choice; no benchmark yet'}
    if not eligible:
        return {'status': 'blocked', 'provider': None, 'reason': 'No installed and explicitly approved local model'}
    return {'status': 'ready', 'provider': 'ollama', 'model': eligible[0], 'reason': 'Approved local model; no external inference billing expected'}

class State:
    def __init__(self, root):
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.db = sqlite3.connect(root / 'state.sqlite3')
        self.db.execute('CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, at TEXT DEFAULT CURRENT_TIMESTAMP, action TEXT, status TEXT)')
        self.db.execute('CREATE TABLE IF NOT EXISTS registry (source TEXT PRIMARY KEY, snapshot TEXT NOT NULL)')
        self.db.commit()

    def event(self, action, status):
        with self.db:
            self.db.execute('INSERT INTO events(action,status) VALUES (?,?)', (action, status))

    def save(self, source, value):
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO registry VALUES (?,?)', (source, json.dumps(value)))

    def catalog(self):
        return {k: json.loads(v) for k,v in self.db.execute('SELECT source,snapshot FROM registry')}

    def costs(self):
        return {'additional_cloud_budget_usd': 0, 'cloud_execution_enabled': False, 'events': dict(self.db.execute('SELECT action || ":" || status, COUNT(*) FROM events GROUP BY action,status')), 'local_energy_cost': 'unknown'}

def discover(ollama, gateway=None):
    result = {'cli': {k: {'installed': bool(shutil.which(v)), 'authenticated': 'unknown', 'execution': 'blocked'} for k,v in CLI.items()}, 'cloud': {k: 'disabled' for k in CLOUD}, 'ollama': {'status': 'unavailable', 'models': []}, 'litellm': {'status': 'not configured'}}
    try:
        result['ollama'] = {'status': 'reachable', 'models': ollama.inventory()}
    except (OSError, ValueError, KeyError, TypeError, Blocked):
        pass
    if gateway:
        try:
            result['litellm'] = {'status': 'reachable', 'models': HTTP(gateway).call('/v1/models')['data'], 'execution': 'blocked'}
        except (OSError, ValueError, KeyError, TypeError, Blocked):
            result['litellm'] = {'status': 'unavailable', 'execution': 'blocked'}
    return result

def main(argv=None):
    p = argparse.ArgumentParser(prog='devhub')
    p.add_argument('--version', action='version', version=VERSION)
    p.add_argument('--state', default=os.getenv('DEVHUB_STATE', str(Path.home()/'.local/state/devhub')))
    p.add_argument('--ollama', default=os.getenv('DEVHUB_OLLAMA', 'http://127.0.0.1:11434'))
    p.add_argument('--litellm', default=os.getenv('DEVHUB_LITELLM'))
    p.add_argument('--approve-local', action='append', default=[], help='Locally verified model tag; repeat as needed')
    s = p.add_subparsers(dest='cmd', required=True)
    for cmd in ('doctor','discover','catalog','costs'):
        s.add_parser(cmd)
    pull = s.add_parser('pull'); pull.add_argument('model'); pull.add_argument('--confirm-download', action='store_true')
    for cmd in ('plan','run'):
        t = s.add_parser(cmd); t.add_argument('prompt'); t.add_argument('--provider', choices=['auto','ollama','litellm',*CLI,*CLOUD], default='auto'); t.add_argument('--complexity', choices=['simple','advanced'], default='simple'); t.add_argument('--trust-local-endpoint', action='store_true')
    a = p.parse_args(argv)
    os.umask(0o077)
    state = State(Path(a.state))
    try:
        ollama = Ollama(a.ollama)
        if a.cmd in ('doctor','discover'):
            out = discover(ollama, a.litellm)
            if a.cmd == 'discover': state.save('discovery', out)
        elif a.cmd == 'catalog': out = state.catalog()
        elif a.cmd == 'costs': out = state.costs()
        elif a.cmd == 'pull':
            if not a.confirm_download: raise Blocked('Explicit --confirm-download required')
            out = ollama.pull(a.model)
            if out.get('status') != 'success': raise Blocked('Download not confirmed')
        else:
            try: models = ollama.inventory()
            except (OSError, ValueError, KeyError, TypeError, Blocked): models = []
            out = plan(models, a.approve_local, a.provider, a.complexity)
            if a.cmd == 'run':
                if out['status'] != 'ready': raise Blocked(out['reason'])
                if not a.trust_local_endpoint: raise Blocked('Confirm endpoint only performs local inference with --trust-local-endpoint')
                out['response'] = ollama.generate(out['model'], a.prompt)
        state.event(a.cmd, out.get('status','ok'))
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get('status') not in ('blocked','review') else 2
    except (OSError, ValueError, KeyError, TypeError, Blocked) as exc:
        state.event(a.cmd, 'blocked' if isinstance(exc, Blocked) else 'error')
        # Do not disclose prompts, HTTP bodies, environment or credentials in logs.
        print(json.dumps({'status':'error','reason': str(exc) if isinstance(exc, Blocked) else type(exc).__name__}), file=sys.stderr)
        return 2
    finally:
        state.db.close()

if __name__ == '__main__':
    sys.exit(main())
