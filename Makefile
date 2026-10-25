PYTHON ?= python3
PYTEST ?= pytest
SYNC_SCRIPT ?= scripts/sync_singapore_api.py

.PHONY: help test test-skills test-local test-top test-sg-home-chef package-skills package-property-advisor sync clean lint verify

help:
	@echo "Targets:"
	@echo "  make test                - run pytest on the whole repo (skills + top-level)"
	@echo "  make test-skills         - run published, self-contained package checks"
	@echo "  make test-local          - run the local-only developer suite and package checks"
	@echo "  make test-top            - run pytest on the top-level tests only"
	@echo "  make test-sg-home-chef   - run chef unit tests (requires local development/)"
	@echo "  make package-skills      - export all runtime-only skill folders and .skill ZIPs"
	@echo "  make package-property-advisor - export a runtime-only folder and .skill ZIP"
	@echo "  make sync                - copy canonical singapore_api.py to all 10 per-skill copies"
	@echo "  make clean               - remove __pycache__/ and .pytest_cache/ (gitignored)"
	@echo "  make verify              - clean + sync + test (full pre-PR gate)"
	@echo "  make lint                - LSP-style sanity check (not yet implemented)"

test:
	cd .. && $(PYTEST) singapore-skills/ -q

test-skills:
	$(PYTEST) tests/test_skill_distribution.py tests/test_property_distribution.py -q

test-local:
	@test -d development || (echo "Local development/ workspace is absent; it is not distributed in Git."; exit 1)
	$(PYTEST) development/ tests/test_skill_distribution.py tests/test_property_distribution.py -q

test-top:
	$(PYTEST) tests/ -q

test-sg-home-chef:
	$(PYTHON) -m unittest discover -s development/sg-home-chef/tests -v

package-skills:
	$(PYTHON) scripts/package_skills.py

package-property-advisor:
	$(PYTHON) scripts/package_property_advisor.py

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
