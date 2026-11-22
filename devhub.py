"""DevHub 0.1: local-first, explicit trust, no automatic cloud billing."""
import argparse
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import engine_manager as em
import online_catalog as oc
import ollama_registry as rg
from datetime import datetime, timezone, timedelta
from urllib.parse import urlsplit
from urllib import request, error, parse

VERSION = '0.1.3'
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
        if (u.scheme not in ('http', 'https') or not u.hostname or u.username or u.password
                or u.query or u.fragment or u.path not in ('', '/') or u.port == 0):
            raise Blocked('Invalid endpoint; credentials, paths and query strings in URL forbidden')
        self.base = base.rstrip('/')
        self.client = request.build_opener(request.ProxyHandler({}), NoRedirect())

    def call(self, path, payload=None, timeout=15, method=None):
        if not path.startswith('/') or '://' in path:
            raise Blocked('Invalid API path')
        data = None if payload is None else json.dumps(payload).encode()
        req = request.Request(self.base + path, data=data, method=method,
                              headers={'Content-Type': 'application/json'})
        with self.client.open(req, timeout=timeout) as res:
            raw = res.read(16 * 1024 * 1024 + 1)
        if len(raw) > 16 * 1024 * 1024:
            raise Blocked('Response too large')
        return json.loads(raw) if raw else {}

class Ollama:
    def __init__(self, base):
        self.http = HTTP(base)

    def version(self):
        return self.http.call('/api/version').get('version', 'unknown')

    def inventory(self):
        return [m for m in self.http.call('/api/tags')['models'] if isinstance(m.get('name'), str)]

    def running(self):
        return self.http.call('/api/ps').get('models', [])

    def inspect(self, name):
        return self.http.call('/api/show', {'model': name})

    def generate(self, model, prompt, num_predict=1024):
        return self.http.call('/api/generate', {'model': model, 'prompt': prompt, 'stream': False,
                                               'options': {'num_predict': num_predict}}, timeout=180)['response']

    def pull(self, model):
        if not em.valid_local_tag(model):
            raise Blocked('Invalid or cloud-tagged local model')
        return self.http.call('/api/pull', {'model': model, 'stream': False}, timeout=900)

    def delete(self, model):
        if not em.valid_local_tag(model):
            raise Blocked('Invalid or cloud-tagged local model')
        return self.http.call('/api/delete', {'model': model}, method='DELETE', timeout=45)

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

    def snapshot(self, source):
        row = self.db.execute('SELECT snapshot FROM registry WHERE source=?', (source,)).fetchone()
        return json.loads(row[0]) if row else None

    def costs(self):
        return {'additional_cloud_budget_usd': 0, 'cloud_execution_enabled': False, 'events': dict(self.db.execute('SELECT action || ":" || status, COUNT(*) FROM events GROUP BY action,status')), 'local_energy_cost': 'unknown'}

def discover(ollama, gateway=None):
    result = {'cli': {k: {'installed': bool(shutil.which(v)), 'authenticated': 'unknown', 'execution': 'blocked'} for k,v in CLI.items()}, 'cloud': {k: 'disabled' for k in CLOUD}, 'ollama': {'status': 'unavailable', 'models': []}, 'litellm': {'status': 'not configured'}}
    try:
        result['ollama'] = {'status': 'reachable', 'version': ollama.version(), 'models': ollama.inventory()}
    except (OSError, ValueError, KeyError, TypeError, Blocked):
        pass
    if gateway:
        try:
            result['litellm'] = {'status': 'reachable', 'models': HTTP(gateway).call('/v1/models')['data'], 'execution': 'blocked'}
        except (OSError, ValueError, KeyError, TypeError, Blocked):
            result['litellm'] = {'status': 'unavailable', 'execution': 'blocked'}
    return result

