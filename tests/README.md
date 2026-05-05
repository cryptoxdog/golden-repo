<!--
L9_META:
  l9_schema: 1
  origin: l9-template
  engine: golden-repo
  layer: tests
  tags: [tests, contracts, integration, compliance]
  owner: platform
  status: active
-->

# tests/

Tests organised by **what they protect**, not by what they import.

## Purpose

The test suite is the executable specification of the node. It enforces contracts, exercises the gate, and validates engine behaviour against golden fixtures. Every PR keeps this suite green.

## Layout

| Path | Protects |
|---|---|
| `tests/unit/` | Pure-logic correctness. No I/O, no network, no fixtures heavier than a dict. Target: ≥ 90% line coverage on `engine/core/`. |
| `tests/contracts/` | Round-trip every handler through `TransportPacket` (in) → handler → `TransportPacket` (out). Asserts conformance to `contracts/transport/transport_packet.schema.json` and per-action contract files. |
| `tests/integration/` | End-to-end execute path through the chassis with a stub engine. Boots the FastAPI app in-process, exercises gate semantics. |
| `tests/compliance/` | L9 template compliance — file inventory, headers, banned imports, contract meta-schema validity. |
| `tests/review_fixtures/` | Golden inputs for the reviewer pipeline (`tools/review/`). Treat as immutable; updates require a fixture-change review. |
| `tests/conftest.py` | Shared fixtures: ephemeral settings, packet factories, tenant context builders. |

## What does NOT live here

- **No live network calls.** Integration tests run against in-process stubs and ephemeral databases. Live calls belong in pre-deploy smoke tests under `scripts/predeploy_check.py`.
- **No production secrets** — even in fixtures.
- **No domain reach across slices.** A unit test for `engine/core/foo` does not import from `engine/core/bar`.

## Contracts that govern this directory

- [`/contracts/transport/transport_packet.contract.yaml`](../contracts/transport/transport_packet.contract.yaml) — `tests/contracts/` is the runtime check that this contract holds.
- [`/contracts/gate/gate.contract.yaml`](../contracts/gate/gate.contract.yaml) — `tests/integration/` exercises the gate execute path described here.
- [`/contracts/_schemas/l9_contract_meta.schema.json`](../contracts/_schemas/l9_contract_meta.schema.json) — `tests/compliance/` validates every contract YAML against this meta-schema.

## Quality gates

- `pytest` exits zero before any merge.
- Coverage threshold enforced in `pyproject.toml`. Drops fail CI.
- `tests/contracts/` must include at least one failing-shape test per action (negative case).
- New handlers ship with: 1 unit test, 1 contract test, 1 integration test minimum.

## Conventions

- One test file per module under test. Mirror the source tree.
- Use `pytest.mark.contract`, `pytest.mark.integration`, `pytest.mark.compliance` to scope CI shards.
- Fixtures that build packets must use the canonical builder from `client/packet_builder.py` — never raw dict construction.
- No `time.sleep` in tests; use injected clocks.
