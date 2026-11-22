# Roadmap

- 0.1.x: validate Rocky 9/10, Python 3.12, real Ollama and GPU workers; hardware inventory and documented local trust checks.
- 0.2: official provider onboarding and capability probes, authorized subscription adapters, explicit cost controls; LiteLLM inference only after local routing verification or explicit budget.
- 0.3: model discovery, validated catalogs, licenses, disk/VRAM limits, approved automatic installs and benchmarks.
- 0.4: PostgreSQL state, job queue, bounded concurrency, worker authentication, isolation and checkpoints.
- 0.5: Git project context, review and orchestration; isolated branches/worktrees, no production credentials.
- 0.6+: portal, intelligent scheduling, verified cross-review, recovery, security and operational hardening.

Version numbers are tentative; no release claims before tests.

## Progresso 0.1.1

- [x] Descoberta CLI do Ollama e catálogo de motores (os demais apenas planejados/inventário).
- [x] Catálogo curado de modelos com busca/recomendação offline.
- [x] Inventário NVIDIA e visibilidade GPU.
- [x] Listar/inspecionar/baixar/testar/excluir modelos Ollama com aprovação explícita.
- [x] Instalação global controlada root -> runtime devhub sem root; rollback.
- [ ] Homologação real dos comandos DevHub no LXC Rocky 9.
- [ ] Descoberta dinâmica de modelos e versões com fontes oficiais.
- [ ] Instalação assistida de motores pelo DevHub (além de fornecer instruções).
- [ ] Estimativa de requisitos baseada em variantes reais, contexto e hardware.
- [ ] Benchmarks executados automaticamente com métricas válidas.
- [ ] Controle remoto de outros workers, autenticação e isolamento distribuído.


## 0.1.2 implemented / next

- [x] Search public Hugging Face model metadata through official API (read-only).
- [x] Read current release tags for Ollama/llama.cpp/vLLM/LiteLLM through official GitHub API.
- [x] Persist discovery snapshots in existing SQLite registry.
- [x] Evaluate known Ollama tags against currently free VRAM and optional available disk (estimates only).
- [x] Deny automatic downloading of arbitrary discovered models and automatic engine upgrades.
- [ ] Validate live HTTPS responses and installer in Rocky 9 LXC.
- [ ] Search official Ollama library model/tag pages with a supported interface or vetted parser and provenance checks.
- [ ] Verify exact artifact, license, quantization, RAM/VRAM and storage before automated installation.
- [ ] Engine upgrade workflow with provenance, semantic compatibility, tested rollback and explicit administrator approval.
- [ ] Add authenticated remote workers and agent management, benchmark metrics, PostgreSQL queue.


## 0.1.3 implemented / pending

- [x] Read official registry model manifest with known default-library tag.
- [x] Validate layer names, SHA256 digest formatting and byte sizes; summarize estimated download footprint.
- [x] Explicit storage mount planning, estimated reserve and refusal on insufficient disk.
- [x] Plan fingerprint and 1-hour expiry, dual authorization plus license-review declaration.
- [x] Recheck mutable registry fingerprint before invoking model download; verify installed inventory.
- [x] Block remote endpoints for unattended installation until trusted worker protocol exists.
- [ ] Validate official API response against qwen2.5-coder:3b from IA-01.
- [ ] Support recent Ollama manifest lists and platform-specific runners.
- [ ] Verify actual downloaded digest, licensing, GPU memory and quantization.
- [ ] Implement authenticated worker agents and multi-LXC inventory.
- [ ] Create a streamlined interactive model search/choice/install UI.
