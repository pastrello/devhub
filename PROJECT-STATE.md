# Project state — 0.1.0 PoC

Implemented: per-user CLI installer; static provider inventory and executable presence detection; live Ollama model listing and explicit pull/generation; optional unauthenticated LiteLLM catalog endpoint; deterministic local selection; zero-additional-cloud-cost deny policy; SQLite discovery snapshots and action/status audit.

Evidence: 13/13 unit tests passed in Python 3.13.5 in the development container; bash -n passed. No real provider, GPU, Rocky 9/10 installation, authentication, API billing or network integration validated. No charges incurred by these tests. Installer and Python 3.12 runtime pending lab validation.

Not implemented: hardware detection, live catalog harvesting, automatic local model installs, provider onboarding, cloud CLI execution, paid budget accounting, benchmarks, intelligent routing, Git project access, portal, worker isolation, PostgreSQL, multi-agent scheduling.

Next safe test: non-root installation on Rocky; doctor/discover; verify a known local Ollama tag with plan then run. Do not enable cloud until permissions, quotas and billing are verified. SQLite is temporary for PoC; PostgreSQL remains the distributed design target.
