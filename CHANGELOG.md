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
