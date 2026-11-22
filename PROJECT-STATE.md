# Project state — 0.1.0 PoC

Implemented: per-user CLI installer; static provider inventory and executable presence detection; live Ollama model listing and explicit pull/generation; optional unauthenticated LiteLLM catalog endpoint; deterministic local selection; zero-additional-cloud-cost deny policy; SQLite discovery snapshots and action/status audit.

Evidence: 13/13 unit tests passed in Python 3.13.5 in the development container; bash -n passed. No real provider, GPU, Rocky 9/10 installation, authentication, API billing or network integration validated. No charges incurred by these tests. Installer and Python 3.12 runtime pending lab validation.

Not implemented: hardware detection, live catalog harvesting, automatic local model installs, provider onboarding, cloud CLI execution, paid budget accounting, benchmarks, intelligent routing, Git project access, portal, worker isolation, PostgreSQL, multi-agent scheduling.

Next safe test: non-root installation on Rocky; doctor/discover; verify a known local Ollama tag with plan then run. Do not enable cloud until permissions, quotas and billing are verified. SQLite is temporary for PoC; PostgreSQL remains the distributed design target.

## Laboratório GPU informado em 2026-11-22

O operador informou Proxmox VE 9, LXC Rocky Linux 9 e RTX 3060 Ti 8 GB, driver NVIDIA 620.73.04. `nvidia-smi` funciona dentro do contêiner, mas inferência GPU ainda não foi homologada. Um bootstrap experimental de Ollama e guia foram propostos em branch `feat/lxc-rocky9-ollama-lab` (PR pendente de revisão/merge). Prioridade explicitada: DevHub Engine Manager deve descobrir e instalar motores, pesquisar/baixar modelos, inventariar hardware e gerenciar lifecycle sem exigir CLI manual. Root apenas para instalação de serviços; execução dos agentes e motores sem root. O bootstrap foi validado somente por bash -n em ambiente de desenvolvimento não-Rocky, sem download nem instalação real.


## Incidente de homologação de inferência — 2026-11-22

O operador executou `bootstrap-ollama-lxc.sh --install` com serviço systemd ativo e download `qwen3:4b` bem-sucedido; a inferência devolveu HTTP 500 com `llama-server binary not found`. Causa imediata confirmada pelo erro: runtime não localizado nos caminhos esperados. A razão exata (pacote upstream incompleto versus extração/localização) ainda não foi comprovada. Corrigido o bootstrap para validar também `/usr/lib/ollama/llama-server`; criado reparo com download em staging e backup/rollback. Requer testes reais antes de merge. Nenhuma evidência de inferência GPU bem-sucedida ainda.

## Homologação inferência GPU — 2026-11-22

Operador confirmou `ollama run qwen3:4b` com resposta OK e `ollama ps` com `100% GPU`, runner `llamacpp`, contexto `4096`, consumo ~3.2 GB. NVIDIA RTX 3060 Ti reportou 3207/8192 MiB de VRAM. Primeiro teste de inferência GPU **APROVADO no laboratório IA-01**. Ainda não comprovamos causa raiz ou ação exata que eliminou erro anterior de `llama-server` nem a execução do CLI DevHub como usuário não-root. Evidência: `docs/evidence/2026-11-22-ia01-qwen3-gpu.md`. Manter PR #1 em draft até validação de instalador/segurança; não confundir inferência Ollama bem-sucedida com conclusão do Engine Manager.

## Engine Manager 0.1.1 — atualização em branch de laboratório

Implementado em `feat/lxc-rocky9-ollama-lab`: catálogo local curado de motores (Ollama suportado, LiteLLM inventário, llama.cpp/vLLM planejados); catálogo curado de modelos pequenos com busca e recomendação por tarefa; inventário NVIDIA por `nvidia-smi`; Ollama API version/tags/show/ps/pull/delete; inferência local curta; autorização explícita antes de download/exclusão/teste; instalador system-wide root -> runtime isolado devhub, diretório de releases e rollback; preservado instalador por usuário.

