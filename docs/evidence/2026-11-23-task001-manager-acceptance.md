# DevHub Task Manager 0.1.7-lab — evidência de regressão da Tarefa #001

Data: 23/11/2026. Repositório: pastrello/devhub. PR #11, Issue #10.

## Incidente original

No IA-01 o operador executou `devhub --approve-local qwen2.5-coder:3b run "$TASK" --provider ollama --trust-local-endpoint`, recebendo `status: "ready"` e texto de código Python. A resposta, copiada para `tests/fixtures/task001-original.json`, não cumpre o contrato de IDs do Worker Registry:

- `str.isalnum()` rejeita hífens, invalidando `ia-01`;
- `count('-') > 1` rejeita IDs com vários hífens;
- o teste gerado considera `jane.doe-456` válido, embora pontos sejam proibidos;
- letras maiúsculas poderiam passar pela lógica de `isalnum()`;
- o prompt exigia três métodos `unittest`, mas foram escritos dois.

A função oficial do DevHub em `worker_registry.py` valida o padrão `^[a-z0-9][a-z0-9-]{0,62}$` (1–63 caracteres, primeiro alfanumérico minúsculo).

## Resultado do avaliador estático

A regra versionada `worker-id-validator-v1` exige uma função `validate_worker_id`, regex de ID da registry, uso de `fullmatch` e pelo menos três testes `unittest`. A fixture original deve produzir:

```json
{
  "status": "evaluated",
  "task": {
    "id": "task-001",
    "provider_status": "not_checked",
    "task_status": "response_received",
    "acceptance_status": "acceptance_failed",
    "generated_code_executed": false
  },
  "assessment": {
    "static_status": "failed",
    "tests_executed": false
  }
}
```

Este bloco é **expectativa resumida**, não transcrição de uma execução real do CLI no IA-01. O modelo também pode gerar outra resposta em novas inferências; não assumir determinismo.

Uma implementação com sintaxe e estrutura esperadas pode atingir `static_passed_review_required`, mas jamais `acceptance_passed`: **verificar estrutura AST não prova correção funcional**. Nenhuma importação, execução, shell ou teste do código gerado é feita nesta etapa. O operador deve revisar qualquer resposta.

## CI

GitHub Actions `tests` no PR #11, run #192 / ID `45104026687`, executou Python 3.12 e relatou **132 tests OK**, incluindo **21 testes** do módulo Task Manager e CLI SQLite com mocks e fixture; `bash -n` dos instaladores também passou. URL: https://github.com/pastrello/devhub/actions/runs/45104026687 . Novos commits posteriores deverão ser validados por outro run.

## Laboratório

Checkout: `/software/devhub`. A instalação global em `/opt/devhub` deve continuar em `0.1.5.1`; a branch 0.1.7-lab é experimental. Teste recomendado:

```bash
cd /software/devhub
git fetch origin
git switch feat/task-manager-0.1.7-lab
python3.12 -m unittest discover -s tests -p 'test_task_manager.py' -v

TASK_STATE=$(mktemp -d /tmp/devhub-tasklab.XXXXXXXX)
python3.12 devhub.py --state "$TASK_STATE" tasks create --id task-001 --model qwen2.5-coder:3b
python3.12 devhub.py --state "$TASK_STATE" tasks evaluate task-001 --response-file /software/devhub/tests/fixtures/task001-original.json
python3.12 devhub.py --state "$TASK_STATE" tasks show task-001
```

Esta etapa não cria contêineres, serviços, portas ou novas despesas com IA.
