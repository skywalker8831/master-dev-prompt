SHELL := /bin/bash

PYTHON ?= python3
VALIDATOR := ./validate_output.py
MOCK_RUNNER := ./mock_runner.sh
OUTPUT_DIR ?= ./outputs
TRANSCRIPTS_DIR ?= ./transcripts
FILE ?=
TRANSCRIPT ?=

.PHONY: help validate-file validate-outputs test-validator mock-run test-mock ci

help:
	@echo "Targets:"
	@echo "  make validate-file FILE=path/to/output.json"
	@echo "  make validate-outputs [OUTPUT_DIR=./outputs]"
	@echo "  make test-validator"
	@echo "  make mock-run [TRANSCRIPT=path/to/transcript.txt]"
	@echo "  make test-mock"
	@echo "  make ci"

validate-file:
	@if [[ -z "$(FILE)" ]]; then \
		echo "FILE is required. Example: make validate-file FILE=outputs/sample.json"; \
		exit 2; \
	fi
	@$(PYTHON) $(VALIDATOR) "$(FILE)"

validate-outputs:
	@files=$$(find "$(OUTPUT_DIR)" -type f -name "*.json" ! -name "*.invalid.json" 2>/dev/null | sort); \
	if [[ -z "$$files" ]]; then \
		echo "No JSON files found in $(OUTPUT_DIR). Skipping."; \
		exit 0; \
	fi; \
	while IFS= read -r file; do \
		echo "Validating $$file"; \
		$(PYTHON) $(VALIDATOR) "$$file"; \
	done <<< "$$files"

test-validator:
	@$(PYTHON) $(VALIDATOR) ./ci/fixtures/valid_output.json

mock-run:
	@chmod +x $(MOCK_RUNNER)
	@if [[ -n "$(TRANSCRIPT)" ]]; then \
		$(MOCK_RUNNER) "$(TRANSCRIPT)"; \
	else \
		./batch_run_master_dev.sh "$(TRANSCRIPTS_DIR)" "$(OUTPUT_DIR)" --mock; \
	fi

test-mock:
	@pytest tests/test_mock_runner.py -v

ci: test-validator validate-outputs
	@echo "CI checks passed."
