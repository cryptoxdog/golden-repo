# Architecture

The engine remains chassis-compatible and does not own HTTP, auth, tenancy, or workflow policy.
The review subsystem is separate from engine runtime code and enforces architectural boundaries.

## Core rules

- `engine/handlers.py` is the only chassis bridge.
- `engine/services/*` may not import handlers.
- `engine/models/*` may not import services or handlers.
- `tools/review/*` analyzes runtime code but does not participate in runtime execution.
