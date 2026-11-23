"""Passive worker inventory for DevHub 0.1.5.

This is an offline metadata registry, never a transport, a trust anchor, or
an execution authorization. Imported records are always untrusted.
"""
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

MAX_BYTES = 32768
TTL_SECONDS = 900
ID = re.compile(r'^[a-z0-9][a-z0-9-]{0,62}$')
TAG = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,95}:[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$')
VERSION = 1

class WorkerRegistryError(Exception):
    pass

def valid_id(value):
    return isinstance(value, str) and bool(ID.fullmatch(value))

def _limited(value, max_len):
    if not isinstance(value, str) or len(value) > max_len:
        raise WorkerRegistryError('Invalid worker metadata field')
    return value

def validate_manifest(item, *, now=None):
    """Whitelist-only schema; no endpoints, secrets or executable configuration."""
    if not isinstance(item, dict) or set(item) != {
            'schema', 'worker_id', 'observed_at', 'hostname',
            'os', 'architecture', 'ollama', 'gpus'}:
        raise WorkerRegistryError('Unexpected or missing worker fields')
    if type(item['schema']) is not int or item['schema'] != VERSION or not valid_id(item['worker_id']):
        raise WorkerRegistryError('Invalid worker schema or ID')
    hostname = _limited(item['hostname'], 128)
    system = _limited(item['os'], 32)
    architecture = _limited(item['architecture'], 64)
    if not isinstance(item['ollama'], dict) or set(item['ollama']) != {
            'status', 'version', 'installed'}:
        raise WorkerRegistryError('Unexpected Ollama inventory fields')
    ollama = item['ollama']
    if ollama['status'] not in ('reachable', 'unavailable'):
        raise WorkerRegistryError('Invalid engine state')
    version = ollama['version']
    if version is not None:
        _limited(version, 48)
    installed = ollama['installed']
    if (not isinstance(installed, list) or len(installed) > 128
            or any(not isinstance(m, str) or not TAG.fullmatch(m)
                   or 'cloud' in m.lower() for m in installed)):
        raise WorkerRegistryError('Invalid installed model inventory')
    if not isinstance(item['gpus'], list) or len(item['gpus']) > 16:
        raise WorkerRegistryError('GPU inventory exceeds limits')
    gpus = []
    for g in item['gpus']:
        if not isinstance(g, dict) or set(g) != {
                'index', 'name', 'memory_total_mib', 'memory_free_mib',
                'driver_version'}:
            raise WorkerRegistryError('Unexpected GPU inventory fields')
        if (type(g['index']) is not int or not 0 <= g['index'] < 16
                or type(g['memory_total_mib']) is not int
                or not 1 <= g['memory_total_mib'] <= 1048576
                or type(g['memory_free_mib']) is not int
                or not 0 <= g['memory_free_mib'] <= g['memory_total_mib']):
            raise WorkerRegistryError('Invalid GPU capacity data')
        gpus.append({'index': g['index'], 'name': _limited(g['name'], 128),
                     'memory_total_mib': g['memory_total_mib'],
                     'memory_free_mib': g['memory_free_mib'],
                     'driver_version': _limited(g['driver_version'], 48)})
    stamp = item['observed_at']
    if not isinstance(stamp, str) or len(stamp) > 48:
        raise WorkerRegistryError('Invalid snapshot timestamp')
    try:
        seen = datetime.fromisoformat(stamp)
        if seen.tzinfo is None or seen.utcoffset() is None:
            raise ValueError('timezone missing')
    except ValueError as exc:
        raise WorkerRegistryError('Timestamp must be timezone-aware ISO 8601') from exc
    now = now or datetime.now(timezone.utc)
    if seen > now + timedelta(minutes=2):
        raise WorkerRegistryError('Snapshot from future clock')
    return {'schema': VERSION, 'worker_id': item['worker_id'],
            'observed_at': seen.astimezone(timezone.utc).isoformat(),
            'hostname': hostname, 'os': system, 'architecture': architecture,
            'ollama': {'status': ollama['status'], 'version': version,
                       'installed': sorted(set(installed))}, 'gpus': gpus}

def local_manifest(worker_id, local_report, *, now=None):
    if not valid_id(worker_id):
        raise WorkerRegistryError('Worker ID must contain lowercase a-z, 0-9 and dashes')
    if not isinstance(local_report, dict):
        raise WorkerRegistryError('Invalid local worker report')
    obj = {'schema': VERSION, 'worker_id': worker_id,
           'observed_at': (now or datetime.now(timezone.utc)).isoformat(),
           'hostname': local_report.get('worker', ''),
           'os': local_report.get('os', ''),
           'architecture': local_report.get('architecture', ''),
           'ollama': {'status': local_report.get('ollama', {}).get('status', 'unavailable'),
                      'version': local_report.get('ollama', {}).get('version'),
                      'installed': local_report.get('ollama', {}).get('installed', [])},
           'gpus': local_report.get('gpu', {}).get('gpus', [])}
    return validate_manifest(obj, now=now)

def read_manifest(path):
    file = Path(path)
    if file.is_symlink() or not file.is_file():
        raise WorkerRegistryError('Use an ordinary local JSON file, not a symlink')
    if file.stat().st_size > MAX_BYTES:
        raise WorkerRegistryError('Worker file exceeds size limit')
    try:
        with file.open('rb') as handle:
            raw = handle.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise WorkerRegistryError('Worker file exceeds size limit')
        item = json.loads(raw)
    except (OSError, ValueError, UnicodeError) as exc:
        raise WorkerRegistryError('Unable to parse worker JSON') from exc
    return validate_manifest(item)

def status(manifest, *, now=None):
    now = now or datetime.now(timezone.utc)
    seen = datetime.fromisoformat(manifest['observed_at'])
    age = max(0, (now - seen).total_seconds())
    return {'worker_id': manifest['worker_id'],
            'hostname': manifest['hostname'],
            'age_seconds': int(age),
            'freshness': 'recent_snapshot' if age <= TTL_SECONDS else 'stale_snapshot',
            'engine_status_at_capture': manifest['ollama']['status'],
            'model_count': len(manifest['ollama']['installed']),
            'gpu_count': len(manifest['gpus']),
            'trust': 'metadata_only_unverified',
            'remote_execution': 'disabled'}

def enroll(state, manifest, *, replace=False):
    manifest = validate_manifest(manifest)
    key = 'worker:' + manifest['worker_id']
    current = state.snapshot(key)
    if current is not None and not replace:
        raise WorkerRegistryError('Worker record exists; use --replace for an explicit overwrite')
    state.save(key, {'manifest': manifest, 'origin': 'operator_supplied',
                     'trust': 'metadata_only_unverified'})
    return status(manifest)

def list_workers(state):
    return [status(item['manifest']) for key, item in sorted(state.catalog().items())
            if key.startswith('worker:') and isinstance(item, dict)
            and isinstance(item.get('manifest'), dict)]

def show(state, worker_id):
    if not valid_id(worker_id):
        raise WorkerRegistryError('Invalid worker ID')
    record = state.snapshot('worker:' + worker_id)
    if record is None:
        raise WorkerRegistryError('Worker record not found')
    return {'status': 'ok', 'worker': status(record['manifest']),
            'manifest': record['manifest']}

def forget(state, worker_id):
    if not valid_id(worker_id):
        raise WorkerRegistryError('Invalid worker ID')
    key = 'worker:' + worker_id
    if state.snapshot(key) is None:
        raise WorkerRegistryError('Worker record not found')
    with state.db:
        state.db.execute('DELETE FROM registry WHERE source=?', (key,))
    return {'status': 'forgotten_from_local_registry', 'worker_id': worker_id,
            'remote_worker_untouched': True}
