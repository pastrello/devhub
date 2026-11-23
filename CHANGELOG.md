# Changelog

## 0.1.0 — initial PoC

- Bootstrap CLI, local Ollama inventory and inference, explicit model download.
- CLI binary discovery, optional LiteLLM inventory, SQLite audit.
- Default-deny cloud execution; no automatic spending.
- 13 unit tests (mocked inference), Bash syntax check.
- No live integration, release tag, or production readiness claim.

## 0.1.1 — Engine Manager PoC (branch de laboratório)

- Catálogo curado de motores e modelos; busca por tarefa e estimativas limitadas de VRAM.
- Descoberta NVIDIA via nvidia-smi; inspeção, execução de teste e gestão explícita no Ollama.
- `devhub engines`, `devhub models`, `devhub gpu`.
- Instalador global `install-system.sh`: somente instalação root, runtime usuário devhub, releases e rollback.
- API cloud permanece bloqueada (orçamento adicional zero).
- 29 testes unitários com mocks; homologação real no LXC ainda pendente.


## 0.1.2 — official model discovery (test branch)

- Added Hugging Face read-only search (`models online`) and official GitHub release lookup (`engines releases`).
- Added `models fit` for conservative, clearly qualified GPU/disk sizing estimates on curated Ollama tags.
- Snapshots of discovery and release metadata persist to SQLite.
- Security: allowlisted public HTTPS APIs, no arbitrary URLs, no credentials/redirects, size and timeout bounds.
- No automatic model imports from Hugging Face, no cloud billing, no engine upgrades.
- 41/41 development unit tests passed; live-network/LXC version 0.1.2 testing pending.


## 0.1.3 — Registry preflight and supervised model acquisition (unmerged lab branch)

- Added official Ollama registry manifest inspection with digest/size checks and disk reserve estimates.
- New CLI commands: `models preflight` and `models install` with review gate and 1-hour expiry.
- Registry fingerprint must remain unchanged, download must be explicitly approved, and Ollama endpoint must be loopback for automated install.
- Fail-closed on unsupported manifest-list schema, unknown license or capacity problems; licensed review remains human.
- No commercial services, cloud calls for inference or automatic infrastructure modifications.
- 15 registry parser tests executed locally; CLI regression CI requested, and real Rocky LXC test pending.


## 0.1.4 — local worker diagnostics and interactive assistant (lab branch)

- Local worker status: OS/architecture/GPU/Ollama models.
- Bounded synthetic Ollama benchmark, token timings, VRAM residency, finite keep_alive, SQLite evidence.
- Interactive wizard for safe discovery, preflight and local model tests.
- Cloud costs and remote execution remain disabled; new tests added for blocking unauthorized operations.
- Lab homologation and CI confirmation pending.


## 0.1.5 — passive multi-worker inventory (lab branch)

- Snapshot export and explicit SQLite registry of local or manually imported worker inventories.
- Strict metadata-only schema; limits for size/IDs/GPUs/models; 15-minute stale classification.
- CLI `workers snapshot|enroll-local|import-file|list|show|forget`.
- No automatic enrollment, remote connection, credentials, downloads or task execution.
- New unit tests for rejection of malicious manifests, freshness and explicit approval.


## 0.1.5.1 — correção workers show e auditoria

- Corrigido `workers show ID`: retorno JSON inclui `status: "ok"` e estrutura descritiva em `worker` e `manifest`.
- Padronizada auditoria para gravar um estado textual no SQLite, evitando exceção ao receber estruturas JSON.
- Acrescentados dois testes de regressão que reproduzem falha real em `sqlite3.ProgrammingError`.
- O cadastro de workers e os arquivos SQLite existentes são preservados no upgrade via `install-system.sh --install`.
- Homologação de integração no IA-01 e execução completa da suíte pendentes.


### Homologação da suíte no IA-01

O operador confirmou `python3.12 -m unittest discover -s tests -v` encerrando com `OK`. Ajustado caminho de checkout nos exemplos para `/software/devhub`. Execução específica de `workers show` após a correção e status do GitHub Actions ainda não foram fornecidos.


## Worker mTLS foundation — experimental (no release)

- Added `worker_mtls.py`: construction of TLS 1.3 contexts requiring mutual certificates, validation of approved worker DNS SAN and SHA256 certificate fingerprint, and inventory/health-only authorization policy.
- New `tests/test_worker_mtls.py` covers negative identity/TLS cases and permissions; no live network test run or listener added.
- ADR-0001 documents rollout and security gates. Operational version remains 0.1.5.1.
