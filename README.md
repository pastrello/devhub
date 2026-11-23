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


## DevHub 0.1.3 — pré-verificação oficial e instalação supervisionada

A novidade é a consulta **somente leitura** do manifesto do registro oficial do Ollama para obter os tamanhos de camadas, com aprovação separada para instalação. A busca do Hugging Face continua informativa, **sem importar modelos arbitrários**.

No laboratório Rocky Linux 9 LXC, após `git fetch` e mudar para `feat/registry-preflight-0.1.3`, executar `bash install-system.sh --check` e `bash install-system.sh --install` para atualizar de 0.1.2 para 0.1.3.

Antes do comando abaixo, confirme em qual filesystem o Ollama realmente armazena modelos com `df -T /var/lib/ollama/models /var/lib`. O usuário `devhub` pode não ter permissão para verificar diretamente `/var/lib/ollama/models`; **não altere permissões por isso**. Se ambos estiverem no mesmo filesystem, utilize o diretório legível `/var/lib` para estimar espaço, deixando claro que a estimativa não considera cotas específicas.

```bash
devhub --version
devhub models online "qwen coder" --limit 5
devhub models preflight qwen2.5-coder:3b --storage-path /var/lib
```

O `preflight` consulta `https://registry.ollama.ai/v2/library/...`, exige um manifesto com camadas locais de pesos e guarda o hash do manifesto no estado SQLite com validade de uma hora. Exibe os bytes estimados de download, espaço disponível e avisos sobre licença e GPU. Não instala nem altera modelos.

Depois de avaliar a licença em sua fonte oficial, confirmar que a API Ollama usa inferência local e aprovar o consumo de disco:

```bash
devhub models install qwen2.5-coder:3b \
  --confirm-download --license-reviewed --trust-local-endpoint
devhub models test qwen2.5-coder:3b --trust-local-endpoint
devhub models running
```

A instalação reconsulta o manifesto, bloqueia se o hash mudou, verifica o espaço e só então chama a API Ollama para baixar o modelo. O endpoint deve ser loopback; a instalação em workers remotos exigirá um protocolo autenticado. O modelo deve aparecer na lista do Ollama depois do download.

**Limitações:** para evitar escolhas incorretas de runner, o pré-verificador recusa listas de manifestos multi-plataforma; nesse caso não instala e indica que a resolução do manifesto precisa ser implementada. O pré-verificador não consegue comprovar licença, adequação CUDA, custo de energia, quantização ou integridade do modelo efetivamente instalado. Tags podem ser mutáveis, inclusive entre uma checagem e o download final. O fluxo histórico `models pull` continua disponível apenas para o catálogo curado; para novos modelos, utilize `preflight` e `install`.

Nenhuma compra, login, integração cloud paga, atualização do Ollama ou instalação em outros contêineres é realizada automaticamente.

Referências: https://registry.ollama.ai/ , https://docs.ollama.com/api/pull , https://docs.ollama.com/api/tags .


## DevHub 0.1.4 — assistente interativo, worker local e benchmark

Versão de laboratório. O Ollama Qwen2.5-Coder 3B foi testado pelo operador no IA-01 com resposta OK e `runner_size_vram_bytes=2163568803` no retorno de teste, GPU NVIDIA 3060 Ti 8 GiB. A consulta `models running` posterior estava vazia, o que **não é erro**: segundo o Ollama os modelos são descarregados quando seu `keep_alive` expira (padrão de 5 min). A medição anterior **não garante** permanência do modelo nem 100% de offload, pois relata apenas memória associada ao runner.

### Atualização em IA-01

```bash
cd /root/software/devhub
git fetch origin
git switch feat/local-worker-benchmark-0.1.4
bash install-system.sh --check
bash install-system.sh --install
devhub --version
```

Comandos novos:

```bash
devhub wizard
devhub workers local
devhub models benchmark qwen2.5-coder:3b --trust-local-endpoint --keep-alive 5m
devhub models running
devhub catalog
```

`wizard` abre um menu interativo português: inventário, modelos instalados, pesquisa no catálogo interno, pré-verificação de um modelo e teste explicitamente confirmado. Ele não executa automaticamente downloads, instala motores ou ativa nuvem. O CLI continua a interface principal para homologação, e uma interface web vem depois.

`workers local` gera snapshot local de hostname, arquitetura, GPU, motor e modelos. **Não** abre porta, não registra outro LXC e não distribui tarefas.

