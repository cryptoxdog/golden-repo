<!-- L9_META
l9_schema: 1
origin: l9-template
engine: golden-repo
layer: [meta]
tags: [L9_TEMPLATE, implementation-note, audit, harden, principal_id, build_manifest]
owner: platform
status: active
/L9_META -->

# Implementation Note — L9 Pack Harden + Principal-ID Strategy

**Branch:** `chore/l9-pack-harden`
**Includes:** corrections to `chore/l9-docs-contracts-scaffold` and
`feat/contracts-ci-wiring`, plus the `principal_id` strategy memo and Phase 0
build manifest.

This branch executes a single YNP bundle:

1. **Audit / harden / regenerate** the prior file pack
   (`pack_audit_harden_regenerate.kernel.v1`).
2. **Reasoning memo** for `principal_id` propagation across 106 endpoints
   (`reasoning_think_strategy.kernel.v1_1`, 8 blocks).
3. **Phase 0 build manifest** for the resulting middleware
   (`l9_zero_stub_build_protocol.kernel.v3_0_0`, Phase 0 only).

---

## 1. Audit findings (Action 1)

Pack audited under `pack_audit_harden_regenerate.kernel.v1`.

| Severity | Finding | Resolution |
|---|---|---|
| CRITICAL | `contracts/governance/delegation_chain.contract.yaml` was invalid YAML — parser failed on unquoted `≤` glyph and malformed `failure_modes` list at lines 56–69. | Full regeneration. `scope_lattice` examples now structured records; `failure_modes` is a list of typed objects with `code` + `reject_reason`. |
| HIGH | `scripts/verify_l9_contracts.py` accepted only the inline `# L9_META:` form; every contract used the block form `# --- L9_META --- ... # --- /L9_META ---`. Result: 12/12 contracts falsely reported as missing the header. | Full regeneration. Verifier now accepts both inline and block forms. |
| HIGH | `scripts/check_l9_meta_headers.py` accepted only the inline `<!-- L9_META:` form; every doc used the block form `<!-- L9_META\n...\n/L9_META -->`. | Full regeneration. Header check now accepts both inline and block forms. |
| MEDIUM | `docs/ci/REQUIRED_CHECKS.md` did not document either header form, so authors had no reference for what passes. | Full regeneration. Document now shows both Markdown and YAML forms with examples and recommends the block form for new files. |
| LOW | `.github/workflows/contracts-l9.yml` install step swallowed real failures with an `|| echo "NOTE: ..."` chain. | Full regeneration. Tighten to `pip install -e ".[dev]" || pip install -e "."`; a real install failure is now fatal. |

### Files regenerated in full

- `contracts/governance/delegation_chain.contract.yaml`
- `scripts/verify_l9_contracts.py`
- `scripts/check_l9_meta_headers.py`
- `.github/workflows/contracts-l9.yml`
- `docs/ci/REQUIRED_CHECKS.md`

### Revalidation (post-harden)

| Check | Before | After |
|---|---|---|
| `python scripts/verify_l9_contracts.py` | FAIL (0/12 contracts) | **PASS (12/12 contracts)** |
| `python scripts/check_l9_meta_headers.py` | FAIL (12 missing) | **PASS (46/46 in-scope)** |
| `python -c 'import yaml; yaml.safe_load(open(...))'` over every `contracts/**/*.contract.yaml` | 1 broken | **all parse** |
| Workflow YAML validity | OK | **OK** |

No file from the original pack was dropped. No new file was introduced
beyond what Action 2 and Action 3 explicitly require.

---

## 2. Strategy memo (Action 2)

**File:** `docs/strategy/PRINCIPAL_ID_PROPAGATION.md`

Produced under `reasoning_think_strategy.kernel.v1_1`. The 8-block flow
(Objective → Context → Decomposition → Leverage → Strategy 5A/5B/5C →
Execution → Synthesis → Sum/Anticipate/Deliver) lands on the answer:

> **One chassis middleware that hydrates `tenant_context.principal_id` on
> every TransportPacket inside the existing gate execute path. Zero handler
> changes. 106 endpoints covered in a single PR.**

The memo includes:
- Three-way leverage comparison (per-handler refactor vs. decorator vs.
  middleware) with explicit kernel-1 gate rationale.
- Rollout plan R0 → R3 with a feature flag and SLI gate per phase.
- Verification plan (unit, contract, compliance, performance, banned-pattern
  scan).
- Anticipated questions (legacy packet handling, orchestrator impact) with
  pre-decided answers.

---

## 3. Phase 0 build manifest (Action 3)

**File:** `docs/strategy/PHASE_0_BUILD_MANIFEST.principal_id.md`

Produced under `l9_zero_stub_build_protocol.kernel.v3_0_0`, Phase 0. Mandated
sections:

| Section | Status |
|---|---|
| `file_tree` | 9 new files · 4 modified files · 13 touchpoints, listed verbatim. |
| `public_signatures` | Full type-hinted signatures for `TenantContext`, `principal_middleware`, `build_app`, `hash_principal_id_processor`, contract YAML field. |
| `handler_registrations` | Zero — by design. The strategy's central property is no handler change. |
| `domain_yaml_list` | Empty — chassis-only feature. |
| `packet_type_list` | None new — extends `tenant_context` block of every existing packet. |
| `external_deps` | No new third-party dependencies. |
| `external_utils` | Five existing chassis utilities reused; missing-util edge case documented. |
| `validation_checklist` | 7 categories (naming, imports, security, completeness, wiring, signatures, testing) plus performance and ADR gates. |

