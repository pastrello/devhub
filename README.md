# DevHub 0.1.0 (PoC)

**Local first. Subscription first. Pay-per-use last.**

Orquestrador independente de recursos de IA. A primeira entrega valida o núcleo local; não é um agente autônomo de edição de código nem um serviço de produção. Orçamento adicional cloud: US$ 0; nenhuma assinatura ou crédito é adquirido.

## Instalação e primeiro teste

Requisitos: Linux, usuário não root, Python 3.12 ou superior, Git e uma instalação Ollama própria para inferência. Rocky 9/10 são alvos de homologação, ainda não certificados.

```bash
git clone https://github.com/pastrello/devhub.git
cd devhub
bash install.sh
export PATH="$HOME/.local/bin:$PATH"
devhub --version
devhub doctor
devhub discover
devhub catalog
devhub costs
```

O instalador não instala dependências de sistema, clientes comerciais, PostgreSQL nem serviços. Para outro executável Python >= 3.12: PYTHON_BIN=python3 bash install.sh.

Ollama remoto, somente em host confiável e autorizado (não exponha a API à internet):

```bash
export DEVHUB_OLLAMA=http://192.168.1.50:11434
devhub discover
```

Substitua o endereço de exemplo. Em produção use rede privada e transporte protegido. Alternativamente, use --ollama antes do subcomando. Não coloque credenciais na URL.

Escolha um tag realmente instalado, local e validado pelo administrador. Exemplo:

```bash
devhub --approve-local qwen2.5-coder:7b plan "Explique um índice PostgreSQL"
devhub --approve-local qwen2.5-coder:7b run "Explique um índice PostgreSQL" --trust-local-endpoint
```

--trust-local-endpoint confirma que o operador verificou que o endpoint faz inferência local, não roteia para cloud. O DevHub não pode comprovar isso por um nome de modelo. Não use dados confidenciais no argumento: ele pode aparecer no histórico e na lista de processos. A seleção inicial é determinística (ordem alfabética entre tags aprovados), não um benchmark. Tarefas avançadas em modo auto exigem revisão.

Download explícito de modelo local, após verificar licença, origem, hardware e espaço:

```bash
devhub pull qwen2.5-coder:7b --confirm-download
```

LiteLLM opcional: export DEVHUB_LITELLM=http://127.0.0.1:4000; devhub discover. Apenas GET /v1/models sem autenticação na PoC; não desative a autenticação de um gateway existente. Chamadas de inferência LiteLLM ficam bloqueadas. Não há fallback pago.

## Testes

```bash
python3.12 -m unittest discover -s tests -v
bash -n install.sh
```

13 testes unitários executados em Python 3.13.5, com mocks para inferência; sem teste em Rocky, GPU real ou contas comerciais. Estado SQLite em ~/.local/state/devhub (DEVHUB_STATE ou --state para alterar). Logs registram ação/status, não prompts. O comando discover grava um snapshot de inventário, não uma sincronização de catálogos públicos.

Veja ARCHITECTURE.md, PROJECT-STATE.md, ROADMAP.md, SECURITY.md e AGENTS.md antes de contribuir.

## Laboratório Proxmox VE 9 / Rocky Linux 9 LXC / RTX 3060 Ti

Novo guia experimental: [docs/proxmox-rocky9-ollama.md](docs/proxmox-rocky9-ollama.md). Inclui bootstrap administrativo opcional de Ollama em [scripts/bootstrap-ollama-lxc.sh](scripts/bootstrap-ollama-lxc.sh), sem modificar drivers NVIDIA. Uso normal do DevHub permanece sem root. O bootstrap não foi executado no LXC real; confira as permissões dos dispositivos e teste a GPU com um modelo pequeno.
