# L9 Golden Repo Protocol Lock Pack

This pack upgrades the golden repo into the canonical source of truth for:
- PacketEnvelope v1
- Conformant node requirements
- Node registration and capability descriptors
- Template wiring that makes future nodes protocol-native by default

## Adopt now
1. Copy `contracts/` into the golden repo.
2. Copy `templates/` into the golden repo.
3. Update root governance files with the references in this pack.
4. Make template generation depend on `templates/service/service.manifest.yaml`.
5. Treat protocol contract files as SSOT for all future node work.
