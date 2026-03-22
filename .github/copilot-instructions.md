# Copilot Instructions for master-dev-prompt

## Project Overview

This repository is the **Master Developer Prompt Kit** — a toolkit for processing developer transcripts through a structured master prompt, validating outputs against a strict JSON schema, and serving results via a FastAPI application.

## Architecture

- **`master_dev_runtime.py`** — Shared Python runtime module centralizing prompt loading, transcript formatting, JSON parsing, and schema validation. All other components import from here.
- **`validate_output.py`** — Thin CLI wrapper around the shared runtime for command-line validation.
- **`app.py`** — FastAPI application with `/process` and `/process/stream` endpoints. Uses the shared runtime for prompt loading and strict schema validation.
- **`watcher.py`** — File watcher that monitors transcript directories and triggers processing/validation.
- **`master_dev_prompt.txt`** — The master prompt template.
- **`Makefile`** — Primary build/validation interface. `make ci` runs all validation and tests.

## Key Conventions

1. **Shared runtime first**: All validation, prompt loading, and schema logic lives in `master_dev_runtime.py`. Never duplicate this logic.
2. **Strict JSON schema validation**: API responses and CLI outputs must pass schema validation. Invalid JSON or schema failures should raise errors, not be silently ignored.
3. **CI parity**: `make ci` must work identically locally and in GitHub Actions. The workflow is defined in `.github/workflows/validate-master-dev-prompt.yml`.
4. **Python 3.11+**: Use modern Python conventions. Dependencies are in `requirements.txt`.
5. **Tests**: Located in `tests/`. Run with `python3 -m pytest -q`. Tests cover both the shared runtime and FastAPI endpoints.

## When Making Changes

- Run `make ci` before committing to verify nothing is broken.
- If adding validation logic, add it to `master_dev_runtime.py` and write a test in `tests/`.
- If modifying API behavior, update both `app.py` and the corresponding test in `tests/test_app.py`.
- Keep shell scripts (`run_master_dev.sh`, `batch_run_master_dev.sh`) as thin wrappers.
- Do not introduce new workflow YAML files without ensuring they are valid standalone YAML (no concatenated documents).

## File Structure

```
.github/
  agents/          # Copilot agent definitions
  workflows/       # GitHub Actions CI workflows
  CODEOWNERS       # Code ownership rules
ci/fixtures/       # CI test fixtures
docs/plans/        # Architecture roadmaps and plans
outputs/           # Processed output files
static/            # Web UI assets
tests/             # Python tests (pytest)
transcripts/       # Input transcript files
```
