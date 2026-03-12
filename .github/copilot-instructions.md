# Copilot instructions for this repository

This repository packages the `master_dev_prompt.txt` prompt, validation scripts, batch tooling, a small FastAPI server, and sample transcripts/outputs.

## Key files
- `master_dev_prompt.txt` is the canonical prompt definition. Preserve its output schema and allowed enum values.
- `validate_output.py` enforces the JSON contract used by generated outputs.
- `run_master_dev.sh` and `batch_run_master_dev.sh` are the main CLI entrypoints.
- `app.py` serves the HTTP API and the UI in `static/index.html`.
- `.github/workflows/validate-master-dev-prompt.yml` and `Makefile` define the validation flow used in CI.

## Working conventions
- Keep changes minimal and focused on the requested task.
- Reuse the existing shell, Python, and FastAPI patterns already present in the repository.
- Do not change the output JSON shape unless the task explicitly requires it.
- Do not add new dependencies or tools unless they are required to solve the task.
- Avoid editing generated outputs unless a task specifically requires updating fixtures or samples.

## Validation
- Run `make ci` for the repository's standard validation path.
- If you change only the validator behavior, at minimum run `python3 validate_output.py ./ci/fixtures/valid_output.json`.
- If you change batch or prompt behavior, validate produced JSON files with `make validate-outputs`.

## Repository-specific notes
- Mock-friendly flows already exist; prefer `--mock` or existing sample fixtures instead of introducing ad hoc test harnesses.
- When changing the server or UI, keep the terminal-style UI and current API routes intact unless the task says otherwise.
