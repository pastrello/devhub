"""Engine/model discovery without cloud calls or privileged side effects.

The built-in catalog is deliberately small and curated; it is NOT a live registry.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

ENGINES = (
    {'id': 'ollama', 'kind': 'local', 'availability': 'supported', 'homepage': 'https://ollama.com/', 'description': 'Local model runtime with management API'},
    {'id': 'llama.cpp', 'kind': 'local', 'availability': 'planned', 'homepage': 'https://github.com/ggml-org/llama.cpp', 'description': 'GGUF inference server'},
    {'id': 'vllm', 'kind': 'local', 'availability': 'planned', 'homepage': 'https://docs.vllm.ai/', 'description': 'High-throughput inference server'},
    {'id': 'litellm', 'kind': 'gateway', 'availability': 'inventory-only', 'homepage': 'https://docs.litellm.ai/', 'description': 'Provider/API gateway; routes may cost money'},
)

# Informational approximate weights/download sizes. Context KV-cache, overhead and
# runtime/quantization choices can increase required VRAM dramatically.
MODELS = (
    {'tag': 'qwen3:4b', 'tasks': ['general', 'reasoning'], 'weights_gib': 2.5, 'url': 'https://ollama.com/library/qwen3', 'note': 'Thinking may be enabled'},
    {'tag': 'gemma3:4b', 'tasks': ['general', 'vision'], 'weights_gib': 3.1, 'url': 'https://ollama.com/library/gemma3', 'note': 'License review required'},
    {'tag': 'qwen2.5-coder:3b', 'tasks': ['coding'], 'weights_gib': 1.9, 'url': 'https://ollama.com/library/qwen2.5-coder', 'note': 'Small code-oriented model'},
    {'tag': 'qwen2.5-coder:7b', 'tasks': ['coding'], 'weights_gib': 4.7, 'url': 'https://ollama.com/library/qwen2.5-coder', 'note': 'Memory use depends on context'},
    {'tag': 'deepseek-r1:1.5b', 'tasks': ['reasoning'], 'weights_gib': 1.1, 'url': 'https://ollama.com/library/deepseek-r1', 'note': 'Small reasoning model'},
    {'tag': 'llama3.2:3b', 'tasks': ['general'], 'weights_gib': 2.0, 'url': 'https://ollama.com/library/llama3.2', 'note': 'License review required'},
)
TAG = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,95}:[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}$')


def valid_local_tag(tag):
    return isinstance(tag, str) and bool(TAG.fullmatch(tag)) and 'cloud' not in tag.casefold()


def gpu_inventory():
    exe = shutil.which('nvidia-smi')
    if not exe:
        return {'status': 'unavailable', 'gpus': [], 'reason': 'nvidia-smi unavailable'}
    try:
        p = subprocess.run([exe, '--query-gpu=index,name,memory.total,memory.free,driver_version', '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=8, check=True)
        rows = []
        for line in p.stdout.splitlines():
            a = [x.strip() for x in line.split(',')]
            if len(a) != 5:
                continue
            rows.append({'index': int(a[0]), 'name': a[1], 'memory_total_mib': int(a[2]), 'memory_free_mib': int(a[3]), 'driver_version': a[4]})
        return {'status': 'ok' if rows else 'unavailable', 'gpus': rows}
    except (OSError, ValueError, subprocess.SubprocessError):
        return {'status': 'unavailable', 'gpus': [], 'reason': 'GPU probe failed; no driver changes attempted'}


def engines_catalog(ollama=None):
    cli = {'ollama': 'ollama', 'llama.cpp': 'llama-server', 'vllm': 'vllm', 'litellm': 'litellm'}
    result = []
    for engine in ENGINES:
        item = dict(engine)
        item['cli_installed'] = shutil.which(cli[item['id']]) is not None
        if item['id'] == 'ollama' and ollama is not None:
            try:
                item['api_version'] = ollama.version()
                item['reachable'] = True
            except (OSError, ValueError, KeyError, TypeError):
                item['reachable'] = False
        result.append(item)
    return result


def search_models(query='', task=None, vram_mib=None, installed=()):
    text = query.casefold().strip()
    installed = set(installed)
    candidates = []
    for entry in MODELS:
        if text and text not in (entry['tag'] + ' ' + ' '.join(entry['tasks']) + ' ' + entry['note']).casefold():
            continue
        if task and task not in entry['tasks']:
            continue
        row = dict(entry)
        row['installed'] = row['tag'] in installed
        if vram_mib is not None:
            # Classification refers to *approximate weights only*, not actual fit.
            row['weights_vs_vram'] = ('weights_above_vram' if row['weights_gib'] * 1024 > vram_mib
                                      else 'weights_below_vram_not_guaranteed')
        candidates.append(row)
    return candidates


def estimated_download_check(tag, path=None):
    item = next((m for m in MODELS if m['tag'] == tag), None)
    if path is None:
        return {'known_size_gib': item['weights_gib'] if item else None,
                'space': 'unverified', 'note': 'Actual Ollama model storage path not provided'}
    target = Path(path)
    if not target.is_dir():
        raise ValueError('Model storage directory must already exist')
    free_gib = round(shutil.disk_usage(target).free / 1024**3, 2)
    # 25% buffer is not a guarantee for temp files, layers or runtime.
    estimate = item['weights_gib'] * 1.25 if item else None
    return {'known_size_gib': item['weights_gib'] if item else None, 'free_gib': free_gib,
            'space': 'insufficient_estimate' if estimate is not None and free_gib < estimate else 'not_guaranteed',
            'note': 'Approximate weights; check disk/manifest and model license before installing'}
