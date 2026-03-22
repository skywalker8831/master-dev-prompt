# Contributing to Master Developer Prompt Kit

Thank you for your interest in contributing!

## Getting Started

1. **Fork** the repository and clone your fork
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes
4. Run CI checks locally: `make ci`
5. Push and open a Pull Request against `main`

## Development Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Run all tests
python3 -m pytest -q

# Run full CI check (same as GitHub Actions)
make ci
```

## Project Structure

```
.
├── master_dev_prompt.txt      # Core system prompt
├── master_dev_runtime.py      # Python runtime for prompt + validation
├── validate_output.py         # JSON schema validator
├── run_master_dev.sh          # CLI runner script
├── batch_run_master_dev.sh    # Batch processing script
├── watcher.py                 # Autopilot file watcher
├── app.py                     # FastAPI server
├── tests/                     # pytest test suite
├── ci/fixtures/               # CI test fixtures
├── transcripts/               # Sample transcripts
├── outputs/                   # Generated outputs (gitignored)
└── .github/workflows/         # CI/CD workflows
```

## Workflows

| Workflow | Purpose |
|---|---|
| `validate-master-dev-prompt.yml` | Runs `make ci` on every push/PR to `main` |
| `copilot-autofix.yml` | GitHub Copilot automated suggestions |
| `cleanup-workflow-runs.yml` | Weekly cleanup of old run history |

## Code Style

- Python: follow PEP 8; use type hints where practical
- Shell scripts: use `set -euo pipefail` at the top
- Keep prompt changes backward-compatible with the JSON schema

## Branch Conventions

- Default branch: `main`
- Feature branches: `feature/<name>` or `fix/<name>`
- Copilot branches are ephemeral and auto-deleted after merge
- Do not force-push to `main`

## Reporting Issues

Open an issue with a clear title and description. For accidental/test issues, they will be closed with a note.

## License

See [LICENSE](LICENSE) if present, otherwise all rights reserved by the repository owner.