def configure_engine_parsers(sub):
    engines = sub.add_parser('engines', help='Discover inference runtimes and installation instructions')
    eng = engines.add_subparsers(dest='engine_command', required=True)
    for name in ('list', 'status'):
        eng.add_parser(name)
    install = eng.add_parser('install'); install.add_argument('engine', choices=[e['id'] for e in em.ENGINES])
    releases = eng.add_parser('releases'); releases.add_argument('--engine', choices=list(oc.ENGINE_REPOS), default='ollama')

    models = sub.add_parser('models', help='Search and manage Ollama models')
    mod = models.add_subparsers(dest='model_command', required=True)
    srch = mod.add_parser('search'); srch.add_argument('query', nargs='?', default=''); srch.add_argument('--task', choices=['general','reasoning','coding','vision'])
    rec = mod.add_parser('recommend'); rec.add_argument('--task', choices=['general','reasoning','coding','vision'], default='coding')
    online = mod.add_parser('online'); online.add_argument('query'); online.add_argument('--limit', type=int, default=10)
    fit = mod.add_parser('fit'); fit.add_argument('model'); fit.add_argument('--models-dir')
    preflight = mod.add_parser('preflight', help='Check official Ollama manifest and storage before an approved download')
    preflight.add_argument('model'); preflight.add_argument('--storage-path', required=True)
    acquire = mod.add_parser('install', help='Download an approved model after saved manifest preflight')
    acquire.add_argument('model'); acquire.add_argument('--confirm-download', action='store_true')
    acquire.add_argument('--license-reviewed', action='store_true')
    acquire.add_argument('--trust-local-endpoint', action='store_true')
    for name in ('installed', 'running'):
        mod.add_parser(name)
    show = mod.add_parser('inspect'); show.add_argument('model')
    pull = mod.add_parser('pull'); pull.add_argument('model'); pull.add_argument('--confirm-download', action='store_true'); pull.add_argument('--trust-local-endpoint', action='store_true'); pull.add_argument('--models-dir')
    delete = mod.add_parser('delete'); delete.add_argument('model'); delete.add_argument('--confirm-delete', action='store_true'); delete.add_argument('--trust-local-endpoint', action='store_true')
    test = mod.add_parser('test'); test.add_argument('model'); test.add_argument('--trust-local-endpoint', action='store_true')
    sub.add_parser('gpu', help='Inspect GPUs without privileged changes')


