PYTHON ?= python3
PYTEST ?= pytest
SYNC_SCRIPT ?= scripts/sync_singapore_api.py

.PHONY: help test test-skills test-top sync clean lint verify

help:
	@echo "Targets:"
	@echo "  make test       - run pytest on the whole repo (skills + top-level)"
	@echo "  make test-skills - run pytest on per-skill tests only"
	@echo "  make test-top   - run pytest on the top-level tests only"
	@echo "  make sync       - copy canonical singapore_api.py to all 10 per-skill copies"
	@echo "  make clean      - remove __pycache__/ and .pytest_cache/ (gitignored)"
	@echo "  make verify     - clean + sync + test (full pre-PR gate)"
	@echo "  make lint       - LSP-style sanity check (not yet implemented)"

test:
	cd .. && $(PYTEST) singapore-skills/ -q

test-skills:
	$(PYTEST) skills/ -q

test-top:
	$(PYTEST) tests/ -q

sync:
	$(PYTHON) $(SYNC_SCRIPT)

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type d -name .pytest_cache -prune -exec rm -rf {} +
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
	@echo "Cleaned __pycache__/, .pytest_cache/, *.pyc, *.pyo"

verify: clean sync test

lint:
	@echo "No linter configured. Run 'basedpyright singapore-skills/' or your LSP for static analysis."
