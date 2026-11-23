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


## 0.1.4 — Worker local, benchmark e wizard

Operador confirmou no IA-01 `devhub models test qwen2.5-coder:3b --trust-local-endpoint` com `status:ok`, resposta `OK`, `runner_size_vram_bytes:2163568803`, RTX 3060 Ti 8192 MiB (5615 MiB livres durante snapshot); `models running` e `ollama ps` estavam vazios na observação posterior. Isso confirma inferência local e telemetria parcial; a lista vazia é compatível com unload por `keep_alive`, sem causa exata demonstrada. Não se deve classificar esta segunda observação como falha GPU. A primeira inferência GPU comprovada com `100% GPU` foi Qwen3 4B.

Implementada em `feat/local-worker-benchmark-0.1.4`: módulo `local_worker.py`; `devhub workers local` inventário sem registro remoto, `models benchmark` com limites fixos e `keep_alive` finito, resultado persistido em SQLite com métricas da API do Ollama, `devhub wizard` interativo (sem compras, downloads implícitos ou privilégios). Instaladores atualizados para módulo novo e versão 0.1.4. Testes novos adicionados para autorização e telemetria, aguardando validação completa em CI e LXC real. Os dois PRs de base seguem draft até homologação.

Ainda não implementado: servidor de worker remoto, autenticação mTLS, comunicação segura entre LXCs, pesquisas web interativas ricas, benchmarks com controle de qualidade e repetição, registro automático de novos motores, portal web.

## IA-01 — homologação 0.1.4 confirmada em 2026-11-22

Operador enviou `devhub --version=0.1.4`, `workers local` detectando RTX 3060 Ti 8192 MiB, Ollama 0.40.17 e modelos `qwen2.5-coder:3b`/`qwen3:4b`. `models benchmark qwen2.5-coder:3b --trust-local-endpoint --keep-alive 5m` retornou resposta válida, 112,73 tokens/s geração, 554,98 tokens/s avaliação do prompt, total 2,6702 s, carga do modelo 2,2583 s, 36 tokens gerados, 2.163.568.803 bytes reportados tanto em size quanto size_vram. `models running` confirmou modelo em memória após execução, expiry 2026-11-23 01:07 UTC. Evidência: `docs/evidence/2026-11-22-ia01-qwen25-coder3b-benchmark.md`. A GPU foi inferida da telemetria reportada e do teste local; métricas não substituem benchmark estatístico. O wizard interativo não foi homologado nesta evidência.


## 0.1.5 — Worker Registry passivo

Implementado na branch `feat/worker-registry-0.1.5` a partir da 0.1.4 homologada: `worker_registry.py` com manifesto versionado `schema:1`, ID explícito, horário UTC, sistema, arquitetura, dados Ollama e GPUs, formatos estritos e limite de arquivo de 32 KiB. `devhub workers snapshot --id` exporta inventário local sem registro; `enroll-local`, `import-file` com confirmação explícita, `list`, `show`, `forget` gerenciam metadados SQLite. Reclassificação de snapshots com mais de 900 segundos como `stale_snapshot`. Importação nunca autoriza execução remota, não abre portas nem grava credenciais.

Evidência de laboratório existente: 0.1.4 `workers local`, `models benchmark` e `models running` homologados com Qwen2.5-Coder 3B e RTX 3060 Ti, descrita em `docs/evidence/2026-11-22-ia01-qwen25-coder3b-benchmark.md`. Novos testes de 0.1.5 foram escritos e versionados; execução completa do CI, o instalador 0.1.5 no LXC e importação real de segundo worker permanecem pendentes.

NÃO implementado: registro remoto autenticado, heartbeat/TTL de conectividade real, job scheduler, sincronização de modelos, invocação de APIs externas, gerenciamento de serviços nos workers, mTLS/PSK e quotas distribuídas. O cadastro não deve ser representado como autorização de tráfego ou cluster funcional.


## DevHub 0.1.5.1 — hotfix SQLite no comando workers show

