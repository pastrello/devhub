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
