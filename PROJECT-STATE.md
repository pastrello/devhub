# Project state — 0.1.0 PoC

Implemented: per-user CLI installer; static provider inventory and executable presence detection; live Ollama model listing and explicit pull/generation; optional unauthenticated LiteLLM catalog endpoint; deterministic local selection; zero-additional-cloud-cost deny policy; SQLite discovery snapshots and action/status audit.

Evidence: 13/13 unit tests passed in Python 3.13.5 in the development container; bash -n passed. No real provider, GPU, Rocky 9/10 installation, authentication, API billing or network integration validated. No charges incurred by these tests. Installer and Python 3.12 runtime pending lab validation.

Not implemented: hardware detection, live catalog harvesting, automatic local model installs, provider onboarding, cloud CLI execution, paid budget accounting, benchmarks, intelligent routing, Git project access, portal, worker isolation, PostgreSQL, multi-agent scheduling.

Next safe test: non-root installation on Rocky; doctor/discover; verify a known local Ollama tag with plan then run. Do not enable cloud until permissions, quotas and billing are verified. SQLite is temporary for PoC; PostgreSQL remains the distributed design target.

## Laboratório GPU informado em 2026-11-22

O operador informou Proxmox VE 9, LXC Rocky Linux 9 e RTX 3060 Ti 8 GB, driver NVIDIA 620.73.04. `nvidia-smi` funciona dentro do contêiner, mas inferência GPU ainda não foi homologada. Um bootstrap experimental de Ollama e guia foram propostos em branch `feat/lxc-rocky9-ollama-lab` (PR pendente de revisão/merge). Prioridade explicitada: DevHub Engine Manager deve descobrir e instalar motores, pesquisar/baixar modelos, inventariar hardware e gerenciar lifecycle sem exigir CLI manual. Root apenas para instalação de serviços; execução dos agentes e motores sem root. O bootstrap foi validado somente por bash -n em ambiente de desenvolvimento não-Rocky, sem download nem instalação real.


## Incidente de homologação de inferência — 2026-11-22

O operador executou `bootstrap-ollama-lxc.sh --install` com serviço systemd ativo e download `qwen3:4b` bem-sucedido; a inferência devolveu HTTP 500 com `llama-server binary not found`. Causa imediata confirmada pelo erro: runtime não localizado nos caminhos esperados. A razão exata (pacote upstream incompleto versus extração/localização) ainda não foi comprovada. Corrigido o bootstrap para validar também `/usr/lib/ollama/llama-server`; criado reparo com download em staging e backup/rollback. Requer testes reais antes de merge. Nenhuma evidência de inferência GPU bem-sucedida ainda.
