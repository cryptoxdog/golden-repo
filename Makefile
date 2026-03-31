PYTHON ?= python
BASE_REF ?= HEAD~1
HEAD_REF ?= HEAD
ARTIFACT_DIR ?= .artifacts/review
EVAL_OUTPUT ?= .artifacts/evals/eval_results.json

.PHONY: test lint typecheck review-local validate-policy eval clean

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check .

typecheck:
	$(PYTHON) -m mypy engine tools

review-local:
	mkdir -p $(ARTIFACT_DIR)
	$(PYTHON) tools/review/build_context.py --base-ref $(BASE_REF) --head-ref $(HEAD_REF) --output $(ARTIFACT_DIR)/review_context.json
	$(PYTHON) tools/review/classify_pr.py --proposal $(ARTIFACT_DIR)/review_context.json --policy tools/review/policy/review_policy.yaml --output $(ARTIFACT_DIR)/pr_classification.json
	$(PYTHON) tools/review/analyzers/template_compliance.py --repo-root . --manifest tools/review/policy/template_manifest.yaml --context $(ARTIFACT_DIR)/review_context.json --output $(ARTIFACT_DIR)/template_report.json
	$(PYTHON) tools/review/analyzers/architecture_boundary.py --repo-root . --architecture tools/review/policy/architecture.yaml --context $(ARTIFACT_DIR)/review_context.json --output $(ARTIFACT_DIR)/architecture_report.json
	$(PYTHON) tools/review/analyzers/protected_paths.py --policy tools/review/policy/review_policy.yaml --context $(ARTIFACT_DIR)/review_context.json --output $(ARTIFACT_DIR)/protected_paths_report.json
	$(PYTHON) tools/review/analyzers/spec_coverage.py --repo-root . --spec spec.yaml --output $(ARTIFACT_DIR)/spec_coverage_report.json
	$(PYTHON) tools/review/analyzers/yaml_validation.py --policy tools/review/policy/review_policy.yaml --output $(ARTIFACT_DIR)/yaml_validation_report.json
	$(PYTHON) tools/review/aggregate.py --reports \
		$(ARTIFACT_DIR)/template_report.json \
		$(ARTIFACT_DIR)/architecture_report.json \
		$(ARTIFACT_DIR)/protected_paths_report.json \
		$(ARTIFACT_DIR)/spec_coverage_report.json \
		$(ARTIFACT_DIR)/yaml_validation_report.json \
		--policy tools/review/policy/review_policy.yaml \
		--proposal $(ARTIFACT_DIR)/review_context.json \
		--output $(ARTIFACT_DIR)/final_verdict.json
	$(PYTHON) tools/review/format_pr_comment.py --report $(ARTIFACT_DIR)/final_verdict.json --output $(ARTIFACT_DIR)/pr_comment.md

validate-policy:
	$(PYTHON) tools/review/analyzers/yaml_validation.py --policy tools/review/policy/review_policy.yaml --output /tmp/yaml_validation_report.json

eval:
	mkdir -p $(dir $(EVAL_OUTPUT))
	$(PYTHON) tools/review/evals/replay.py --cases tests/fixtures/eval_cases.json --policy tools/review/policy/review_policy.yaml --output $(EVAL_OUTPUT)

clean:
	rm -rf .artifacts .pytest_cache
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
