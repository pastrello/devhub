# Security

Laboratory only. No production access, privileged execution, automatic shell execution, cloud fallback, credential handling or account creation. Use trusted endpoints on private networks; prefer HTTPS. HTTP redirects and ambient proxies are refused. Do not use confidential prompts as CLI arguments. Local model tags are not proof of local execution: verify actual backend, model licensing, integrity, and no cloud routing. Restrict access to the state directory. Never publish secrets in this public repository. No claim of complete sandboxing or zero indirect electricity/network costs. Report security issues privately to the maintainer; do not post secrets in public issues.


## Discovery endpoint policy (0.1.2)

Model discovery is opt-in for each `models online` request. Search terms go to Hugging Face's public API; avoid submitting secrets, internal repositories or customer names. Results are untrusted metadata and never become executable commands or automatically approved downloads. GitHub releases are informational only, not update approval. Only fixed official HTTPS origins and API paths are queried; redirects and ambient proxies are disabled, response bytes capped, and no keys or browser account tokens are used. Persistent SQLite snapshots are private to the DevHub runtime user. Model fit calculations are heuristic and cannot certify LXC driver compatibility or security. Do not enable cloud inference or expose unauthenticated Ollama API publicly.


## Model preflight and supply chain (0.1.3)

An official registry manifest is not equivalent to a signed license, a vetted model, a trustworthy quantization or a guaranteed fit. Public tags can be retargeted. Every automated installation requires a stored preflight less than one hour old, unchanged manifest fingerprint, enough estimated disk space and explicit flags confirming download, license review and locally trusted inference. Off-host installation through unauthenticated Ollama API is blocked in the new command. The legacy curated-only pull remains for compatibility; use the reviewed preflight path for new models. Future hardened implementation should bind model digest to actual installed artifact and check original model card/license and runner compatibility. Do not grant broad permissions to Ollama's model directories to satisfy a non-root DevHub installer.


## 0.1.4 local worker and benchmark

Only local Ollama (localhost/127.0.0.1/::1) is accepted for automated benchmarks, with explicit `--trust-local-endpoint` approval. The wizard requires an interactive terminal; guided preflight does not download anything and performance probes require explicit confirmation. Benchmark prompts are fixed and not customer data, but generated content/telemetry is saved in the per-user SQLite registry. This is not a production multiagent sandbox. Remote worker registration, exposed ports, identity management and cloud execution are intentionally absent.


## 0.1.5 worker inventory trust model

Imported snapshots are not authenticated, are limited to descriptive metadata and **must never be interpreted as authorization for control-plane access or execution**. Input fields, ID syntax, file size, GPU values and model tags are validated with a strict whitelist. File import rejects symbolic links. `--confirm-import`, `--confirm-enroll` and `--confirm-forget` are required for changes; replacement also requires `--replace`. The 15-minute age limit only indicates how old a snapshot is, **not a verified remote heartbeat**. Public IPs, keys, shell commands, passwords and endpoints are not part of the schema. Future worker agents must be independently authenticated and audited.


## Worker mTLS policy — design not deployed

A [ADR-0001](docs/adr/0001-worker-mtls.md) specifies TLS 1.3 + mutual CA-based certificate validation + exact DNS SAN binding (`ia-01.worker.devhub.internal`) + per-worker SHA256 certificate fingerprint allowlisting. Merely importing worker metadata never authorizes a connection. The experimental `worker_mtls.py` accepts only read-only inventory/health actions after post-handshake identity validation; no listener, enrollment network service, runtime certificate generation, privileged integration or remote inference is included. Private keys must be operator provisioned and protected (file permissions `0600` or stricter); never place a CA key or worker private key in Git, audit logs or user chat. Certificate verification/PKI issuance and real handshake negative tests remain required before any remote deployment.