Validação de desenvolvimento: 29/29 testes unitários usando mocks e `bash -n` de instaladores no container de desenvolvimento (Python 3.13.5). Não houve execução dos novos recursos no LXC nem GitHub Actions comprovado. **Não** foram implementados busca dinâmica na web, benchmarks comparativos, descoberta autônoma de novos motores, download de motores pelo próprio aplicativo, instalação distribuída ou provedores cloud pagos.

Próxima evidência requerida: instalar `install-system.sh` no Rocky 9, validar `devhub gpu`, `engines status`, `models installed/search/test` com Ollama local. O Ollama qwen3:4b já foi homologado manualmente no LXC; esse fato é independente dos novos comandos do DevHub.


## DevHub 0.1.2 — pesquisa oficial e estimativa de adequação (branch de laboratório)

Criada branch `feat/model-discovery-0.1.2` a partir da branch Rocky 9 LXC, como evolução revisável (sem alterar main). Adicionado `online_catalog.py`: pesquisa pública na API Hugging Face, leitura de releases do GitHub oficial dos motores Ollama, llama.cpp, vLLM e LiteLLM, hosts/endpoints fixos, sem credenciais/proxies/redirects e resposta limitada a 1 MiB. CLI: `models online`, `models fit`, `engines releases`. Snapshots armazenados em SQLite para inspeção. Instaladores preparados para copiar o novo módulo e atualizar a versão 0.1.2.

Testes locais: 41/41 unitários (Python 3.13.5), e `bash -n` dos instaladores; fixtures simuladas, sem consulta web real e sem instalação no LXC. O operador havia confirmado testes do 0.1.1 em IA-01, mas **não** houve homologação da versão 0.1.2.

Status: catálogo online **somente descoberta**, não instala automaticamente resultados do Hugging Face; a lista curada de tags Ollama permanece a única permitida para download. Verificações de VRAM/disco são aproximadas, sem benchmark de qualidade ou consumo real. Pesquisa na biblioteca web oficial do Ollama, downloads/atualizações de motores, dependências/licenças automatizadas e múltiplos workers com autenticação seguem pendentes.

Segurança: nenhum recurso cloud pago ativado, nenhuma alteração no serviço Ollama existente, orçamento extra inicial US$ 0.


## 0.1.3 — Oficial Ollama Registry Preflight (branch de trabalho)

Implementado em `feat/registry-preflight-0.1.3`: `ollama_registry.py` com validação de tags locais, consulta pública read-only ao registry.ollama.ai, validação da estrutura de camadas e hashes SHA256, cálculo de tamanho dos blobs e estimativa de espaço em filesystem explicitamente informado. Adicionados comandos `devhub models preflight TAG --storage-path PATH` (guarda plano com validade de uma hora) e `devhub models install TAG --confirm-download --license-reviewed --trust-local-endpoint` (consulta de novo manifesto; rejeita mudança, orçamento de disco insuficiente, endpoint remoto, aprovação ausente ou tag divergente). Valida após download que o modelo aparece em Ollama /api/tags. Instalação dos novos componentes adaptada em `install.sh` e `install-system.sh`; versão 0.1.3.

Validação: 15 testes de unidade do parser/preflight em ambiente Python local; testes adicionais de CLI versionados no GitHub para executar no CI. *Não* foi efetuado download real da API pública do registry neste ambiente e não há homologação real de 0.1.3 no LXC IA-01. O operador confirmou a versão 0.1.1 e a inferência GPU do Ollama. Consulta remota pode requerer autenticação do registry ou usar uma lista de manifestos não suportada pelo parser; o programa deve falhar fechado nessas situações.

Ainda não implementado: descoberta web oficial completa de tags Ollama, conversão confiável HF -> Ollama, resolução multi-plataforma de manifestos, revisão automática de licença/arquivos/quantização, atualização administrativa de motores, workers remotos autenticados, controle de filas PostgreSQL e benchmarks comparativos. Nenhuma despesa adicional autorizada.
