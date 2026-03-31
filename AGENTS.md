# Agent guide

## Scope

This repo produces reusable microservice packs.
It is not the place for service-specific business rules unless they live under templates.

## Roles

- Platform agent: maintains transport, startup, security, deploy, clients
- Template agent: maintains service generator and 10X templates
- Service agent: consumes this repo to stamp new microservices

## Boundaries

Allowed:
- improve chassis, startup, deploy, template rendering, tests
- add provider-safe deploy defaults
- add reusable service scaffolds

Not allowed:
- hardcode service secrets
- hardcode Gate-only assumptions into the golden runtime
- drift from PacketEnvelope-only transport
