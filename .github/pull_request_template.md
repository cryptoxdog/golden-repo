<!-- L9 PR template. Keep it short. Sharp PRs ship faster. -->

## Summary

<!-- One paragraph: what changes, why, and the user-visible effect. -->

## Type of change

- [ ] Feature
- [ ] Fix
- [ ] Chore / docs / refactor
- [ ] Contract change (breaking)
- [ ] Contract change (additive)

## Contracts touched

<!-- List every file under contracts/ this PR adds, modifies, or supersedes.
     If none, write "none". -->

- `contracts/...`

## ADR

- [ ] No ADR needed
- [ ] ADR added or updated: `docs/adr/NNNN-...`

For any change that alters a contract under `contracts/`, mark the relevant
boxes below or explain in the ADR why they do not apply:

- [ ] `docs/contracts/BREAKING_CHANGE_POLICY.md` reviewed
- [ ] Migration contract added under `contracts/transport/migration_*` if breaking
- [ ] Companion doc updated under `docs/contracts/`

## Verification

- [ ] `python scripts/verify_l9_contracts.py` passes locally
- [ ] `python scripts/check_l9_meta_headers.py` passes locally
- [ ] `python tools/verify_contracts.py` passes locally
- [ ] `pytest tests/contracts -q` passes locally

## Required reviewers

CODEOWNERS will request reviewers automatically. Confirm that owners for
every touched path have been requested.

## Risk

<!-- One line: rollout risk and rollback plan. -->
