# Agent Instructions

Agents must treat the following as canonical:
- `contracts/packet_envelope_v1.yaml`
- `contracts/conformant_node_contract.yaml`
- `contracts/node_registration_contract.yaml`
- `contracts/conformance_checklist.md`

When generating or editing services:
1. Read the contracts first.
2. Preserve PacketEnvelope invariants.
3. Keep Gate compatibility intact.
4. Use the service manifest and generator instead of hand-building structure.