Operador confirmou `workers enroll-local --id ia-01 --confirm-enroll` e `workers list` funcionando (worker IA-01, 2 modelos, 1 GPU, snapshot recente). O comando `workers show ia-01` falhou com `sqlite3.ProgrammingError: Error binding parameter 2: type 'dict' is not supported`. Causa: `worker_registry.show` devolvia objeto em `out['status']`, e `main` encaminhava o dicionário para a coluna TEXT da tabela de auditoria. A resposta agora usa `status: ok` e `worker: {...}`; a camada comum de auditoria normaliza estados não-textuais para `ok`. Dois testes de regressão reproduzem o comando com SQLite real em memória temporária e protegem contra regressões futuras. Release identificada como 0.1.5.1 em `devhub --version`, apenas na branch de laboratório. **Não requer recriação do banco ou cadastro já existente**. Execução da suíte no LXC ainda pendente.


## Validação de testes 0.1.5.1 — IA-01

O operador confirmou que `python3.12 -m unittest discover -s tests -v` terminou com `OK` no laboratório. Isso valida a suíte de testes disponível na árvore de trabalho do IA-01, conforme relato do operador; quantidade exata e execução no GitHub Actions não foram informadas. **A execução pós-hotfix de `devhub workers show ia-01` ainda não foi demonstrada neste registro**. A raiz do checkout no contêiner é **`/software/devhub`** (não `/root/software/devhub`); utilizar esse caminho nos próximos comandos. A instalação global em `/opt/devhub` e o estado em `/var/lib/devhub` são caminhos distintos e não foram alterados por essa correção documental.

## IA-01: Worker Registry 0.1.5.1 homologado

O operador confirmou `devhub --version` retornando `0.1.5.1` e `devhub workers show ia-01` retornando `status: ok` sem exceção SQLite. O manifesto cadastrado é `schema=1`, `worker_id=ia-01`, `hostname=IA-01`, arquitetura `x86_64`, Ollama `0.40.17`, modelos `qwen2.5-coder:3b` e `qwen3:4b`, GPU `NVIDIA GeForce RTX 3060 Ti` (8192 MiB, driver 620.73.04). Snapshot `observed_at=2026-11-23T01:18:05.242914+00:00`, `age_seconds=382`, `freshness=recent_snapshot`, `remote_execution=disabled`, `trust=metadata_only_unverified`. A suíte `python3.12 -m unittest discover -s tests -v` foi relatada como OK anteriormente. Conclusão: worker registry local, persistência do snapshot, auditoria de texto e consulta `show` homologados; sem comprovação de comunicação remota ou identidade autenticada. Checkout `/software/devhub`.


## Identidade criptográfica para Worker Manager — branch de segurança

Após confirmação do operador, o DevHub 0.1.5.1 foi homologado no IA-01: `workers show ia-01` devolveu `status: ok`, manifesto com 2 modelos e RTX 3060 Ti 8 GiB; testes unitários completos reportados `OK`. Documento de arquitetura mTLS iniciado em `docs/adr/0001-worker-mtls.md`, código experimental `worker_mtls.py` e testes `tests/test_worker_mtls.py` na branch `feat/worker-mtls-security-foundation`, derivada da 0.1.5.1. O código exige TLS 1.3, certificados dos dois lados, SAN por worker e fingerprint aprovado por operador, e só autoriza metadados de inventário/saúde.

**Este código não possui listener, servidor, cliente nem integração ativa com DevHub CLI; não está homologado em rede e não deve ser instalado em produção.** Nenhum firewall, Ollama, driver, porta, certificado ou segredo foi modificado. Execução dos novos testes TLS no IA-01 e integração real mTLS permanecem pendentes. Cadastro de snapshots continua sem autenticação.


## Hotfix mTLS — correção da política remote_execution em 2026-11-22

No IA-01, o operador executou `python3.12 -m unittest discover -s tests -p 'test_worker_mtls.py' -v`: 14 testes, 12 OK e 2 FAIL (`test_post_handshake_peer` e `test_valid_pinned_identity_only_allows_inventory`). Causa: `verify_worker_identity` devolvia string `remote_execution: 'disabled'` enquanto a autorização exigia booleano `remote_execution is False` e um teste esperava `False`. Corrigido `worker_mtls.py` para emitir booleano `False` nas identidades mTLS; registros passivos do worker existentes continuam usando texto e seguem sem autoridade. Adicionado teste de regressão rejeitando valor textual `'disabled'`, numérico 0 e booleano True na autorização. Nenhuma porta, certificado ou serviço alterado. **A correção ainda aguarda resultado da suíte no IA-01**; tentativa de executar no ambiente de desenvolvimento via clone GitHub indisponível por DNS.


