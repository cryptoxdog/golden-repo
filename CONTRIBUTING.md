# Contributing

## Standard

Changes must make the golden repo better for future services without introducing service-specific drift.

## Required checks

- packet contract preserved
- startup remains deterministic
- deploy remains non-interactive after secret provisioning
- tests updated
- templates remain parameterized

## Reject changes that

- add hardcoded secrets
- add Gate-only logic
- bypass predeploy validation
- weaken duplicate/idempotency checks
