# ADR-0001 — Identidade de worker e transporte mTLS (design experimental)

Status: **proposto / não habilitado**. Origem: homologação DevHub 0.1.5.1 no Rocky Linux LXC `IA-01` em 2026-11-22. Este ADR não autoriza abertura de portas nem execução distribuída.

## Contexto

O registro `worker_registry.py` apenas mantém snapshots. Um JSON importado pode ser forjado: nome, GPU e modelos não provam identidade. A próxima fase deve conectar workers sem expor o Ollama em `0.0.0.0:11434`, sem login por SSH para tarefas e sem fallback para serviços pagos.

## Decisão

1. **Identidade separada:** `worker_id` é etiqueta interna estável (ex.: `ia-01`), não host ou endereço IP. A identidade de certificado deverá ser um DNS SAN `ia-01.worker.devhub.internal`. O certificado será emitido por CA interna controlada pelo administrador; não aceitar identidade baseada somente em CN.
2. **Autenticação mútua:** tanto coordenador quanto worker apresentam certificados durante TLS. TLS 1.3 como versão mínima; verificação completa de cadeia e nome do servidor no cliente; o worker exige certificado de cliente válido e aprovado. Bibliotecas Python 3.12 `ssl` devem usar `CERT_REQUIRED`.
3. **Autorização independente:** CA válida não basta: um worker precisa estar em allowlist explícita `worker_id -> SHA256(DER certificado)`; igualdade com `hmac.compare_digest`. A SAN deve corresponder ao `worker_id`. O cadastro passivo sozinho não concede permissões.
4. **Escopo inicial exclusivo de leitura:** identidade validada só autoriza `inventory.read` ou `health.read`. Sem comando arbitrário, shell, instalação, pull, delete, inferência remota, credenciais de nuvem ou acessos a repositórios.
5. **Provisionamento externo:** esta branch **não** gera CA, certificados, chaves, sistema de secrets nem configura firewall. Referências a arquivos TLS devem ser caminhos absolutos de arquivos existentes, sem symlink final; chaves não podem ser acessíveis por grupo ou outros (`0600` ou mais restritivo). A CA privada não deve ser armazenada no mesmo worker e nunca deve entrar no GitHub.
6. **Sem listener nesta fase:** `worker_mtls.py` é uma biblioteca pura de configuração de contexto e verificação pós-handshake. Não chama `bind`, `listen`, `connect` nem abre HTTP. Nenhum comando novo DevHub fica disponível até teste de transporte e autorização em ambiente isolado.

## Fluxo futuro de homologação (não implementado)

1. Criar CA offline, emitir certificados de servidor e cliente com propósito/EKU correto, SAN distinto por node, expiração curta e rotação documentada.
2. Registrar impressão digital pública do certificado do worker após verificar identidade pela via administrativa.
3. Teste local de handshake mTLS com cert válido e negativo para CA desconhecida, nome errado, cert expirado, SAN errado e fingerprint não aprovado.
4. Implementar endpoint de inventário e saúde com autenticação anterior à serialização; limite de bytes e taxa, timeout, restrição de IPs e logs sem segredos.
5. Publicar só na rede privada/túnel aprovado, regras de firewall `default deny`; manter Ollama restrito a `127.0.0.1:11434`. Para múltiplos LXCs, provar que nenhuma rota externa consegue conectar diretamente à API Ollama.
6. Validar revogação/rotação, retries, auditoria, atualização segura e rollout/rollback antes de liberar a ação de coleta remota.
7. **Qualquer ação mutável** exige novo ADR sobre isolamento, políticas por worker, replay protection, quotas, autorização do usuário e auditoria. Não aproveitar automaticamente um token/identidade apenas de leitura.

## Limitações e ameaças residuais

- SHA256 fingerprint vincula uma instância do certificado, mas **não revoga a chave da CA**. Revogação nesta fase significa retirar o fingerprint do allowlist; transporte futuro deverá aplicar essa checagem em todas as sessões e encerrar conexões existentes quando necessário.
- Rotação de certificado exige atualização explícita do pin e período de transição controlado; implementação inicial aceita um pin por worker.
- Um worker comprometido pode mentir em inventários; mTLS autentica a identidade de quem reportou os dados, não garante correção das métricas.
- Uma SAN válida não substitui validação de cadeia e EKU feita no handshake TLS. Testes unitários com `mock` comprovam a política de aplicação, não a segurança criptográfica de um handshake real.
- Certificado pinado não implica automaticamente permissão de acesso a banco PostgreSQL, a API Ollama ou a outras máquinas.
- Os snapshots do `Worker Registry` continuam `metadata_only_unverified`; não mudar essa indicação sem autenticação online real.

## Referências

- Python 3.12 `ssl`: https://docs.python.org/3.12/library/ssl.html
- Issue de evolução: https://github.com/pastrello/devhub/issues/5
- Origem do laboratório: `docs/evidence/2026-11-22-ia01-qwen25-coder3b-benchmark.md`
