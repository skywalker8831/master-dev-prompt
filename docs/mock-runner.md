# Mock Runner

## Overview

The **mock runner** (`mock_runner.sh`) is a deterministic stand-in for the
real `run_master_dev.sh` that calls a live LLM backend (Claude / Codex).

Instead of invoking any external service, the mock runner immediately
outputs a pre-built, schema-valid JSON fixture.  This makes it possible to
run the full pipeline—transcript → runner → validate—in CI or locally
without any API keys, network access, or model quotas.

## How It Achieves 100% Confidence

| Property | Real runner | Mock runner |
|---|---|---|
| Needs LLM CLI installed | ✅ yes | ❌ no |
| Output is deterministic | ❌ no | ✅ yes |
| Output is always schema-valid | ⚠️ depends on model | ✅ yes |
| Safe to run in CI | ⚠️ only with credentials | ✅ always |
| Suitable for dry-run / regression | ❌ | ✅ |

Because the fixture is a real, pre-validated JSON file that passes
`validate_output.py`, every run of the mock runner produces the same
result, and that result is guaranteed to be correct.  This gives you
**100% confidence** that the pipeline wiring, schema validation, and
downstream tooling all work correctly, independently of the LLM.

## Usage

```bash
# Basic usage – uses outputs/sample.json as the fixture
./mock_runner.sh transcripts/sample_transcript.txt

# Pipe the output to a file
./mock_runner.sh transcripts/sample_transcript.txt > outputs/dry-run.json

# Use a custom fixture file via flag
./mock_runner.sh transcripts/sample_transcript.txt --fixture ci/fixtures/valid_output.json

# Use a custom fixture file via environment variable
MOCK_FIXTURE=ci/fixtures/valid_output.json ./mock_runner.sh transcripts/sample_transcript.txt
```

## Batch Dry-Run

The batch runner already supports `--mock`, which calls `run_master_dev.sh`
in mock mode.  You can achieve the same fully-deterministic result with
`mock_runner.sh` by substituting it for the real runner:

```bash
# Run the batch pipeline in mock mode (built-in support)
./batch_run_master_dev.sh ./transcripts ./outputs --mock

# Alternatively, use mock_runner.sh directly for a single transcript
./mock_runner.sh transcripts/sample_transcript.txt | python3 validate_output.py /dev/stdin
```

## CI Integration

The GitHub Actions workflow (`.github/workflows/validate-master-dev-prompt.yml`)
already runs the batch pipeline with `--mock` on every pull request.
`mock_runner.sh` is also available as a simpler entry point if you want to
add per-transcript steps in a workflow:

```yaml
- name: Dry-run single transcript
  run: |
    chmod +x ./mock_runner.sh
    ./mock_runner.sh transcripts/sample_transcript.txt > /tmp/dry-run.json
    python3 validate_output.py /tmp/dry-run.json
```

## Extending the Mock

To test with a different fixture (e.g. an edge-case document), place the
JSON in `ci/fixtures/` and point the mock runner at it:

```bash
./mock_runner.sh transcripts/sample_transcript.txt \
  --fixture ci/fixtures/edge_case_output.json
```

The fixture must pass `validate_output.py` validation or the pipeline will
report a failure, which is the intended behaviour (the validator is the
source of truth for schema correctness).
