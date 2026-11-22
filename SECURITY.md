# Security

Laboratory only. No production access, privileged execution, automatic shell execution, cloud fallback, credential handling or account creation. Use trusted endpoints on private networks; prefer HTTPS. HTTP redirects and ambient proxies are refused. Do not use confidential prompts as CLI arguments. Local model tags are not proof of local execution: verify actual backend, model licensing, integrity, and no cloud routing. Restrict access to the state directory. Never publish secrets in this public repository. No claim of complete sandboxing or zero indirect electricity/network costs. Report security issues privately to the maintainer; do not post secrets in public issues.


## Discovery endpoint policy (0.1.2)

Model discovery is opt-in for each `models online` request. Search terms go to Hugging Face's public API; avoid submitting secrets, internal repositories or customer names. Results are untrusted metadata and never become executable commands or automatically approved downloads. GitHub releases are informational only, not update approval. Only fixed official HTTPS origins and API paths are queried; redirects and ambient proxies are disabled, response bytes capped, and no keys or browser account tokens are used. Persistent SQLite snapshots are private to the DevHub runtime user. Model fit calculations are heuristic and cannot certify LXC driver compatibility or security. Do not enable cloud inference or expose unauthenticated Ollama API publicly.


## Model preflight and supply chain (0.1.3)

An official registry manifest is not equivalent to a signed license, a vetted model, a trustworthy quantization or a guaranteed fit. Public tags can be retargeted. Every automated installation requires a stored preflight less than one hour old, unchanged manifest fingerprint, enough estimated disk space and explicit flags confirming download, license review and locally trusted inference. Off-host installation through unauthenticated Ollama API is blocked in the new command. The legacy curated-only pull remains for compatibility; use the reviewed preflight path for new models. Future hardened implementation should bind model digest to actual installed artifact and check original model card/license and runner compatibility. Do not grant broad permissions to Ollama's model directories to satisfy a non-root DevHub installer.
