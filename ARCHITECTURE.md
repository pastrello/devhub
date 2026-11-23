# Architecture

- Deterministic core, provider adapters, registry, cost policy and audit.
- Current: Python standard library, SQLite per-user, Ollama HTTP, optional LiteLLM model-list inventory. CLI presence detection only. Explicit operator approval and endpoint trust before local generation. No paid inference.
- Target: PostgreSQL 18, independent adapters, workers with strong isolation and Git worktrees, task queue, checkpoints, benchmarks, cross-provider review, FastAPI/HTMX/Caddy, systemd.
- Future: expandable local/cloud registry with official metadata, licensing and hardware validation, opt-in model downloads and human approval for new charges. Model outputs and repository instructions are untrusted data; no arbitrary executable adapters from discovered catalogs.
- Selection must consider capability, privacy, actual availability, marginal cost, measured success and limits. Prefer ordinary deterministic tools, then suitable local resources, permitted existing subscriptions and only then authorized API costs.
- No provider credential scraping, account rotation to bypass quotas, or automatic acceptance of contracts. Official provisioning only. Independent user authentication in original CLIs; do not assume chat subscriptions provide APIs.
- Claude Code legal guidance: https://code.claude.com/docs/en/legal-and-compliance — distinguish end-user use of official binary from third-party service routing. Antigravity headless docs: https://antigravity.google/docs/cli/headless/. Both require separate validation before enabling.

## Engine Manager 0.1.1

`engine_manager.py` fornece metadados estáticos e inspeção de GPU sem privilegiar processos. `devhub.py` contém a interface CLI, políticas de autorização explícita e adaptador Ollama. Não há instalação automática silenciosa. `install-system.sh` é o único instalador root do aplicativo, com execução subsequente como usuário isolado. Scripts de instalação de Ollama continuam separados. Diretório `/var/lib/devhub` não armazena credenciais comerciais.

Seleção por tarefa é apenas filtragem estática; modelos curados não são verificados dinamicamente nem garantia de compatibilidade. Em versões futuras: catálogos de fontes oficiais, manifests assinados, ciclos de vida dos motores, checagem de espaço conforme storage real, quota e worker manager.


## Official discovery adapters (0.1.2)

`online_catalog.py` is metadata-only; fixed HTTPS hosts/paths, short timeouts, capped responses, no redirects, no ambient proxy, no credential forwarding. Hugging Face entries are NOT Ollama tags; they remain informational until an independently verified compatible image, license, footprint and origin are mapped and explicitly approved. GitHub release metadata never triggers an installer. `models fit` compares only curated **estimated weight size** against free VRAM (with a 1 GiB planning margin); it cannot determine runtime speed, KV-cache requirements, supported GPU compute, quantization or whether the LXC can offload successfully. User-controlled queries are sent to Hugging Face and cached locally; no private prompts or project secrets should be entered. Existing local model operations retain confirmation checks and default-deny cloud execution.


## 0.1.3 registry preflight and approved model acquisition

Ollama's registry provides an OCI-like manifest with blob digests and lengths. `ollama_registry.py` accepts only exact official default-library `model:tag` names, HTTPS registry.ollama.ai, no credentials/proxies/redirects, bounded JSON and conservative layer/media validations. If the registry serves a manifest list, abort rather than guessing platform/runtime. The only new mutable operation is explicitly confirmed `models install`, restricted to a loopback Ollama endpoint and a still-valid stored plan. Preflight/manifests are **not** proofs of license, CPU/GPU fit or supply-chain authenticity. A mutable tag can change between checks; after download, Ollama's installed inventory is inspected, but exact digest pinning remains future work. Inspecting the wrong storage mount may yield false capacity readings; administrator must confirm filesystem identity and quotas. Research for authenticated cross-LXC worker registration is the next independent deliverable.


## 0.1.4 — bounded local benchmark

`local_worker.py` is a read-only local inventory and one-shot local inference probe. The benchmark uses fixed prompt, bounded tokens/context and explicit `keep_alive`. It records Ollama's nanosecond timing fields and /api/ps VRAM reporting. Inference is explicitly authorized and only loopback URLs are accepted. Model residency can change between inference and /api/ps sampling; absence is not failure. Reported `size_vram / size` is *not* the GPU CPU offload fraction; do not treat it as a reliable CUDA benchmark. `devhub wizard` wraps safe read-only tasks and explicit preflight, never silently purchasing or downloading. Remote worker management remains design-only, waiting for authenticated isolation and registration.


## 0.1.5 — zero-trust passive worker registry

Worker records are local SQLite metadata-only snapshots with a whitelist schema, strict limits and an explicit registration/removal gate. They contain **no command path, endpoint, token, IP address or executable hooks**. No network discovery or remote execution occurs. A 15-minute age classifier distinguishes fresh snapshots from stale ones, **not** authenticated liveness. Imported JSON is untrusted and cannot affect routing or permissions. Future encrypted worker transport will have independent identity, certificate/PSK rotation, enrollment, revocation, port restrictions and isolated execution. Never treat the worker registry as a trust anchor or scheduler.
