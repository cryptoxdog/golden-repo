<!-- L9_META
l9_schema: 1
origin: l9-template
engine: golden-repo
layer: [docs, contracts]
tags: [L9_TEMPLATE, contracts, delegation]
owner: platform
status: active
/L9_META -->

# Delegation Protocol

Source contract: [`contracts/governance/delegation_chain.contract.yaml`](../../contracts/governance/delegation_chain.contract.yaml)

## Purpose

Carry scoped, time-bounded authorization across multi-hop flows. Every node that further delegates appends a grant. The chain is append-only and tamper-evident.

## Grant Shape

```yaml
- delegator: <principal granting authority>
  delegate:  <principal receiving authority>
  scope:     [<capability tokens>]
  issued_at: <ISO 8601 UTC>
  expires_at: <ISO 8601 UTC>
  signature: <optional detached signature>
```

## Invariants

- Append-only.
- Chain must root at the originator.
- Each grant's `scope` must be ≤ the previous grant's scope (no widening).
- Expired grants invalidate the entire packet.
- Signature is optional but strongly recommended for cross-org delegation.

## Scope Lattice

Scopes form a partial order. Examples:

- `execute:match` ≤ `execute:*`
- `read:org:acme` ≤ `read:org:*`

A child grant must request a subset of its parent's scope.

## Enforcement Points

- `gate_ingress_validator` — checks chain shape, expiry, root match.
- `runtime_handler_pre_execute_check` — validates the action is in scope.
- `orchestrator_step_authorization_check` — validates each step's required scope is granted.

## Failure Modes

| Condition | Reason |
|---|---|
| Empty chain when required | `DELEGATION_REQUIRED` |
| Expired grant | `DELEGATION_EXPIRED` |
| Scope widening violation | `SCOPE_WIDENING_FORBIDDEN` |
| Originator mismatch | `DELEGATION_ROOT_MISMATCH` |
