# DevHub 0.1.1 (Engine Manager PoC)

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


## Falha no laboratório: llama-server não encontrado

Se `ollama run` reportar `llama-server binary not found`, não é necessário apagar o modelo. Na branch de laboratório, use `bash scripts/repair-ollama-lxc.sh --check`, confira `/usr/lib/ollama/llama-server` e, após snapshot, `bash scripts/repair-ollama-lxc.sh --repair`. O reparo só altera a instalação depois de verificar que o pacote oficial contém o runtime de inferência. Consulte [guia do laboratório](docs/proxmox-rocky9-ollama.md).

## Engine Manager 0.1.1 (branch de laboratório)

O Engine Manager disponibiliza um catálogo **curado e offline** de motores e modelos pequenos, descoberta de GPU via `nvidia-smi`, inventário de modelos instalados no Ollama, inspeção, teste de inferência e gestão supervisionada. **Não** equivale ainda à pesquisa dinâmica da Internet nem instala automaticamente qualquer motor.

### Instalação simplificada para root no Rocky Linux 9 LXC

Faça snapshot do LXC antes de atualizar. Na branch `feat/lxc-rocky9-ollama-lab`:

```bash
cd /root/software/devhub
git pull --ff-only
bash install-system.sh --check
bash install-system.sh --install
devhub --version
```

O instalador administrativo é executado como root, instala o programa em `/opt/devhub`, cria usuário/grupo isolados `devhub`, mantém releases anteriores e fornece rollback via `bash install-system.sh --rollback`. **Mesmo quando chamado pelo root, o comando `devhub` do sistema executa sob o usuário sem privilégios.** Não instala Ollama, altera drivers nem compra serviços.

Caso não queira a instalação global, use o instalador por usuário `bash install.sh` fora da conta root.

### Primeiros comandos

```bash
devhub engines list
devhub engines status
devhub engines install ollama    # Apenas instruções, não altera serviços
devhub gpu
devhub models installed
devhub models running
devhub models search coder
devhub models recommend --task coding
devhub models inspect qwen3:4b
devhub models test qwen3:4b --trust-local-endpoint
devhub costs
```

### Baixar um modelo local autorizado

Confirme a licença, o nome do modelo, o consumo de disco, o endereço de Ollama e as limitações do hardware:

```bash
devhub models pull qwen2.5-coder:3b --confirm-download --trust-local-endpoint
```

A primeira versão aceita downloads via Engine Manager **somente dos tags da lista curada**, e não de nomes arbitrários retornados por fontes não confiáveis. O tamanho do download é aproximado; o Ollama e suas dependências podem utilizar mais espaço. A verificação opcional `--models-dir /CAMINHO` consulta o espaço livre em um diretório existente que o usuário devhub consiga acessar, mas não comprova que ele corresponde ao storage real do Ollama.

Exclusão de modelos:

```bash
devhub models delete qwen2.5-coder:3b --confirm-delete --trust-local-endpoint
```

A API é inicialmente considerada não confiável para execução de modelos até que você confirme que o endpoint não encaminha pedidos para um provedor cloud. Endpoints em outra máquina exigem transporte privado/criptografado; **não exponha a API não autenticada do Ollama à Internet**.

### Limitações conhecidas

- Busca de modelos na Internet ainda não implementada; catálogo embutido com referência à fonte oficial.
- Compatibilidade de VRAM é aproximação baseada no tamanho dos pesos; **não é teste de desempenho nem garantia de execução GPU**.
- O instalador de motores via CLI fornece instruções, mas instalação efetiva continua no bootstrap administrativo supervisionado.
- LiteLLM é somente inventário, sem inferência cloud.
- Nenhum modelo/componente foi baixado pelo Engine Manager durante os testes automatizados, que utilizam mocks. Inferência Qwen3 4B foi demonstrada manualmente pelo operador no LXC.

Referências de API: [Ollama API](https://docs.ollama.com/api), [Biblioteca Ollama](https://ollama.com/library).


## DevHub 0.1.2 — pesquisa online e planejamento de modelos

Esta etapa adiciona **descoberta de metadados públicos**, sem criar assinaturas ou consumir APIs de inferência pagas. A busca online consulta diretamente a API pública oficial do Hugging Face; não equivale a pesquisar os tags instaláveis do Ollama. Não insira nomes de projetos confidenciais nas consultas: o termo é enviado ao provedor externo e fica salvo no catálogo SQLite privado.

Comandos após atualizar a branch e executar novamente o instalador:

```bash
cd /root/software/devhub
git fetch origin
git switch feat/model-discovery-0.1.2
bash install-system.sh --check
bash install-system.sh --install
devhub --version
devhub models online "qwen coder" --limit 10
devhub engines releases --engine ollama
devhub models fit qwen2.5-coder:3b
devhub models search coder
devhub catalog
devhub costs
```

- `models online`: consulta a API pública do Hugging Face e salva um snapshot no catálogo. Cada resultado traz ID, URL oficial, licença disponível, indicação de acesso restrito e pistas sobre GGUF; o resultado **não** constitui um tag Ollama e **não** libera instalação automática. Nenhum arquivo/modelo é baixado nessa operação.
- `engines releases --engine ollama|llama.cpp|litellm|vllm`: consulta metadados da última *release* no GitHub oficial; não baixa nem atualiza o motor. A tag mais recente não significa compatibilidade ou estabilidade comprovada no LXC.
- `models fit TAG`: estima a relação entre pesos do catálogo curado e VRAM livre, reservando 1 GiB para custos adicionais. Não comprova execução GPU. Use `--models-dir CAMINHO` apenas quando souber qual é o diretório de armazenamento acessível.
- `devhub catalog`: mostra snapshots persistidos; pesquisas anteriores permanecem disponíveis localmente.
- `models pull`: continua exigindo `--confirm-download --trust-local-endpoint` e somente aceita tags curados. Não é possível instalar diretamente um resultado do Hugging Face.

O tráfego HTTPS de metadados utiliza somente `huggingface.co/api/models` e `api.github.com/repos/.../releases/latest`, com limite de tamanho, sem redirecionamento ou uso de credenciais. Um proxy corporativo exigido pela rede poderá impedir a consulta; nesse caso o catálogo offline continua funcional.

Testes de desenvolvimento: **41/41 unitários**, sem integração externa ao vivo (internet indisponível no ambiente de testes). Nenhuma operação real de download, pagamento ou upgrade realizada. Os testes de integração com seu Rocky 9 ainda precisam de homologação.

Fontes: https://huggingface.co/docs/huggingface_hub/en/package_reference/hf_api e https://docs.ollama.com/api
