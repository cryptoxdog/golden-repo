
---

## Part III: Complete Pipeline DAG

```
PR Event → context-build
             ├── D1 arch-boundary        (deterministic, fast)
             ├── D3 spec-fidelity        (deterministic, fast)
             ├── D4 integration-boundary (deterministic, fast)
             ├── D5 template-compliance  (deterministic, fast)
             └── D6 supply-chain        (deterministic, fast)
                      │
                      └── DETERMINISTIC GATE ──────────────────┐
                               │ PASS                          │ FAIL → ❌ BLOCK
                               ↓
                    ┌──────────────────────────┐
                    │    D2 logic-correctness  │
                    │    D7 test-sufficiency   │  (static + optional mutation)
                    │    D8 performance-ops    │
                    └──────────────────────────┘
                               │
                               ↓
                    confidence-aggregation
                    S = Σ(wᵢ × score(vᵢ) × confᵢ)
                               │
              ┌────────────────┼───────────────┐
              ↓                ↓               ↓
        S >= 0.82          S >= 0.62        S < 0.62 or
        ✅ APPROVE         ⚠️ WARN          >=2 ESCALATE
                                             👤 ESCALATE TO HUMAN
```

**Implementation:** `.github/workflows/ai-review-full.yml`

---

## Part IV: Confidence Aggregation

### Weighted Ensemble Formula

```
S = Σ (wᵢ × score(verdictᵢ) × confidenceᵢ)
```

| Dimension | Weight | Veto Power |
|---|---|---|
| template_compliance | 0.20 | ✅ Absolute veto |
| security | 0.20 | ✅ Absolute veto |
| architectural_fit | 0.15 | |
| spec_fidelity | 0.15 | |
| business_logic | 0.12 | |
| test_sufficiency | 0.10 | |
| integration_boundary | 0.05 | |
| performance_ops | 0.03 | |

Verdict scores: APPROVE=1.0, WARN=0.6, ESCALATE=0.3, BLOCK=0.0

**Implementation:** `tools/auditors/review_aggregator.py`

### ReviewResult Schema v2.0.0

All 8 dimensions produce output conforming to `tools/review/schemas/review_result_v2.schema.json`:
- `dimension` — one of 8 canonical enum values
- `verdict` — APPROVE | WARN | BLOCK | ESCALATE
- `confidence` — 0.0-1.0 (deterministic = 0.97-0.99, LLM = 0.5-0.9)
- `evidence[]` — file/line/snippet/finding/severity
- `reasoning_chain[]` — step-by-step reasoning (required, minItems=1)
- `spec_coverage` — rules_found/covered/ratio/missing (D2, D3)
- `review_schema_version` — "2.0.0"
