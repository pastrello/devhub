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
