<!--
L9_META:
  l9_schema: 1
  origin: l9-template
  engine: golden-repo
  layer: templates
  tags: [templates, scaffolding, generators]
  owner: platform
  status: active
-->

# templates/

Scaffolding the platform uses to generate new services, docs, and deploys. The **fingerprint** of a well-formed L9 artifact lives here.

## Purpose

When a developer runs `bootstrap.sh` or any generator, content is composed from this directory. The templates encode L9 invariants — headers, contracts, layout, naming — so that every generated artifact starts compliant.

## What lives here

| Path | Responsibility |
|---|---|
| `templates/service/` | New-service skeleton — chassis bindings, engine main, sample handler, contracts entry, README. |
| `templates/deploy/` | Deploy scaffolds — Terraform module skeleton, deploy script outline. |
| `templates/docs/` | Documentation templates — ADR, runbook, README skeletons matching `docs/`'s shape. |
| `templates/dev.conf.template` | Developer-environment configuration template, copied to `.env` on bootstrap. |
| `templates/styleguide.template.md` | Drop-in style guide for new services to ship `docs/STYLEGUIDE.md`. |

## What does NOT live here

- **No live service code.** Templates are *generators*, not running code. Imports here are checked but not executed in production.
- **No environment-specific values.** Templates are env-agnostic; bootstrap fills in env values.
- **No business logic.** Domain-specific patterns belong in `domains/example_domain/` and graduate into a real domain.

## Contracts that govern this directory

- [`/contracts/_schemas/l9_contract_meta.schema.json`](../contracts/_schemas/l9_contract_meta.schema.json) — every generated contract YAML validates against this meta-schema.
- [`/contracts/transport/transport_packet.contract.yaml`](../contracts/transport/transport_packet.contract.yaml) — generated services ship handlers that comply with this canonical envelope.

## Quality gates

- Every template ships an L9_META header (HTML comment for Markdown, YAML comment for YAML).
- `tools/auditors/` runs each template through a generator dry-run and asserts output is L9-compliant.
- Template changes require a corresponding update to `tools/l9_template_manifest.yaml`.
- Style guide template is matched against `docs/STYLEGUIDE.md` of every generated service.

## Conventions

- Template variables: `{{ snake_case_name }}`. No bare brace placeholders.
- Templates fail fast — missing variables raise; never silently default.
- Generated files include a comment line `# generated from templates/<path> — edits must be reflected upstream`.
- Add a template only when the same scaffold has been hand-written ≥ 3 times.
