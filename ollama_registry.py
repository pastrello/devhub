"""Read-only official Ollama registry preflight; never downloads models."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from urllib import request

REGISTRY = "https://registry.ollama.ai"
MAX_RESPONSE = 1024 * 1024
MAX_BYTES = 1024 ** 4
TAG = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,95}:[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}$")
DIGEST = re.compile(r"^sha256:[a-f0-9]{64}$")
WEIGHTS = "application/vnd.ollama.image.model"

class RegistryError(Exception):
    pass

class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise RegistryError("Official registry redirected unexpectedly")

def valid_tag(tag):
    return isinstance(tag, str) and bool(TAG.fullmatch(tag)) and "cloud" not in tag.casefold()

def manifest_url(tag):
    if not valid_tag(tag):
        raise RegistryError("Only explicit local default-library model:tag names are supported")
    name, version = tag.split(":", 1)
    return f"{REGISTRY}/v2/library/{name}/manifests/{version}"

def parse_manifest(tag, payload, raw=None):
    """Fail closed on manifest lists: selecting a runtime/platform requires separate review."""
    if not valid_tag(tag) or not isinstance(payload, dict):
        raise RegistryError("Invalid manifest")
    layers = payload.get("layers")
    if not isinstance(layers, list) or not 1 <= len(layers) <= 128:
        raise RegistryError("Unsupported manifest list or invalid layer count")
    total = 0
    weights = 0
    for entry in layers:
        if not isinstance(entry, dict):
            raise RegistryError("Invalid manifest layer")
        media, digest, size = entry.get("mediaType"), entry.get("digest"), entry.get("size")
        if not isinstance(media, str) or not media.startswith("application/vnd.ollama.image."):
            raise RegistryError("Unsupported manifest layer type")
        if not isinstance(digest, str) or not DIGEST.fullmatch(digest):
            raise RegistryError("Invalid SHA256 layer digest")
        if type(size) is not int or not 0 <= size <= MAX_BYTES:
            raise RegistryError("Invalid layer size")
        total += size
        if media == WEIGHTS:
            weights += size
    if not 1024 * 1024 <= weights <= total <= MAX_BYTES:
        raise RegistryError("Manifest has no local model weights or exceeds size limit")
    raw = raw if raw is not None else json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return {
        "source": "official_ollama_registry",
        "model": tag,
        "manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "layers": len(layers),
        "weight_bytes": weights,
        "total_bytes": total,
        "url": manifest_url(tag),
        "license": "not_verified",
        "notice": "Model license, CUDA support and runtime overhead are not established by the manifest"
    }

def fetch_manifest(tag):
    url = manifest_url(tag)
    opener = request.build_opener(request.ProxyHandler({}), NoRedirect())
    req = request.Request(url, headers={
        "Accept": "application/vnd.docker.distribution.manifest.v2+json, application/vnd.ollama.manifest.list.v2+json",
        "User-Agent": "DevHub/0.1.3"
    })
    try:
        with opener.open(req, timeout=12) as res:
            raw = res.read(MAX_RESPONSE + 1)
    except (OSError, ValueError, RegistryError) as exc:
        raise RegistryError("Official Ollama registry unavailable or tag not found") from exc
    if len(raw) > MAX_RESPONSE:
        raise RegistryError("Manifest too large")
    try:
        return parse_manifest(tag, json.loads(raw), raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise RegistryError("Invalid manifest JSON") from exc

def storage_probe(path, required_bytes):
    """Inspect explicitly chosen storage mount. Never infer it from user HOME."""
    if not isinstance(path, str) or not path.startswith("/"):
        raise RegistryError("Provide an absolute storage path")
    directory = Path(path)
    if not directory.is_dir() or directory.is_symlink():
        raise RegistryError("Storage mount must be an existing directory, not a symlink")
    try:
        free = shutil.disk_usage(directory).free
    except OSError as exc:
        raise RegistryError("Unable to inspect model storage filesystem") from exc
    # 30% overhead + 1 GiB reserve; estimates only.
    recommended = int(required_bytes * 1.30 + 1024 ** 3)
    return {"path": str(directory), "free_bytes": free,
            "estimated_required_bytes": recommended, "enough_by_estimate": free >= recommended,
            "notice": "Estimated reserve is not a guarantee; the actual Ollama store may reside on another mount"}

def preflight(tag, path, fetch=None):
    manifest = (fetch or fetch_manifest)(tag)
    if manifest.get("model") != tag:
        raise RegistryError("Manifest identity mismatch")
    disk = storage_probe(path, manifest["total_bytes"])
    return {
        "status": "ready_for_review" if disk["enough_by_estimate"] else "blocked_insufficient_space",
        "model": tag, "manifest": manifest, "disk": disk,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "approval_required": True,
        "warnings": ["No download performed", "Review model license before approval",
                     "Model tags are mutable; the plan must be rechecked before a pull"]
    }

def same_manifest(old, new):
    return (isinstance(old, dict) and isinstance(new, dict)
            and old.get("model") == new.get("model")
            and old.get("manifest_sha256") == new.get("manifest_sha256")
            and old.get("total_bytes") == new.get("total_bytes"))
