# IA-01 — Qwen2.5-Coder 3B: DevHub 0.1.4

Data do benchmark: 2026-11-23T01:02:05.229862Z (2026-11-22 22:02:05 America/Sao_Paulo). Evidência encaminhada pelo operador; não é teste executado por CI.

## Plataforma
- Host: IA-01, LXC Rocky Linux 9 no Proxmox VE 9; arquitetura x86_64.
- GPU: NVIDIA GeForce RTX 3060 Ti, 8192 MiB; driver 620.73.04.
- Ollama: 0.40.17.
- Modelos instalados: `qwen2.5-coder:3b`, `qwen3:4b`.
- Modelo testado: `qwen2.5-coder:3b`, GGUF, família qwen2, 3.1B parâmetros, Q4_K_M, contexto 4096.

## Teste confirmado
Comando:
```bash
devhub models benchmark qwen2.5-coder:3b --trust-local-endpoint --keep-alive 5m
```

Resultado:
- status: ok; resposta da inferência em português sobre índices SQL.
- duração total: 2,6702 s; carregamento: 2,2583 s.
- prompt: 49 tokens, 554,98 tokens/s.
- resposta: 36 tokens, 112,73 tokens/s.
- tamanho do modelo informado pelo Ollama: 2.163.568.803 bytes;
- tamanho em VRAM informado: 2.163.568.803 bytes.
- GPU: memória livre 5615 MiB após inferência (7845 MiB livres em consulta anterior).
- residency: currently_loaded=true; expires_at=2026-11-23T01:07:05.167189158Z.

Confirmação imediatamente após teste:
```text
devhub models running
name=qwen2.5-coder:3b size=2163568803 size_vram=2163568803 context_length=4096 runner=llamacpp
```

## Interpretação
Inferência via DevHub e Ollama com modelo reportado inteiramente na VRAM, com dados de desempenho de uma medição curta. `size_vram == size` não mede diretamente utilização de compute GPU ou a proporção das operações realizadas em CUDA. `running` vazio observado anteriormente é consistente com descarregamento posterior por política `keep_alive`. Resultado bom, ainda não constitui benchmark reproduzível com repetição/aquecimento e carga controlada.

## Consequências
- Homologação de `devhub workers local`, `models benchmark` e `models running` no laboratório IA-01.
- O wizard da 0.1.4 não foi confirmado nessa evidência.
- Próximo passo: registro de inventário de múltiplos workers sem comunicação de rede; autenticação e execução remota seguem fora do escopo.
