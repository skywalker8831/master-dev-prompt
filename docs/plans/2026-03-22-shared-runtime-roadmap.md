# Shared Runtime Reliability Roadmap

**Date:** 2026-03-22  
**Project:** Master Developer Prompt Kit

## Goal

Improve overall architecture reliability by moving prompt loading and strict schema validation into a shared Python runtime module, then reusing that runtime across the validator CLI and FastAPI application.

## Milestone-Based Roadmap

### Milestone 1 — Establish a shared runtime core
- Create a reusable Python module for:
  - prompt loading
  - transcript-to-user-message formatting
  - strict JSON parsing
  - strict schema validation
- Keep the existing `validate_output.py` CLI as a thin wrapper so existing commands continue to work.

**Success criteria**
- Validation logic exists in one importable location.
- Existing `python3 validate_output.py <file>` usage still works.

### Milestone 2 — Enforce strict schema validation in API responses
- Refactor `app.py` to use the shared runtime.
- Make `POST /process` fail with `502` when model output is not valid JSON or fails schema validation.
- Make `POST /process/stream` emit a final success event only for schema-valid output.

**Success criteria**
- API success means the same thing as CLI validator success.
- Streaming endpoint returns validation errors instead of silently returning malformed final objects.

### Milestone 3 — Expand reliability-focused automated tests
- Add tests for shared runtime validation behavior.
- Add FastAPI endpoint tests for:
  - valid output
  - schema-invalid output
  - API key enforcement
  - streaming success/error behavior
- Keep watcher tests passing during the refactor.

**Success criteria**
- Refactor is protected by focused automated tests.
- Runtime contract regressions are caught locally and in CI.

### Milestone 4 — Align local and CI validation
- Update `Makefile` so `make ci` includes Python tests in addition to output validation.
- Repair the GitHub Actions workflow to install dependencies and run the same validation command locally and in CI.

**Success criteria**
- `make ci` is the primary repo validation command.
- GitHub Actions mirrors local validation behavior.

### Milestone 5 — Future consolidation opportunities
- Consider migrating watcher validation fully to in-memory validation paths where appropriate.
- Consider moving more shell-driven behavior into shared Python code if future feature work increases duplication pressure.

**Success criteria**
- Fewer duplicated runtime paths.
- Clear direction for future architecture work without forcing a large one-shot rewrite.

## File-by-File Change Plan

### Implemented in this refactor

#### `master_dev_runtime.py`
- New shared runtime module
- Centralizes:
  - prompt path constants
  - prompt loading
  - transcript message construction
  - strict JSON parsing
  - strict schema validation
  - file-based validation entrypoint

#### `validate_output.py`
- Reduced to a thin CLI wrapper around the shared runtime
- Preserves current command-line behavior and output format

#### `app.py`
- Uses the shared runtime for prompt loading and schema validation
- `POST /process` now rejects schema-invalid model output
- `POST /process/stream` now validates the accumulated final payload before emitting `done`

#### `watcher.py`
- Reuses shared validation logic instead of spawning a separate validator subprocess
- Keeps existing output/log behavior intact while reducing validation duplication

#### `tests/test_master_dev_runtime.py`
- Adds focused tests for reusable validation behavior

#### `tests/test_app.py`
- Adds endpoint tests for strict schema validation and API auth behavior
- Adds streaming tests for success/error end states

#### `Makefile`
- Adds Python test execution to `make ci`

#### `.github/workflows/validate-master-dev-prompt.yml`
- Replaces the malformed combined workflow with one valid workflow
- Installs Python dependencies and runs `make ci`

#### `README.md`
- Documents the shared runtime module
- Documents the Python test command
- Clarifies that API responses are schema-validated

### Likely future files for follow-up milestones

#### `run_master_dev.sh`
- Candidate for future thin-wrapper behavior around shared Python runtime utilities

#### `batch_run_master_dev.sh`
- Candidate for future consolidation if batch orchestration moves into Python

#### `static/index.html`
- Candidate for future UX improvements around stream validation errors

## Validation Plan

- `python3 -m pytest -q`
- `make ci`

## Risks

- Refactoring shared validation logic can subtly change error messages used by existing scripts/tests.
- Adding tests to `make ci` means local validation now depends on installing `requirements.txt` first.

## Mitigations

- Preserve the existing CLI validator interface and output style.
- Keep tests focused on contract-level behavior rather than brittle implementation details.
- Use the same validation entrypoint in both local and CI workflows.
