# DevHub Worker Manager — mTLS loopback handshake test

Data: 2026-11-22 (lab validation), experimental branch `feat/worker-mtls-loopback-0.1.6`.

## Baseline

On the Rocky 9 LXC IA-01, the operator confirmed `python3.12 -m unittest discover -s tests -p 'test_worker_mtls.py' -v` completed **15 tests, OK**. That suite tests policy logic with mock TLS sockets; it does not perform real handshakes.

## New live TLS experiment (development environment)

The new test fixture `tests/test_worker_mtls_loopback.py` establishes TLS 1.3 handshakes using actual `socket`, Python `ssl` and OpenSSL-generated P-256 CA/server/client certificates. All temporary secret files are stored inside a private `TemporaryDirectory`, keys mode 0600, with cleanup after the test class. Server binds **127.0.0.1, port 0** and does not persist or invoke Ollama.

Environment: Python 3.13.5, OpenSSL 3.5.5 (development lab, not IA-01). Eight live positive/negative cases completed successfully in ~0.15s.

```text
test_client_rejects_unexpected_server_name ... ok
test_client_rejects_untrusted_server_ca ... ok
test_missing_client_certificate_rejected ... ok
test_real_mutual_tls_13_success_and_no_execution ... ok
test_tls12_only_client_rejected ... ok
test_unapproved_pinned_worker_rejected ... ok
test_unknown_ca_worker_rejected_in_handshake ... ok
test_wrong_worker_san_rejected ... ok

Ran 8 tests in 0.150s
OK
```

The accepted connection sends only two bytes `OK` following successful mTLS and read-only authorization. The negatives assert no `OK` arrives. These tests do **not** prove network access between separate LXCs, actual worker inventory transport, replay safety, revocation handling or daemon hardening.

## Next verification

```bash
cd /software/devhub
git fetch origin
git switch feat/worker-mtls-loopback-0.1.6
openssl version
python3.12 -m unittest discover -s tests -p 'test_worker_mtls_loopback.py' -v
python3.12 -m unittest discover -s tests -v
```

Do not run the system installer for these tests; operational DevHub remains 0.1.5.1. Handshake validation in the IA-01 Rocky LXC is pending operator evidence.


## Evidência adicional de CI

A execução GitHub Actions `tests` run **45097214967** concluiu `success` no commit `5249948a0999047a7b7d2f3a02bd842b6c66cbb2` usando Python **3.12.16** em Ubuntu. Logs: **111 tests, OK**; os oito testes de handshake real aparecem com `... ok`. Passaram também `openssl version` e a verificação de sintaxe Bash. URL: https://github.com/pastrello/devhub/actions/runs/45097214967 . Não confundir CI Ubuntu com homologação no Rocky IA-01.
