<!-- L9_META
l9_schema: 1
origin: l9-template
engine: golden-repo
layer: [docs, contracts]
tags: [L9_TEMPLATE, contracts, versioning]
owner: platform
status: active
/L9_META -->

# Breaking-Change Policy

> Contracts are public APIs between authorities. Breaking them silently is the worst-case failure mode of an L9 system.

## Versioning

`{major}.{minor}.{patch}`

| Change | Bump |
|---|---|
| Field rename, removal, semantic change | **Major** |
| New field, new optional section, new enum value | Minor |
| Clarification, typo, non-normative example | Patch |

## Procedure for a Breaking Change

1. **ADR.** Open `docs/adr/NNNN-{slug}.md` with motivation, alternatives, migration plan.
2. **Bump contract major.** Mark prior version `status: superseded`.
3. **Land dual-read adapter** behind a feature flag. The adapter accepts both old and new shapes and emits the new shape downstream.
4. **Roll out producers** to the new shape.
5. **Verify all consumers report new version.** Telemetry: `transport.packet.contract_version{value}`.
6. **Remove the adapter.** Delete the superseded contract file in the same release.

## What Counts As Breaking

- Renaming a field
- Removing a field
- Changing a field's type
- Tightening a constraint that previously-valid messages no longer satisfy
- Removing an enum value
- Changing the meaning of an existing enum value
- Changing the canonical hash inputs

## What Counts As Non-Breaking

- Adding an optional field
- Adding a new enum value (consumers must accept unknown values forward-compatibly)
- Adding a new optional section
- Tightening server-side validation in a way that *rejects previously invalid* messages

## Forward Compatibility Rule

Consumers must:

- Accept unknown fields at the JSON level (drop or pass through).
- Accept unknown enum values gracefully (treat as failure with `reason: UNSUPPORTED_VARIANT`, not crash).
- Validate `header.schema_version` against their declared compatibility policy.

## Enforcement

- `tools/verify_contracts.py` checks every commit's contract diffs and rejects breaking changes without an ADR.
- CI tags every release artifact with `contract.version` so consumers can audit which versions are in flight.
