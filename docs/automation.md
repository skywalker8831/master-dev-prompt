# Automation Guide

This guide covers the two automated processing modes included in the Master Developer Prompt Kit: the **batch runner** and the **autopilot watcher**.

---

## Batch Runner (`batch_run_master_dev.sh`)

The batch runner processes every `.txt` transcript in a directory in one pass, validates each output against the schema, and writes results to an output directory.

### Usage

```bash
chmod +x batch_run_master_dev.sh
./batch_run_master_dev.sh [TRANSCRIPTS_DIR] [OUTPUT_DIR] [--mock]
```

| Argument | Default | Description |
|----------|---------|-------------|
| `TRANSCRIPTS_DIR` | `./transcripts` | Directory containing `.txt` transcript files |
| `OUTPUT_DIR` | `./outputs` | Directory where JSON results are written |
| `--mock` | _(unset)_ | Use mock output instead of a live model CLI |

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MOCK_OUTPUT` | `0` | Set to `1` to enable mock mode (same as passing `--mock`) |

### Output files

For each transcript `<name>.txt` the runner produces:

| File | Condition | Description |
|------|-----------|-------------|
| `outputs/<name>.json` | Run + validation passed | Final validated output |
| `outputs/<name>.invalid.json` | Run passed, validation failed | Raw output that did not pass the schema check |
| `outputs/<name>.log` | Always | stderr from the runner and validator |

### Exit codes

| Code | Meaning |
|------|---------|
| `0` | All transcripts passed |
| `1` | One or more transcripts failed |

### Examples

Process all transcripts in the default directory:

```bash
./batch_run_master_dev.sh
```

Process a custom directory and write results to a custom output folder:

```bash
./batch_run_master_dev.sh ./my_transcripts ./my_outputs
```

Run in mock mode (no model CLI required):

```bash
./batch_run_master_dev.sh ./transcripts ./outputs --mock
# or via environment variable
MOCK_OUTPUT=1 ./batch_run_master_dev.sh
```

Validate all generated outputs afterwards:

```bash
make validate-outputs OUTPUT_DIR=./my_outputs
```

---

## Autopilot Watcher (`watcher.py`)

The watcher monitors a directory for new `.txt` files and automatically processes each one through `run_master_dev.sh` as soon as it appears. It is intended for continuous, hands-free operation.

### Requirements

```bash
pip install -r requirements.txt   # includes watchdog
```

### Usage

```bash
python3 watcher.py [--transcripts DIR] [--outputs DIR]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--transcripts` | `transcripts` | Directory to watch for new `.txt` files |
| `--outputs` | `outputs` | Directory where JSON results are written |

### Behavior

- When a new `.txt` file is created in the watched directory the watcher immediately invokes `run_master_dev.sh` on it.
- If a corresponding `.json` already exists in the output directory the file is **skipped** (deduplication).
- A per-file `.log` is written to the output directory containing stderr from the script.
- Only the watched directory is monitored; sub-directories are ignored.

### Examples

Watch the default directories:

```bash
python3 watcher.py
```

Watch custom directories:

```bash
python3 watcher.py --transcripts ./my-transcripts --outputs ./my-outputs
```

Drop a transcript to trigger automatic processing:

```bash
cp sample_transcript.txt transcripts/demo.txt
# → outputs/demo.json appears automatically
```

Stop the watcher:

```bash
# Press Ctrl+C in the terminal running watcher.py
```

### Logging

All activity is printed to stdout with timestamps:

```
2026-03-01 12:00:00 [INFO] Watching /path/to/transcripts for new transcripts...
2026-03-01 12:00:00 [INFO] Outputs will be written to /path/to/outputs
2026-03-01 12:00:05 [INFO] Processing: demo.txt → demo.json
2026-03-01 12:00:15 [INFO] Done: /path/to/outputs/demo.json
```

Errors are logged at `ERROR` level and include the exit code and the path to the `.log` file for the failed transcript.

---

## Choosing between batch and watcher

| Scenario | Recommended tool |
|----------|-----------------|
| Process a fixed set of transcripts once | `batch_run_master_dev.sh` |
| Continuously ingest transcripts as they arrive | `watcher.py` |
| CI/CD pipeline | `batch_run_master_dev.sh` (or `make ci`) |
| Local development / live demo | `watcher.py` |
