"""
tools/auditors/review_aggregator.py

Confidence Aggregator — Part IV of the AI Review Pipeline.

Combines per-dimension ReviewResult outputs into a single merge decision
using weighted ensemble scoring with security/template veto power.

Usage:
    python tools/auditors/review_aggregator.py \
        --reports report1.json report2.json ... \
        --output final_verdict.json \
        --post-github-comment  # optional

The aggregate score S = Σ (w_i × score(verdict_i) × confidence_i)
Security and template_compliance have absolute veto power:
if their verdict == BLOCK → final = BLOCK regardless of all other scores.

Merge policy:
  APPROVE  (S >= 0.82) → auto-merge
  WARN     (S >= 0.62) → merge with advisory comment
  ESCALATE (S < 0.62 or >= 2 ESCALATE dimensions) → hold for human review
  BLOCK    (any veto dimension BLOCK) → CI fails, merge blocked
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal


# ── Types ─────────────────────────────────────────────────────────────────────

Verdict = Literal["APPROVE", "WARN", "BLOCK", "ESCALATE"]

# Weights for weighted ensemble
DIMENSION_WEIGHTS: dict[str, float] = {
    "template_compliance":  0.20,  # Deterministic — highest weight
    "security":             0.20,  # Absolute veto power
    "architectural_fit":    0.15,
    "spec_fidelity":        0.15,
    "business_logic":       0.12,
    "test_sufficiency":     0.10,
    "integration_boundary": 0.05,
    "performance_ops":      0.03,
}

# Dimensions with absolute veto power — their BLOCK cannot be overridden
VETO_DIMENSIONS: frozenset[str] = frozenset({"security", "template_compliance"})

# Numeric score per verdict for weighted average
VERDICT_SCORE: dict[str, float] = {
    "APPROVE":  1.00,
    "WARN":     0.60,
    "ESCALATE": 0.30,
    "BLOCK":    0.00,
}


# ── Data models ───────────────────────────────────────────────────────────────

@dataclass
class AggregatedVerdict:
    final_verdict: Verdict
    aggregate_score: float
    aggregate_confidence: float
    dimension_verdicts: dict[str, Verdict]
    blocking_dimensions: list[str]
    escalating_dimensions: list[str]
    approval_summary: str
    escalation_message: str
    timestamp: str

    def to_dict(self) -> dict:
        return {
            "verdict": self.final_verdict,
            "final_verdict": self.final_verdict,
            "aggregate_score": round(self.aggregate_score, 4),
            "aggregate_confidence": round(self.aggregate_confidence, 4),
            "dimension_verdicts": self.dimension_verdicts,
            "blocking_dimensions": self.blocking_dimensions,
            "escalating_dimensions": self.escalating_dimensions,
            "approval_summary": self.approval_summary,
            "escalation_message": self.escalation_message,
            "timestamp": self.timestamp,
        }


# ── Core aggregation ──────────────────────────────────────────────────────────

def aggregate_verdicts(results: list[dict]) -> AggregatedVerdict:
    """
    Aggregate per-dimension results into a single merge decision.

    Algorithm:
    1. Check veto dimensions first — any BLOCK from security/template → final BLOCK
    2. Compute weighted score S = Σ (w_i × score_i × confidence_i)
    3. Apply decision thresholds
    """
    dimension_verdicts: dict[str, Verdict] = {}
    blocking_dims: list[str] = []
    escalating_dims: list[str] = []
    weighted_score = 0.0
    total_weight = 0.0
    confidences: list[float] = []

    for result in results:
        dim = result.get("dimension", "unknown")
        verdict: Verdict = result.get("verdict", "ESCALATE")
        confidence = float(result.get("confidence", 0.5))
        weight = DIMENSION_WEIGHTS.get(dim, 0.05)

        dimension_verdicts[dim] = verdict
        confidences.append(confidence)

        if verdict == "BLOCK":
            blocking_dims.append(dim)
        elif verdict == "ESCALATE":
            escalating_dims.append(dim)

        score = VERDICT_SCORE.get(verdict, 0.0) * confidence
        weighted_score += weight * score
        total_weight += weight

    aggregate_score = weighted_score / max(total_weight, 1e-9)

    # Veto check — overrides score
    veto_blocks = [d for d in blocking_dims if d in VETO_DIMENSIONS]

    # Decision
    if blocking_dims:
        final_verdict: Verdict = "BLOCK"
    elif len(escalating_dims) >= 2:
        final_verdict = "ESCALATE"
    elif aggregate_score >= 0.82:
        final_verdict = "APPROVE"
    elif aggregate_score >= 0.62:
        final_verdict = "WARN"
    else:
        final_verdict = "ESCALATE"

    # Conservative confidence: minimum across all dimensions
    aggregate_confidence = min(confidences) if confidences else 0.0

    return AggregatedVerdict(
        final_verdict=final_verdict,
        aggregate_score=aggregate_score,
        aggregate_confidence=aggregate_confidence,
        dimension_verdicts=dimension_verdicts,
        blocking_dimensions=blocking_dims,
        escalating_dimensions=escalating_dims,
        approval_summary=_build_approval_summary(results, aggregate_score),
        escalation_message=_build_escalation_message(results, escalating_dims, blocking_dims),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


# ── Message builders ──────────────────────────────────────────────────────────

_VERDICT_EMOJI = {"APPROVE": "✅", "WARN": "⚠️", "BLOCK": "❌", "ESCALATE": "👤"}


def _build_approval_summary(results: list[dict], score: float) -> str:
    lines = [
        f"## ✅ AI Review: APPROVED (score={score:.2f})",
        "",
        "All review dimensions passed autonomous review.",
        "",
        "| Dimension | Verdict | Confidence |",
        "|-----------|---------|------------|",
    ]
    for r in results:
        dim = r.get("dimension", "?")
        v = r.get("verdict", "?")
        conf = float(r.get("confidence", 0))
        emoji = _VERDICT_EMOJI.get(v, "")
        lines.append(f"| {dim} | {emoji} {v} | {conf:.0%} |")

    lines += ["", "*Reviewed by L9 AI Review Pipeline*"]
    return "\n".join(lines)


def _build_escalation_message(
    results: list[dict],
    escalating: list[str],
    blocking: list[str],
) -> str:
    lines: list[str] = []

    if blocking:
        lines.append(f"## ❌ AI Review: BLOCKED")
        lines.append("")
        lines.append(f"**Blocking dimensions:** {', '.join(blocking)}")
        lines.append("")
        lines.append("### Blocking findings:")
        for r in results:
            if r.get("dimension") in blocking:
                for ev in r.get("evidence", []):
                    lines.append(f"- **{ev.get('severity')}** `{ev.get('file')}:{ev.get('line')}` — {ev.get('finding')}")
    elif escalating:
        lines.append("## 👤 AI Review: ESCALATION REQUIRED")
        lines.append("")
        lines.append(f"**Dimensions requiring human review:** {', '.join(escalating)}")
        lines.append("")
        lines.append("The following items require human judgment:")
        for r in results:
            if r.get("dimension") in escalating:
                lines.append(f"\n### {r.get('dimension')}")
                for step in r.get("reasoning_chain", []):
                    lines.append(f"- {step}")

    lines += ["", "*L9 AI Review Pipeline — escalation requested*"]
    return "\n".join(lines)


# ── GitHub comment posting ────────────────────────────────────────────────────

def post_github_comment(verdict: AggregatedVerdict, pr_number: int) -> None:
    """Post review comment via gh CLI."""
    import subprocess
    body = (
        verdict.approval_summary
        if verdict.final_verdict == "APPROVE"
        else verdict.escalation_message
    )
    subprocess.run(
        ["gh", "pr", "comment", str(pr_number), "--body", body],
        check=False,
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Review verdict aggregator")
    parser.add_argument("--reports", nargs="+", required=True, help="Per-dimension JSON reports")
    parser.add_argument("--output", default="final_verdict.json")
    parser.add_argument("--post-github-comment", action="store_true")
    parser.add_argument("--pr-number", type=int, default=0)
    args = parser.parse_args()

    results: list[dict] = []
    for report_path in args.reports:
        p = Path(report_path)
        if not p.exists():
            print(f"WARNING: report not found: {report_path}", file=sys.stderr)
            continue
        try:
            data = json.loads(p.read_text())
            # Handle both wrapped ({verdict: ..., dimension: ...}) and bare formats
            if "dimension" in data:
                results.append(data)
            elif "verdict" in data:
                # Unwrapped — infer dimension from filename
                stem = p.stem.replace("_report", "").replace("_review", "")
                data["dimension"] = stem
                results.append(data)
        except json.JSONDecodeError as exc:
            print(f"WARNING: could not parse {report_path}: {exc}", file=sys.stderr)

    if not results:
        print("ERROR: no valid reports found", file=sys.stderr)
        return 2

    verdict = aggregate_verdicts(results)
    Path(args.output).write_text(json.dumps(verdict.to_dict(), indent=2))

    print(
        f"verdict={verdict.final_verdict} "
        f"score={verdict.aggregate_score:.3f} "
        f"confidence={verdict.aggregate_confidence:.3f} "
        f"blocking={verdict.blocking_dimensions} "
        f"escalating={verdict.escalating_dimensions}"
    )

    if args.post_github_comment and args.pr_number:
        post_github_comment(verdict, args.pr_number)

    return 0 if verdict.final_verdict in ("APPROVE", "WARN") else 1


if __name__ == "__main__":
    sys.exit(main())