`models benchmark` executa **um teste curto** com prompt fixo sobre índices SQL, contexto de 4096, até 64 tokens de resposta, `keep_alive` finito permitido (`0`, `1m`, `5m`, `10m`) e consulta imediatamente `/api/ps`. O relatório inclui tempos de carregamento e geração, velocidade aproximada em tokens/s, memória de GPU, prazo de expiração quando informado e inventário de GPU. O resultado fica salvo no SQLite em `benchmark:<tag>`. Não é comparação estatisticamente válida entre modelos, pois não faz aquecimento/repetições independentes nem controla cargas concorrentes.

`models running` pode estar vazio se o modelo foi descarregado, mesmo após teste bem-sucedido. Para verificar um modelo sem esperar, execute imediatamente após `benchmark`.

**Segurança:** benchmark restringe-se a um endpoint Ollama de loopback e exige `--trust-local-endpoint`; servidores remotos requerem controle de acesso futuro. Não armazene prompts confidenciais nos argumentos nem permita API do Ollama exposta na Internet. O benchmark não registra valores brutos de prompt do usuário.

Referência: https://docs.ollama.com/api/generate e https://docs.ollama.com/api/ps .


## 0.1.5 — Registro passivo de workers (branch de laboratório)

A nova versão permite armazenar **inventários** de outros LXCs ou máquinas sem conceder acesso remoto a nenhum deles. Não há SSH, API de agente, heartbeat automático, chave ou credencial: **apenas metadados**. Os registros podem ser importados manualmente e nunca autorizam execução de tarefas ou downloads em outro host.

No IA-01, após atualizar para `feat/worker-registry-0.1.5` e rodar novamente `bash install-system.sh --install`, o CLI deverá informar `devhub --version = 0.1.5`.

### Worker local

```bash
devhub workers local
devhub workers snapshot --id ia-01
devhub workers enroll-local --id ia-01 --confirm-enroll
devhub workers list
devhub workers show ia-01
```

O ID é uma etiqueta definida pelo operador, usando letras minúsculas, números e hífens. O `snapshot` apenas imprime JSON e não registra o worker. `enroll-local` coleta uma foto do estado e registra o metadado no SQLite do DevHub. Para substituir um registro existente, acrescente `--replace` conscientemente.

### Outro LXC sem rede de administração

No outro host que tenha DevHub instalado, gere um snapshot:

```bash
devhub workers snapshot --id ia-02 > /tmp/ia-02.json
```

Transfira o JSON pelo método administrativo que você já usa e, no IA-01:

```bash
devhub workers import-file /CAMINHO/ia-02.json --confirm-import
devhub workers list
devhub workers show ia-02
```

O arquivo pode conter hostname, plataforma, nome/versão do motor, tags de modelos e dados de GPU; **não** contém endereço IP de agente, tokens ou chave. Isso não autentica a origem: um JSON copiado pode ser falso. Trate como informação informada pelo operador, nunca como heartbeat ou worker remoto confiável.

Snapshots com mais de **15 minutos** serão apresentados como `stale_snapshot` e não serão atualizados automaticamente. Registros estão limitados em tamanho e validação de campos. A importação rejeita campos extras (como `endpoint`, `token` e `command`), nomes inválidos, arquivos grandes e links simbólicos.

Para apagar apenas o registro local:

```bash
devhub workers forget ia-02 --confirm-forget
```

Isso **não** toca no host de origem e não remove modelos. O próximo passo será estabelecer identidade e comunicação autenticada entre workers, em uma implementação independente e auditável.

Teste de regressão: `python3.12 -m unittest discover -s tests -v`. O novo módulo possui 16 testes de segurança e operações; GitHub Actions e a execução real da versão 0.1.5 no LXC ainda precisam ser verificados.


### Permissões de importação em instalação global

`devhub` executa como usuário `devhub`, mesmo quando chamado por root. Se o JSON foi copiado para um diretório acessível somente a root, copie-o para a área privada do aplicativo sem expor seus metadados:

```bash
install -o devhub -g devhub -m 600 /root/ia-02.json /var/lib/devhub/ia-02.json
devhub workers import-file /var/lib/devhub/ia-02.json --confirm-import
```

Não aplique `chmod 777` em diretórios de sistema. O arquivo do inventário contém nomes de máquinas, modelos e dados de hardware; mantenha-o privado.
