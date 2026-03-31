# Golden Repo Follow-On Pack

This pack wires the canonical protocol contracts into runtime and CI.

## What it does
- loads the canonical contract bundle at runtime
- enforces packet + registration shapes against the contracts
- validates the service manifest against the contracts
- adds a dedicated CI workflow for protocol conformance
- updates the service template renderer to emit protocol-native manifests

## Drop-in targets
Copy these files into the matching paths in the golden repo.

## Immediate post-copy steps
1. Ensure the repo already contains:
   - `contracts/packet_envelope_v1.yaml`
   - `contracts/conformant_node_contract.yaml`
   - `contracts/node_registration_contract.yaml`
2. Run:
   - `python scripts/validate_contract_alignment.py --repo-root . --manifest templates/service/service.manifest.yaml`
3. Run:
   - `pytest tests/contracts -q`
4. Enable the `protocol-conformance` workflow
