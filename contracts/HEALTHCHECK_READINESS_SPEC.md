# Service health contract

## /v1/health
Returns:
- service identity
- version
- adapter readiness flag

## /v1/readiness
Returns:
- ready=true only after startup/preflight/registration complete
- no internal filesystem paths

## /metrics
- optional
- disabled by default in prod