## Teste de handshake mTLS real em loopback — branch 0.1.6 experimental

O operador concluiu **15/15 testes unitários da política mTLS no Rocky IA-01** (`python3.12 -m unittest discover -s tests -p 'test_worker_mtls.py' -v` com OK). Derivada a branch `feat/worker-mtls-loopback-0.1.6` da `feat/worker-mtls-security-foundation`. Criados `tests/test_worker_mtls_loopback.py`: testes de integração com OpenSSL emitindo CA, servidor e certificados de worker temporários com EKUs e SANs explícitos; socket apenas em `127.0.0.1` com porta do kernel, TLS 1.3, pin SHA256 e checagem da política somente de leitura. Oito cenários (1 aceitação, 7 recusas) **8/8 OK** em Python 3.13.5/OpenSSL 3.5.5 de desenvolvimento; CI passa a exigir `openssl version` para não ignorar testes silenciosamente. **Não há ainda comprovação desta nova suíte no Rocky IA-01** nem teste de rede entre hosts. Nenhum daemon, serviço, token, PKI persistente, download ou configuração de firewall ativados. DevHub instalado no IA-01 permanece 0.1.5.1.


### CI confirmado para a branch de handshake real

GitHub Actions `tests` executou no commit `5249948a0999047a7b7d2f3a02bd842b6c66cbb2`, run #161 / ID `45097214967`, no Ubuntu runner com Python 3.12.16: **111 testes, OK**. Os oito casos reais de `test_worker_mtls_loopback` aparecem como `ok`, sem skip, e a etapa `bash -n` passou. O executável OpenSSL também foi verificado. CI: https://github.com/pastrello/devhub/actions/runs/45097214967 . Ainda é obrigatório testar o mesmo cenário no IA-01 Rocky 9 antes de aprovar o transporte para rede interna.

## Decisão de laboratório — IA-01 como coordenador e worker (2026-11-22)

O operador confirmou no IA-01: OpenSSL **3.5.9** (29/09/2026), Python 3.12 e **8/8 testes de handshake mTLS real em loopback OK** (`Ran 8 tests in 0.094s`), abrangendo identidade válida, ausência de certificado, CA inválida, SAN inválida, pin inválido, hostname incorreto e TLS 1.2. Também informou ter iniciado a suíte completa `python3.12 -m unittest discover -s tests -v`, mas **não informou a linha final/total dessa execução**, portanto não atribuir resultado a ela ainda. No GitHub Actions houve `111 tests OK` no commit anterior; isso é evidência de CI, não da execução completa no Rocky.

**Decisão explícita:** utilizar **somente o contêiner IA-01** (`/software/devhub`) como laboratório de coordenador e workers simulados em processos/sockets locais, com loopback `127.0.0.1` e isolamentos de estado/credenciais de teste. Não pedir nem provisionar novos LXCs, GPUs, instalações do Ollama ou dependências no Proxmox neste momento. A instalação operacional do DevHub permanece `0.1.5.1`; usar branch experimental apenas no checkout para testes. Nenhuma porta não-loopback, serviço de rede persistente ou API Ollama externa sem autorização.

Aumentar RAM/disco **apenas se medição demonstrar necessidade** (uso real, dados, logs, modelos, contextos e picos), preservando snapshot e checando cgroups/LXC e espaço do Ollama/DevHub antes de alterar recursos. Não presumir que o laboratório com uma GPU simula paralelismo real de vários nós.

**Marco para recomendar novos contêineres**: protocolo de inventário autenticado com framing/limites, integração local coordenador↔worker real, testes negativos para replay/revogação/rotatividade, TLS e hostname verificados fim a fim, documentação de instalação por função, ausência de exposição do Ollama, benchmark/limites dimensionados, rollback seguro, CI e IA-01 aprovados. Somente então apresentar ao operador proposta concreta de separar coordenador (sem GPU obrigatória) e workers de inferência (GPU opcional por função), tamanhos de RAM/disco dimensionados por métricas, rede e firewall, instalação automatizada e modelos recomendados; solicitar aprovação antes de mudanças. Manter Issue #5 como controle desse marco.
