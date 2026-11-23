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


## 0.1.4 deliverables and next steps

- [x] `workers local`: local inventory of Ollama, installed/running models, GPU and OS.
- [x] `models benchmark`: bounded fixed-prompt inference with timings/tokens/s and GPU residency snapshot.
- [x] `wizard`: interactive user-guided menu without implicit downloads or paid APIs.
- [x] Explicit finite model keep-alive to make post-test `models running` inspection meaningful.
- [ ] Live 0.1.4 test on Proxmox VE 9 Rocky Linux 9 LXC IA-01.
- [ ] Multi-run statistical benchmarking with cost, context and prompt-quality evaluation.
- [ ] Authenticated, authorized Worker Manager for multiple Linux/Windows nodes.
- [ ] Stream-safe model pull/status reporting and signed binary lifecycle manager.
- [ ] Browser-based portal to simplify search, downloads and worker management.


## 0.1.5 worker inventory milestones

- [x] Versioned strict metadata manifest for local worker snapshot export.
- [x] Explicit registration/import/replacement/removal with confirmation and audit via existing DevHub state.
- [x] Basic 15-minute stale snapshot reporting, never masquerading as a live authenticated heartbeat.
- [x] No remote endpoint, shell commands, cloud billing, API exposures or credentials during this phase.
- [ ] Test the 0.1.5 CLI on IA-01 and re-run full test suite.
- [ ] Add second LXC/VM inventory using manually transferred snapshot.
- [ ] Authenticated worker enrollment, TLS channel, key rotation and revocation.
- [ ] Verified heartbeats, device health, queueing, per-worker authorization and resource budgets.
- [ ] Integrated web portal and work distribution when remote transport is proven safe.


## Worker Manager: security foundation started

- [x] Final `workers show` and SQLite audit hotfix 0.1.5.1 reported operational on IA-01.
- [x] Draft mTLS identity/authz ADR with TLS 1.3, worker SAN and pinned certificates.
- [x] Experimental library: strict server/client TLS context and read-only worker authorization.
- [x] Negative unit tests for missing/wrong certificates and unauthorized actions (versioned, execution pending).
- [ ] Test entire new suite in Rocky Python 3.12; verify real mTLS handshake with test certs.
- [ ] Admin key/certificate provisioning and documented rotation/revocation.
- [ ] Authenticated read-only worker inventory service, initially bound to loopback for isolated tests.
- [ ] Explicit firewall rules and network-only-on-approval worker enrollment.
- [ ] Remote inference and scheduling only after independent security review.


## 0.1.6 loopback mutual TLS validation

- [x] 15 mTLS authorization-policy unit tests passed on IA-01 Python 3.12 (operator confirmed).
- [x] Real TLS 1.3 mutual handshake on loopback with ephemeral CA/server/worker certs and certificate pinning: 8/8 local development tests passed.
- [x] Negative tests: no client cert, unknown CA both sides, wrong SAN, invalid pin, wrong hostname and TLS 1.2.
- [ ] Repeat 8 live loopback tests and full suite in Rocky IA-01.
- [ ] Define strict bounded signed/authorized inventory-only message framing.
- [ ] Test enrollment/rotation/revocation, session teardown and replay protection.
- [ ] Deploy an explicitly approved authenticated inventory-only service on a private network after firewall/identity review.
- [ ] Remote inference remains blocked pending separate policy review.


## Decisão do laboratório: um único LXC até amadurecer o Worker Manager

- [x] OpenSSL 3.5.9 e **8/8 testes mTLS reais OK no Rocky IA-01** (Python 3.12) em 22/11/2026.
- [ ] Confirmar saída final da suíte geral no IA-01; a execução foi informada, mas não seu resultado final.
- [ ] Implementar framing JSON delimitado, tamanho máximo, versão e ação `inventory.read`, usando somente `127.0.0.1`.
- [ ] Diferenciar coordenador e worker em processos locais, com credenciais temporárias e armazenamento separado para teste (sem daemon persistente).
- [ ] Testar negações/replay, revogação de pin, rotação, timeouts e isolamento; não autorizar comandos/execução remota.
- [ ] Medir RAM, disco, VRAM e concorrência antes de propor aumento do LXC.
- [ ] **Marco para pedir novos LXCs**: protocolo autenticado validado no Rocky/CI, segurança das ações read-only, instaladores por papel, firewall e rollback documentados, perfil de recursos fundamentado em métricas. Enviar instruções e dimensionamento ao operador quando cumprido, antes de implantar outros contêineres.

Não solicitar novos LXCs, GPU extra ou alteração Proxmox enquanto houver somente trabalho de protocolo, API local e autenticação.
