.PHONY: setup dev test test-unit test-integration test-compliance test-all test-watch lint audit agent-check agent-fix build deploy

# ============================================================
# SETUP
# ============================================================
setup:
	pip install -e ".[dev]"
	pre-commit install

dev:
	docker compose up -d

# ============================================================
# TESTING
# ============================================================
test:
	pytest tests/ -v --tb=short

test-unit:
	pytest tests/unit/ -v --tb=short

test-integration:
	pytest tests/integration/ -v --tb=short -m integration

test-compliance:
	pytest tests/compliance/ -v --tb=short

test-all:
	ruff check .
	ruff format --check .
	python tools/audit_engine.py --strict
	python tools/verify_contracts.py
	pytest tests/ -v --tb=short

test-watch:
	pytest-watch tests/unit/ -- -v --tb=short

# ============================================================
# QUALITY
# ============================================================
lint:
	ruff check .
	ruff format --check .
	mypy engine

audit:
	python tools/audit_engine.py

# ============================================================
# AGENT WORKFLOW
# ============================================================
agent-check:  ## THE universal gate. Agents run this before every commit.
	@echo "=== NAMING ===" && python tools/audit_engine.py --group naming
	@echo "=== SECURITY ===" && python tools/audit_engine.py --group security
	@echo "=== IMPORTS ===" && python tools/audit_engine.py --group imports
	@echo "=== COMPLETENESS ===" && python tools/audit_engine.py --group completeness
	@echo "=== PATTERNS ===" && python tools/audit_engine.py --group patterns
	@echo "=== TESTS ===" && pytest tests/ -v --tb=short
	@echo "=== CONTRACTS ===" && python tools/verify_contracts.py
	@echo "=== ALL CHECKS PASSED ==="

agent-fix:
	ruff check . --fix
	ruff format .
	python tools/audit_engine.py --fix

# ============================================================
# BUILD / DEPLOY
# ============================================================
build:
	docker build -t $$(basename $$(pwd)):latest .

deploy:
	./scripts/deploy.sh $(ENV)