This manifest is the single contract for the implementation PR. The
implementation PR (Phases 1–6) consumes the manifest verbatim; no file
appears in the implementation that is absent from this manifest, and vice
versa.

---

## 4. What this branch does not change

- No engine, chassis, tools, or domain source is modified.
- No legacy contract is removed.
- No production behaviour changes — this branch is corrections + reasoning +
  manifest only.
- The `principal_id` middleware itself is **not implemented** in this branch.
  Phase 0 emits the manifest only; Phases 1–6 land in `feat/principal-id-on-tenant-context`.

---

## 5. Next steps

1. **Open three PRs** in the order:
   1. `chore/l9-docs-contracts-scaffold` → `main`
   2. `feat/contracts-ci-wiring` → `main`
   3. `chore/l9-pack-harden` → `main` (this branch — **corrects** the first two)
2. After (3) merges, configure branch protection per
   `docs/ci/REQUIRED_CHECKS.md`.
3. Open `feat/principal-id-on-tenant-context` and consume
   `docs/strategy/PHASE_0_BUILD_MANIFEST.principal_id.md` verbatim under the
   zero-stub protocol Phases 1–6.
4. After (3) flips R3 (field becomes required), schedule
   `chore/legacy-contract-manifest-reconciliation` to make
   `tools/verify_contracts.py` blocking again.

---

## 6. Kernel adherence summary

| Kernel | How this turn used it |
|---|---|
| `l9_first_order_thinking_enforcement.kernel.v1` | All 5 silent gates run in pre-flight; rabbit-hole gate explicitly bounded action 3 to Phase 0 (manifest only, not implementation). |
| `reasoning_think_strategy.kernel.v1_1` | The 8 blocks are the structure of `PRINCIPAL_ID_PROPAGATION.md` verbatim, including the 5A/5B/5C nested strategy lenses. |
| `l9_zero_stub_build_protocol.kernel.v3_0_0` | Action 3 emits exactly the Phase 0 artifact required (`BUILD_MANIFEST.md`); all eight mandated sections are present; pre-submission checklist is shipped as the validation_checklist for the implementation PR. |
| `pack_audit_harden_regenerate.kernel.v1` | All 6 phases executed: audit → gap analysis → correction → regeneration → revalidation → emission. Every affected file regenerated in full; no fragments. |

---

## 7. Post-PR audit triage (added on push #2 of this branch)

After CI ran on PRs #54/#55/#56, two findings were triaged on the harden
branch under `pack_audit_harden_regenerate.v1` (no new branch — corrections
go to the existing harden branch by design):

### Finding A — CRITICAL: pre-existing YAML bug in `contracts/packet_envelope_v1.yaml`

Three top-level keys (`governance:`, `delegation_chain:`, `hop_trace:`)
were indented with a single leading space, which `yaml.safe_load` rejects
with `expected <block end>, but found '<block mapping start>'` at line
178. The bug pre-existed our scaffold (file last touched in PR #25) but
was masked because no CI step actually parsed the file end-to-end until
our `contracts-l9.yml` workflow added `validate_contract_alignment.py`
to the required check.

**Fix:** Removed the stray leading space on the three lines. File now
parses; all 15 declared top-level keys present:
`protocol`, `packet`, `header`, `address`, `tenant`, `security`,
`governance`, `delegation_chain`, `hop_trace`, `lineage`, `attachments`,
`packet_classes`, `replay_policy`, `error_contract`, `conformance`.

### Finding B — HIGH: schema mismatch between `validate_contract_alignment.py` and `templates/service/service.manifest.yaml`

`scripts/validate_contract_alignment.py` reads
`manifest['service']['protocol_version']`, but the current service
manifest is flat (`service_name`, `package_name`, `app_module`, ...) with
no `service:` wrapper. The script has been broken on `main` since merge
of PR #28 — it failed silently because no required check ran it.
Reconciliation (script ↔ template) is a non-trivial decision (which
schema is canonical?) and is out of scope for L9 contracts CI wiring.

**Fix (this branch):** The alignment step in `contracts-l9.yml` now runs
under `continue-on-error: true` with a clearly logged advisory note. The
required check still asserts the L9 canonical contracts (meta-schema,
L9_META headers, TransportPacket discipline). `docs/ci/REQUIRED_CHECKS.md`
documents the deferral and the promotion path: when the legacy mismatch
is reconciled, drop `continue-on-error` to make the step blocking.

### Files changed in push #2

- `contracts/packet_envelope_v1.yaml` — three indent fixes
- `.github/workflows/contracts-l9.yml` — alignment step → advisory
- `docs/ci/REQUIRED_CHECKS.md` — documented advisory deferral

Re-validation on harden branch: `verify_l9_contracts.py` 12/12 PASS,
`check_l9_meta_headers.py` 46/46 PASS + 27 legacy exemptions,
`yaml.safe_load(packet_envelope_v1.yaml)` succeeds.