def manage(a, ollama, state):
    if a.cmd == 'gpu':
        return em.gpu_inventory()
    if a.cmd == 'engines':
        if a.engine_command == 'releases':
            result = oc.official_engine_release(a.engine)
            if a.engine == 'ollama':
                try: result['installed_version'] = ollama.version()
                except (OSError, ValueError, KeyError, TypeError): result['installed_version'] = 'unknown'
            state.save('official-release:' + a.engine, result)
            return result
        if a.engine_command in ('list', 'status'):
            return {'engines': em.engines_catalog(ollama if a.engine_command == 'status' else None)}
        if a.engine != 'ollama':
            return {'status': 'planned', 'engine': a.engine, 'reason': 'Install adapter not yet homologated; no changes made'}
        return {'status': 'manual-approval-required', 'engine': 'ollama',
                'instructions': ['Review docs/proxmox-rocky9-ollama.md',
                                 'bash scripts/bootstrap-ollama-lxc.sh --check',
                                 'sudo bash scripts/bootstrap-ollama-lxc.sh --install'],
                'note': 'Commands are guidance only; nothing executed'}
    if a.model_command == 'preflight':
        if not rg.valid_tag(a.model):
            raise Blocked('Invalid default-library Ollama model tag')
        result = rg.preflight(a.model, a.storage_path)
        result['ollama_endpoint'] = ollama.http.base
        state.save('pull-plan:' + a.model, result)
        return result
    if a.model_command == 'install':
        if not (a.confirm_download and a.license_reviewed and a.trust_local_endpoint):
            raise Blocked('Explicit --confirm-download --license-reviewed --trust-local-endpoint are required')
        if not rg.valid_tag(a.model):
            raise Blocked('Invalid default-library Ollama model tag')
        endpoint = urlsplit(ollama.http.base)
        if endpoint.hostname not in ('127.0.0.1', 'localhost', '::1'):
            raise Blocked('Automated model installation is restricted to local Ollama; remote workers require authenticated transport')
        approval = state.snapshot('pull-plan:' + a.model)
        if not isinstance(approval, dict) or approval.get('status') != 'ready_for_review':
            raise Blocked('Run models preflight first and resolve storage warnings')
        if approval.get('ollama_endpoint') != ollama.http.base or approval.get('model') != a.model:
            raise Blocked('Endpoint/model differs from approved preflight')
        timestamp = datetime.fromisoformat(approval['created_at'])
        age = datetime.now(timezone.utc) - timestamp
        if not timedelta(0) <= age <= timedelta(hours=1):
            raise Blocked('Preflight expired; prepare a new plan')
        current = rg.fetch_manifest(a.model)
        if not rg.same_manifest(approval.get('manifest'), current):
            raise Blocked('Registry manifest changed since preflight; run preflight again')
        disk = rg.storage_probe(approval['disk']['path'], current['total_bytes'])
        if not disk['enough_by_estimate']:
            raise Blocked('Insufficient space in selected storage filesystem')
        outcome = ollama.pull(a.model)
        if outcome.get('status') != 'success':
            raise Blocked('Ollama did not confirm download')
        if a.model not in [m.get('name') for m in ollama.inventory()]:
            raise Blocked('Download responded success but model is not listed by local Ollama')
        return {'status': 'success', 'installed_model': a.model, 'preflight_sha256': current['manifest_sha256'],
                'notice': 'Ollama registry tag may be mutable after preflight. Validate model license, size and GPU offload before use.'}
    if a.model_command == 'online':
        result = oc.search_huggingface(a.query, a.limit)
        state.save('huggingface:' + a.query.casefold().strip(), result)
        return result
    if a.model_command == 'fit':
        if not em.valid_local_tag(a.model):
            raise Blocked('Only known, curated Ollama tags can be evaluated')
        match = next((m for m in em.MODELS if m['tag'] == a.model), None)
        if match is None: raise Blocked('Model not in curated compatibility catalog')
        gpu = em.gpu_inventory()
        eligible = []
        for g in gpu['gpus']:
            available = round(g['memory_free_mib'] / 1024, 2)
            reserve = 1.0
            eligible.append({'gpu': g['name'], 'available_gib': available,
                             'minimum_reserve_gib': reserve,
                             'fit_by_weights_only': match['weights_gib'] + reserve <= available})
        return {'model': a.model, 'weights_gib_estimate': match['weights_gib'],
                'gpu': eligible, 'disk': em.estimated_download_check(a.model, a.models_dir),
                'status': 'estimate_only',
                'warning': 'No runtime/context/KV-cache benchmark. Some weights may run on CPU; estimate is not a fit guarantee.'}
    if a.model_command in ('search', 'recommend'):
        try:
            installed = [m['name'] for m in ollama.inventory()]
        except (OSError, ValueError, KeyError, TypeError, Blocked):
            installed = []
        gpus = em.gpu_inventory()['gpus']
        max_vram = max((g['memory_total_mib'] for g in gpus), default=None)
        if a.model_command == 'search':
            matches = em.search_models(a.query, a.task, max_vram, installed)
        else:
            matches = em.search_models(task=a.task, vram_mib=max_vram, installed=installed)
        return {'catalog': 'built-in curated snapshot; not live internet search', 'gpu_vram_mib': max_vram,
                'models': matches, 'note': 'Weights size alone does not guarantee GPU fit; verify license/quantization/disk/context'}
    if a.model_command == 'installed':
        return {'models': ollama.inventory()}
    if a.model_command == 'running':
        return {'models': ollama.running()}
    if not em.valid_local_tag(a.model):
        raise Blocked('Use a valid explicit local model tag (no cloud or namespace)')
    if a.model_command == 'inspect':
        obj = ollama.inspect(a.model)
        return {'model': a.model, 'details': obj.get('details'), 'parameters': obj.get('parameters'), 'modified_at': obj.get('modified_at')}
    if not a.trust_local_endpoint:
        raise Blocked('Confirm the Ollama endpoint is a local, non-cloud runtime using --trust-local-endpoint')
    if a.model_command == 'pull':
        if not a.confirm_download:
            raise Blocked('Explicit --confirm-download required')
        if a.model not in [m['tag'] for m in em.MODELS]:
            raise Blocked('In 0.1.1, model must be in curated local catalog; see devhub models search')
        space = em.estimated_download_check(a.model, a.models_dir)
        if space['space'] == 'insufficient_estimate':
            raise Blocked('Disk space below conservative weights estimate')
        out = ollama.pull(a.model)
        if out.get('status') != 'success':
            raise Blocked('Download not confirmed by Ollama')
        return {'status':'success', 'model':a.model, 'space_estimate':space}
    if a.model_command == 'delete':
        if not a.confirm_delete:
            raise Blocked('Explicit --confirm-delete required')
        if a.model not in [m['name'] for m in ollama.inventory()]:
            raise Blocked('Model must exist on selected Ollama endpoint before deletion')
        ollama.delete(a.model)
        return {'status':'success','deleted':a.model}
    if a.model_command == 'test':
        if a.model not in [m['name'] for m in ollama.inventory()]:
            raise Blocked('Model must be installed before test')
        response = ollama.generate(a.model, 'Responda somente OK.', num_predict=32)
        running = ollama.running()
        model_stat = next((m for m in running if m.get('name') == a.model), {})
        return {'status':'ok', 'model':a.model, 'response_preview':response[:300],
                'runner_size_vram_bytes': model_stat.get('size_vram'),
                'gpu_probe':em.gpu_inventory(),
                'note':'An API reply proves inference only. Verify real GPU offload with ollama ps / nvidia-smi.'}
    raise Blocked('Unknown model command')


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
    pull = s.add_parser('pull'); pull.add_argument('model'); pull.add_argument('--confirm-download', action='store_true'); pull.add_argument('--trust-local-endpoint', action='store_true')
    for cmd in ('plan','run'):
        t = s.add_parser(cmd); t.add_argument('prompt'); t.add_argument('--provider', choices=['auto','ollama','litellm',*CLI,*CLOUD], default='auto'); t.add_argument('--complexity', choices=['simple','advanced'], default='simple'); t.add_argument('--trust-local-endpoint', action='store_true')
    configure_engine_parsers(s)
    a = p.parse_args(argv)
    os.umask(0o077)
    state = State(Path(a.state))
    action = a.cmd + ('.' + (getattr(a, 'engine_command', None) or getattr(a, 'model_command', None)) if a.cmd in ('engines','models') else '')
    try:
        ollama = Ollama(a.ollama)
        if a.cmd in ('doctor','discover'):
            out = discover(ollama, a.litellm)
            if a.cmd == 'doctor': out['gpu'] = em.gpu_inventory()
            if a.cmd == 'discover': state.save('discovery', out)
        elif a.cmd == 'catalog': out = state.catalog()
        elif a.cmd == 'costs': out = state.costs()
        elif a.cmd in ('engines', 'models', 'gpu'):
            out = manage(a, ollama, state)
        elif a.cmd == 'pull':
            if not a.confirm_download or not a.trust_local_endpoint:
                raise Blocked('Both --confirm-download and --trust-local-endpoint are required')
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
        state.event(action, out.get('status','ok'))
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get('status') not in ('blocked','review') else 2
    except (OSError, ValueError, KeyError, TypeError, Blocked, oc.CatalogError, rg.RegistryError) as exc:
        state.event(action, 'blocked' if isinstance(exc, Blocked) else 'error')
        print(json.dumps({'status':'error','reason': str(exc) if isinstance(exc, (Blocked, oc.CatalogError, rg.RegistryError)) else type(exc).__name__}), file=sys.stderr)
        return 2
    finally:
        state.db.close()

if __name__ == '__main__':
    sys.exit(main())
