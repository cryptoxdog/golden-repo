<!--
L9_META:
  l9_schema: 1
  origin: l9-template
  engine: golden-repo
  layer: infrastructure
  tags: [infrastructure, docker, local-dev]
  owner: platform
  status: active
-->

# infrastructure/

Local and shared infrastructure assets — Dockerfiles, Compose stacks, supporting service images. Things that are *infrastructure as artifacts*, distinct from `deploy/` which is *infrastructure as environments*.

## Purpose

Provide reproducible local environments and reusable container assets so that "works on my machine" and "works in prod" derive from the same artifacts.

## What lives here

| Path | Responsibility |
|---|---|
| `infrastructure/docker/` | Container images and Compose fragments for the node and its supporting services. |

Use the root `Dockerfile` for development images, `Dockerfile.prod` for production images, and `infrastructure/docker/` for sidecars, dev databases, message brokers, and other services the node depends on locally.

## What does NOT live here

- **No environment-specific values.** Hostnames, secrets, sizes — those belong in `deploy/terraform/<env>/` or env files.
- **No application code.** Engines and chassis stay where they are.
- **No CI workflow definitions.** Those live in `.github/workflows/`.

## Contracts that govern this directory

- [`/contracts/registration/node_registration.contract.yaml`](../contracts/registration/node_registration.contract.yaml) — local Compose stacks must be capable of bringing up the registration handshake.
- [`/contracts/observability/metrics.contract.yaml`](../contracts/observability/metrics.contract.yaml) — local stacks include the observability sidecars from `observability/`.

## Quality gates

- All Dockerfiles run `hadolint` clean.
- Compose files validate with `docker compose config`.
- Pinned base image digests; no floating `:latest` tags.
- Distroless or `slim` bases for production images. Multi-stage builds enforced.

## Conventions

- Image names: `golden-repo/<role>:<sha>`, where `<role>` is one of `node`, `auditor`, `reviewer`.
- One concern per Dockerfile. No combined frontend+backend images.
- Health checks declared in the image, not patched on by Compose or k8s.
- Volumes named, never anonymous, in any Compose file.
