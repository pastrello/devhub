"""Local worker probe and short benchmark with Ollama telemetry.

No remote agent service, credential handling, shell execution or paid cloud inference.
"""
from __future__ import annotations

import platform
import re
from datetime import datetime, timezone

MODEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,95}:[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
KEEP_ALIVE = ('0', '1m', '5m', '10m')
MAX_TOKENS = (16, 32, 64, 128)

class WorkerError(Exception):
    pass

def timing_seconds(value):
    if type(value) is int and value >= 0:
        return round(value / 1_000_000_000, 4)
    return None

def tokens_per_second(count, duration):
    if type(count) is not int or count < 0 or type(duration) is not int or duration <= 0:
        return None
    return round(count * 1e9 / duration, 2)

def summarise(raw, loaded, model, gpu):
    """Report separate generation telemetry, observed residency, GPU inventory."""
    if not isinstance(raw, dict) or not isinstance(loaded, list):
        raise WorkerError('Unexpected inference/ps response')
    stat = next((m for m in loaded if isinstance(m, dict) and m.get('name') == model), {})
    size_vram = stat.get('size_vram') if type(stat.get('size_vram')) is int else None
    size = stat.get('size') if type(stat.get('size')) is int else None
    fraction = round(size_vram / size, 3) if size_vram is not None and size and 0 <= size_vram <= size else None
    return {
        'status': 'ok' if raw.get('done') is True else 'incomplete',
        'model': model,
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'total_seconds': timing_seconds(raw.get('total_duration')),
        'model_load_seconds': timing_seconds(raw.get('load_duration')),
        'prompt_tokens': raw.get('prompt_eval_count') if type(raw.get('prompt_eval_count')) is int else None,
        'output_tokens': raw.get('eval_count') if type(raw.get('eval_count')) is int else None,
        'prompt_tokens_per_second': tokens_per_second(raw.get('prompt_eval_count'), raw.get('prompt_eval_duration')),
        'generation_tokens_per_second': tokens_per_second(raw.get('eval_count'), raw.get('eval_duration')),
        'response_preview': raw.get('response', '')[:160] if isinstance(raw.get('response'), str) else '',
        'residency': {'currently_loaded': bool(stat), 'vram_bytes': size_vram,
                      'reported_model_bytes': size, 'vram_fraction_of_reported_size': fraction,
                      'expires_at': stat.get('expires_at')},
        'gpus': gpu.get('gpus', []) if isinstance(gpu, dict) else [],
        'note': ('A one-shot local measurement, not a validated comparative benchmark. '
                 'VRAM fraction uses reported bytes, not actual processor percent; '
                 'an empty /api/ps means model is no longer resident.'),
    }

def benchmark(ollama, model, gpu_probe, *, keep_alive='5m', max_tokens=64):
    if (not isinstance(model, str) or not MODEL.fullmatch(model) or
            'cloud' in model.lower()):
        raise WorkerError('Only explicit local model:tag is supported')
    if keep_alive not in KEEP_ALIVE or max_tokens not in MAX_TOKENS:
        raise WorkerError('Invalid bounded benchmark settings')
    if model not in [m.get('name') for m in ollama.inventory()]:
        raise WorkerError('Model not installed on selected local Ollama endpoint')
    data = ollama.generate_report(
        model,
        'Responda em uma frase: qual e a finalidade de um indice de banco de dados?',
        keep_alive=keep_alive,
        max_tokens=max_tokens,
    )
    return summarise(data, ollama.running(), model, gpu_probe())

def local_worker(ollama, gpu_probe):
    try:
        version = ollama.version()
        installed = [m.get('name') for m in ollama.inventory() if isinstance(m.get('name'), str)]
        loaded = [m.get('name') for m in ollama.running() if isinstance(m.get('name'), str)]
        status = 'reachable'
    except (OSError, ValueError, KeyError, TypeError):
        version, installed, loaded, status = None, [], [], 'unavailable'
    return {
        'worker': platform.node(),
        'type': 'local-only',
        'architecture': platform.machine(),
        'os': platform.system(),
        'ollama': {'status': status, 'version': version, 'installed': installed, 'loaded': loaded},
        'gpu': gpu_probe(),
        'remote_enrollment': 'disabled',
        'warning': 'Inventory is a local snapshot, not a worker registration or GPU workload guarantee'
    }
