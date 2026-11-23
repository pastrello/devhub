# Task #001 — Validação de identificadores de workers

Data da avaliação: 2026-11-22 (relato do operador). Laboratório IA-01, DevHub 0.1.5.1 operacional, modelo `qwen2.5-coder:3b` via Ollama. Nenhum arquivo de projeto foi criado/modificado pelo comando; esta é a primeira tarefa de geração livre de texto/código, não uma execução automatizada do código.

## Prompt enviado ao DevHub

```bash
TASK='Escreva uma função Python 3.12 que valide IDs de workers. Aceite somente letras minúsculas, números e hífens, com até 63 caracteres. Inclua três testes unittest. Retorne apenas o código.'

devhub --approve-local qwen2.5-coder:3b run "$TASK" --provider ollama --trust-local-endpoint
```

Resposta do DevHub: `status=ready`, `provider=ollama`, `model=qwen2.5-coder:3b`, campo `response` com bloco Markdown de código Python. Isso comprova seleção autorizada do modelo e inferência via CLI, **não** qualidade do código.

## Código principal gerado (transcrito do retorno)

```python
import unittest

def validate_worker_id(worker_id: str) -> bool:
    # Verifica se o ID contém apenas letras minúsculas, números e hífens
    if not worker_id.isalnum() or worker_id.count('-') > 1:
        return False
    if len(worker_id) > 63:
        return False
    return True
```

Testes gerados: dois métodos `test_valid_worker_id` e `test_invalid_worker_id`, não três. Entre os supostamente válidos figuram `john-doe-123` e `jane.doe-456`; entre os supostamente inválidos figura `123-456-7890`.

## Avaliação estática (sem executar o código gerado)

**Execução do comando DevHub: sucesso. Qualidade da solução: reprovada.**

1. `str.isalnum()` rejeita hífens, portanto rejeita `ia-01`, `john-doe-123` e `bob456-789` indevidamente.
2. `count('-') > 1` rejeita IDs com múltiplos hífens que são aceitos pela regra do Worker Registry.
3. `jane.doe-456` contém ponto, proibido pela regra; o código gerado o inclui no grupo de IDs válidos.
4. `ABC` poderia ser aceito por `isalnum()` embora maiúsculas não sejam permitidas.
5. O prompt exige três testes, mas o modelo entregou apenas dois métodos.
6. O padrão efetivo no repositório é `^[a-z0-9][a-z0-9-]{0,62}$` em `worker_registry.py`; todos os critérios devem se alinhar com ele.

A resposta ainda não foi submetida a um executor isolado. Não relatar esses defeitos como falhas comprovadas em execução unittest: são conclusões lógicas da leitura do código. A solução correta usa `re.fullmatch(r'[a-z0-9][a-z0-9-]{0,62}', worker_id)` após conferir tipo.

## Lições para o Task Manager

- Separar `status=ready` (provedor disponível) de `task_execution_status`, `tests_passed` e `acceptance_status`.
- Não tratar resposta textualmente plausível como código aceito.
- Quando testes forem gerados pela própria IA, confrontá-los com critérios e casos adversariais independentes, não só com o código produzido.
- Em versões posteriores, extrair código apenas em sandbox temporário, executar testes com timeout e limites de CPU/RAM, sem rede, sem privilégios nem segredos, registrar artefatos, retornar ao modelo os erros para uma tentativa controlada; revisão humana antes de commit.
- Manter o laboratório coordenador + worker no IA-01 até o protocolo autenticado e a execução isolada serem homologados.

Status: evidência para definição do Task Manager; **nenhuma execução de código arbitrário pela versão atual**.
