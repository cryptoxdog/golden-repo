from __future__ import annotations

import json

import jsonschema

from tools.review.build_context import infer_change_type


def test_change_proposal_schema_accepts_minimal_valid_payload() -> None:
    schema = json.loads(
        open("tools/review/schemas/change_proposal.schema.json", encoding="utf-8").read()
    )
    payload = {
        "id": "proposal_abc",
        "type": "spec_change",
        "changed_files": ["spec.yaml"],
        "changed_lines": 12,
        "diff": "diff",
        "metadata": {
            "base_ref": "origin/main",
            "head_ref": "HEAD",
            "source": "git_pr",
        },
    }
    jsonschema.validate(instance=payload, schema=schema)


def test_change_proposal_type_inference() -> None:
    assert infer_change_type(["spec.yaml"]) == "spec_change"
    assert infer_change_type([".github/workflows/ci.yml"]) == "workflow_change"
    assert infer_change_type(["engine/handlers.py"]) == "code_change"
