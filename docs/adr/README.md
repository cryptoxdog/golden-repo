<!-- L9_META
l9_schema: 1
origin: l9-template
engine: golden-repo
layer: [docs, adr]
tags: [L9_TEMPLATE, adr]
owner: platform
status: active
/L9_META -->

# Architecture Decision Records

> Every non-trivial architectural decision is recorded here. ADRs are immutable once accepted — corrections happen in a new ADR that supersedes the old one.

## Process

1. Copy `TEMPLATE.md` to `NNNN-{slug}.md` where `NNNN` is the next four-digit number.
2. Fill in Context, Decision, Consequences, Alternatives, and References.
3. Open a PR. Reviewers must include at least one platform owner.
4. On merge, the ADR is `Accepted`.
5. To change a decision, open a new ADR with `Status: Supersedes NNNN`.

## Statuses

| Status | Meaning |
|---|---|
| Proposed | Open PR, not yet merged |
| Accepted | Current canonical decision |
| Superseded by NNNN | Decision is no longer in force; see linked ADR |
| Deprecated | Decision is no longer applicable, no replacement |

## Index

| # | Title | Status |
|---|---|---|
| 0001 | TransportPacket as canonical execution contract | Accepted |
| 0002 | Gate is workflow-stateless | Accepted |

## When to Open an ADR

- Choosing a new transport, persistence, or auth mechanism
- Changing a contract (any breaking change requires an ADR)
- Adding a new authority or splitting an existing one
- Adopting or removing a major dependency
- Changing the boundary between Gate, Orchestrator, or Runtime
- Anything that future maintainers would ask "why?" about

## Template

See [`TEMPLATE.md`](TEMPLATE.md).
