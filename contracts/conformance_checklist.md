# L9 Conformance Checklist

A node is **conformant** only if every item below is true.

## Protocol
- [ ] Accepts PacketEnvelope over `POST /v1/execute`
- [ ] Validates canonical packet structure before execution
- [ ] Validates destination, action, packet type, and policy
- [ ] Preserves tenant immutability across derivation
- [ ] Derives responses instead of mutating inbound packets
- [ ] Supports canonical failure packet behavior

## Runtime
- [ ] Loads typed config before serving traffic
- [ ] Runs preflight before readiness becomes true
- [ ] Initializes runtime state store before execution
- [ ] Registers handlers before readiness becomes true
- [ ] Rejects duplicate packet receipts before handler execution

## HTTP surfaces
- [ ] `GET /v1/health` exists
- [ ] `GET /v1/readiness` exists
- [ ] `POST /v1/execute` exists
- [ ] `GET /metrics` is either implemented or explicitly disabled by policy

## Security and policy
- [ ] Signature behavior matches configured algorithm and policy
- [ ] Replay policy is explicit
- [ ] Required idempotency is enforced for configured actions
- [ ] Attachment URI policy is enforced
- [ ] Internal errors are sanitized by default

## Deployment
- [ ] `scripts/predeploy_check.py` passes in target environment
- [ ] Entrypoint runs predeploy check before startup
- [ ] Health passes after boot
- [ ] Readiness passes after boot
- [ ] Rollback path exists
- [ ] Backup/restore path exists

## Gate compatibility
- [ ] Node can be registered with canonical registration contract
- [ ] Supported actions are declared
- [ ] Health endpoint is declared
- [ ] Timeout is declared
- [ ] Node can process Gate-originated PacketEnvelopes without bespoke translation
