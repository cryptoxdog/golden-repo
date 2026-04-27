<!--
L9_META:
  l9_schema: 1
  origin: l9-template
  engine: golden-repo
  layer: ops
  tags: [scripts, ops, automation]
  owner: platform
  status: active
-->

# scripts/

Operational scripts. Things you run **outside** the request path: at boot, at deploy, at audit time, in CI.

## Purpose

Hold the small, sharp tools that operate the service — wait-for, init, backup, restore, predeploy checks, contract alignment validation — without polluting the engine or chassis.

## What lives here

| Script | Purpose |
|---|---|
| `entrypoint.sh` | Container entrypoint shim used by the chassis Dockerfile. |
| `init_runtime.py` | One-shot runtime initialisation (schema check, seed, capability negotiation). |
| `wait_for_http.py` | Polls a URL until ready; used in compose and CI to gate dependent steps. |
| `backup_runtime.sh`, `restore_runtime.sh` | Local-state backup/restore for development sandboxes. |
| `predeploy_check.py` | Pre-deploy assertions: schema diff, contract compatibility, env required. |
| `validate_contract_alignment.py` | Verifies engine handlers and chassis routes match `contracts/`. |
| `validate-policy.sh` | Runs OPA / semgrep policy bundles locally. |
| `review-local.sh` | Runs the full reviewer pipeline (`tools/review/`) against a local working copy. |
| `changed-files.sh` | Helper for CI to scope checks to changed paths. |
| `perplexity_audit_agent.py` | The L9 audit agent driver — invokes auditors in `tools/auditors/`. |

## What does NOT live here

- **No request-path code.** Anything called per packet belongs in `chassis/` or `engine/`.
- **No deployment infra.** Terraform / k8s manifests live in `deploy/` and `infrastructure/`.
- **No secrets.** Read from env or vault; never embedded.

## Contracts that govern this directory

- [`/contracts/registration/node_registration.contract.yaml`](../contracts/registration/node_registration.contract.yaml) — `init_runtime.py` honours the registration handshake.
- [`/contracts/transport/transport_packet.contract.yaml`](../contracts/transport/transport_packet.contract.yaml) — `validate_contract_alignment.py` checks every handler against the canonical packet shape.

## Quality gates

- Every shell script: `set -euo pipefail`, `shellcheck` clean.
- Every Python script: type-checked under `mypy.ini` strict profile, runs under `python -W error`.
- No script may write outside its declared output dir without `--force`.
- `predeploy_check.py` exits non-zero on any contract drift; CI gates merges on it.

## Conventions

- Idempotent by default. Re-running a script must not corrupt state.
- Read configuration from the same env surface as the chassis (`.env.template`).
- Emit structured logs to stderr; data to stdout. Never mix.
