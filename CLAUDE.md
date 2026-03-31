# Canonical behavior

This repo is the golden template for L9 microservices.

Hard rules:
- do not implement Gate-specific orchestration here
- do not add alternate execution endpoints for core transport
- keep PacketEnvelope as the only transport contract
- keep `/v1/execute` as canonical execution endpoint
- keep business logic out of `chassis/` and `app/`
- keep deploy artifacts provider-driven and parameterized
- keep templates service-oriented, not node-specific to Gate

Execution model:
- startup: config -> preflight -> runtime bootstrap -> handler registration -> ready
- request path: inflate -> validate -> duplicate guard -> execute -> deflate
- deploy path: predeploy check -> bootstrap host -> upload release/env -> run deploy -> verify health/readiness

Golden repo ownership:
- reusable runtime belongs here
- service-specific handlers/payloads do not
