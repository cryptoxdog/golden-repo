PYTHON ?= python3
PIP ?= $(PYTHON) -m pip

.PHONY: install install-dev test new-service predeploy

install:
	$(PIP) install -e .

install-dev:
	$(PIP) install -e .[dev]

test:
	pytest

predeploy:
	python scripts/predeploy_check.py

new-service:
	python templates/service/render_service.py $(SERVICE)
