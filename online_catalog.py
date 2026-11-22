"""Read-only official discovery: Hugging Face model metadata and GitHub releases.

Never execute downloaded content, install a model, or query arbitrary URLs.
"""
import json
import re
from urllib import parse, request

MAX_BYTES = 1024 * 1024
MODEL_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,95}/[A-Za-z0-9][A-Za-z0-9_.-]{0,95}$')
ENGINE_REPOS = {'ollama': 'ollama/ollama', 'llama.cpp': 'ggml-org/llama.cpp',
                'vllm': 'vllm-project/vllm', 'litellm': 'BerriAI/litellm'}

class CatalogError(Exception):
    pass

class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise CatalogError('Official source redirected unexpectedly')

def get_json(url, timeout=12):
    """Fixed official API hosts only; no redirects, proxies, credentials or arbitrary API paths."""
    u = parse.urlsplit(url)
    if (u.scheme != 'https' or u.hostname not in ('huggingface.co', 'api.github.com')
            or u.username or u.password or u.port is not None or u.fragment):
        raise CatalogError('Not an approved official discovery endpoint')
    if u.hostname == 'huggingface.co' and u.path != '/api/models':
        raise CatalogError('Unexpected Hugging Face API path')
    if u.hostname == 'api.github.com' and not re.fullmatch(r'/repos/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/releases/latest', u.path):
        raise CatalogError('Unexpected GitHub release API path')
    opener = request.build_opener(request.ProxyHandler({}), NoRedirect())
    req = request.Request(url, headers={'Accept': 'application/json', 'User-Agent': 'DevHub-EngineManager/0.1.2'})
    try:
        with opener.open(req, timeout=timeout) as resp:
            body = resp.read(MAX_BYTES + 1)
    except (OSError, ValueError) as exc:
        raise CatalogError('Official source request failed') from exc
    if len(body) > MAX_BYTES:
        raise CatalogError('Catalog response exceeds size limit')
    try:
        return json.loads(body)
    except (ValueError, UnicodeDecodeError) as exc:
        raise CatalogError('Official source returned invalid JSON') from exc

def search_huggingface(query, limit=10):
    """Official Hub metadata search; hits are NOT Ollama-installable tags."""
    if not isinstance(query, str) or not 2 <= len(query.strip()) <= 100:
        raise CatalogError('Search query must have 2–100 characters')
    if not isinstance(limit, int) or not 1 <= limit <= 30:
        raise CatalogError('Limit must be 1–30')
    params = parse.urlencode({'search': query.strip(), 'limit': limit, 'sort': 'downloads', 'direction': -1})
    rows = get_json('https://huggingface.co/api/models?' + params)
    if not isinstance(rows, list):
        raise CatalogError('Unexpected Hugging Face response')
    models = []
    for item in rows[:limit]:
        if not isinstance(item, dict) or not MODEL_ID.fullmatch(str(item.get('id', ''))):
            continue
        ident = item['id']
        tags = item.get('tags') if isinstance(item.get('tags'), list) else []
        license_tags = [str(t).split(':', 1)[1] for t in tags if isinstance(t, str) and t.startswith('license:')]
        models.append({
            'id': ident, 'source': 'huggingface', 'url': 'https://huggingface.co/' + ident,
            'pipeline': str(item.get('pipeline_tag') or 'unknown')[:100],
            'license': license_tags[0] if license_tags else 'unknown',
            'gated': item.get('gated', False), 'private': bool(item.get('private', False)),
            'downloads': item.get('downloads') if isinstance(item.get('downloads'), int) else None,
            'gguf_hint': any(isinstance(t, str) and t.lower() == 'gguf' for t in tags),
            'ollama_tag': None, 'installable_by_devhub': False,
        })
    return {'source': 'huggingface', 'query': query.strip(), 'count': len(models),
            'models': models,
            'warning': 'Metadata-only discovery; do not pass Hugging Face IDs to Ollama pull. Verify license, files, model format and trusted origin.'}

def official_engine_release(engine):
    if engine not in ENGINE_REPOS:
        raise CatalogError('Unknown engine')
    repository = ENGINE_REPOS[engine]
    item = get_json('https://api.github.com/repos/' + repository + '/releases/latest')
    if not isinstance(item, dict) or not isinstance(item.get('tag_name'), str):
        raise CatalogError('Official GitHub release metadata unavailable')
    return {'engine': engine, 'source': 'github-release', 'repository': repository,
            'latest_tag': item['tag_name'][:100], 'published_at': item.get('published_at'),
            'url': 'https://github.com/' + repository + '/releases',
            'action': 'informational_only',
            'note': 'Latest release is not automatically compatible or approved; no update installed.'}
