# Autopilot File Watcher Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a file watcher (`watcher.py`) that automatically processes any `.txt` dropped into `transcripts/` and writes the JSON result to `outputs/` — no manual commands needed.

**Architecture:** A Python `watchdog` observer monitors `transcripts/` for file creation events. When a new `.txt` appears, it checks if the output already exists (deduplication), then shells out to `run_master_dev.sh`. All activity is logged to stdout and a per-file `.log`.

**Tech Stack:** Python 3, `watchdog` (filesystem events), `subprocess` (shell out to existing script), `pytest` (tests)

---

## Task 1: Add `watchdog` dependency

**Files:**
- Create: `requirements.txt`

**Step 1: Create requirements.txt**

```
fastapi
uvicorn
anthropic
python-dotenv
watchdog
pytest
```

**Step 2: Install it**

```bash
pip install -r requirements.txt
```

Expected: All packages install without error.

**Step 3: Verify watchdog is available**

```bash
python3 -c "import watchdog; print(watchdog.__version__)"
```

Expected: Prints a version number (e.g. `3.x.x`).

**Step 4: Commit**

```bash
git add requirements.txt
git commit -m "chore: add requirements.txt with watchdog"
```

---

## Task 2: Write failing tests for watcher logic

**Files:**
- Create: `tests/test_watcher.py`
- Create: `tests/__init__.py` (empty)

**Step 1: Create `tests/__init__.py`**

```python
```
(empty file)

**Step 2: Write the failing tests in `tests/test_watcher.py`**

```python
import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

# We'll import from watcher once it exists
# from watcher import should_process, get_output_path, process_transcript


def test_should_process_returns_true_for_new_txt(tmp_path):
    from watcher import should_process
    txt = tmp_path / "meeting.txt"
    txt.write_text("hello")
    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir()
    assert should_process(txt, outputs_dir) is True


def test_should_process_returns_false_if_json_exists(tmp_path):
    from watcher import should_process
    txt = tmp_path / "meeting.txt"
    txt.write_text("hello")
    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir()
    (outputs_dir / "meeting.json").write_text("{}")
    assert should_process(txt, outputs_dir) is False


def test_should_process_returns_false_for_non_txt(tmp_path):
    from watcher import should_process
    f = tmp_path / "meeting.md"
    f.write_text("hello")
    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir()
    assert should_process(f, outputs_dir) is False


def test_get_output_path(tmp_path):
    from watcher import get_output_path
    txt = tmp_path / "my-meeting.txt"
    outputs_dir = tmp_path / "outputs"
    result = get_output_path(txt, outputs_dir)
    assert result == outputs_dir / "my-meeting.json"


def test_process_transcript_calls_script(tmp_path):
    from watcher import process_transcript
    txt = tmp_path / "meeting.txt"
    txt.write_text("transcript content")
    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir()
    script = tmp_path / "run_master_dev.sh"
    script.write_text("#!/bin/bash\necho '{}'")
    script.chmod(0o755)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="{}", stderr="")
        process_transcript(txt, outputs_dir, script)
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert str(script) in args
        assert str(txt) in args
```

**Step 3: Run to verify tests fail**

```bash
pytest tests/test_watcher.py -v
```

Expected: All 5 tests fail with `ModuleNotFoundError: No module named 'watcher'`

**Step 4: Commit the failing tests**

```bash
git add tests/
git commit -m "test: add failing tests for watcher logic"
```

---

## Task 3: Implement `watcher.py`

**Files:**
- Create: `watcher.py`

**Step 1: Write the implementation**

```python
#!/usr/bin/env python3
"""
watcher.py — Autopilot file watcher for Master Developer Prompt Kit.

Watches transcripts/ for new .txt files and automatically runs
run_master_dev.sh, writing output to outputs/.

Usage:
    python3 watcher.py
    python3 watcher.py --transcripts ./transcripts --outputs ./outputs
"""

import argparse
import logging
import subprocess
import sys
import time
from pathlib import Path

from watchdog.events import FileCreatedEvent, FileSystemEventHandler
from watchdog.observers import Observer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

_SCRIPT = Path(__file__).parent / "run_master_dev.sh"


def should_process(txt_path: Path, outputs_dir: Path) -> bool:
    """Return True if txt_path is a .txt without a corresponding .json output."""
    if txt_path.suffix != ".txt":
        return False
    output = get_output_path(txt_path, outputs_dir)
    return not output.exists()


def get_output_path(txt_path: Path, outputs_dir: Path) -> Path:
    """Return the expected .json output path for a given .txt transcript."""
    return outputs_dir / (txt_path.stem + ".json")


def process_transcript(txt_path: Path, outputs_dir: Path, script: Path = _SCRIPT) -> None:
    """Run run_master_dev.sh on txt_path, saving output to outputs_dir."""
    output_json = get_output_path(txt_path, outputs_dir)
    log_file = outputs_dir / (txt_path.stem + ".log")

    log.info("Processing: %s → %s", txt_path.name, output_json.name)

    result = subprocess.run(
        [str(script), str(txt_path)],
        capture_output=True,
        text=True,
    )

    log_file.write_text(result.stderr)

    if result.returncode != 0:
        log.error("Failed: %s (exit %d). See %s", txt_path.name, result.returncode, log_file)
        return

    output_json.write_text(result.stdout)
    log.info("Done: %s", output_json)


class TranscriptHandler(FileSystemEventHandler):
    def __init__(self, outputs_dir: Path, script: Path = _SCRIPT):
        self.outputs_dir = outputs_dir
        self.script = script

    def on_created(self, event: FileCreatedEvent) -> None:
        if event.is_directory:
            return
        txt = Path(event.src_path)
        if should_process(txt, self.outputs_dir):
            process_transcript(txt, self.outputs_dir, self.script)


def main() -> None:
    parser = argparse.ArgumentParser(description="Autopilot watcher for transcript processing")
    parser.add_argument("--transcripts", default="transcripts", help="Directory to watch")
    parser.add_argument("--outputs", default="outputs", help="Directory for output JSON files")
    args = parser.parse_args()

    transcripts_dir = Path(args.transcripts).resolve()
    outputs_dir = Path(args.outputs).resolve()

    if not transcripts_dir.exists():
        log.error("Transcripts directory not found: %s", transcripts_dir)
        sys.exit(1)

    outputs_dir.mkdir(parents=True, exist_ok=True)

    log.info("Watching %s for new transcripts...", transcripts_dir)
    log.info("Outputs will be written to %s", outputs_dir)

    handler = TranscriptHandler(outputs_dir=outputs_dir)
    observer = Observer()
    observer.schedule(handler, str(transcripts_dir), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Stopping watcher.")
        observer.stop()

    observer.join()


if __name__ == "__main__":
    main()
```

**Step 2: Run the tests**

```bash
pytest tests/test_watcher.py -v
```

Expected: All 5 tests PASS.

**Step 3: Commit**

```bash
git add watcher.py
git commit -m "feat: add autopilot file watcher"
```

---

## Task 4: Smoke test the watcher manually

**Step 1: Start the watcher**

```bash
python3 watcher.py
```

Expected output:
```
2026-03-01 12:00:00 [INFO] Watching /path/to/transcripts for new transcripts...
2026-03-01 12:00:00 [INFO] Outputs will be written to /path/to/outputs
```

**Step 2: In a second terminal, drop a transcript**

```bash
cp sample_transcript.txt transcripts/smoke-test.txt
```

Expected watcher output within seconds:
```
2026-03-01 12:00:05 [INFO] Processing: smoke-test.txt → smoke-test.json
2026-03-01 12:00:15 [INFO] Done: /path/to/outputs/smoke-test.json
```

**Step 3: Verify the output**

```bash
python3 validate_output.py outputs/smoke-test.json
```

Expected: Validation passes.

**Step 4: Stop the watcher with Ctrl+C**

Expected:
```
2026-03-01 12:00:20 [INFO] Stopping watcher.
```

---

## Task 5: Update README.md

**Files:**
- Modify: `README.md`

**Step 1: Add a new section to README.md after the "FastAPI Server" section**

Add this markdown block:

```markdown
---

## Autopilot Watcher

Run the watcher to automatically process any transcript dropped into `transcripts/`:

```bash
python3 watcher.py
```

Then drop any `.txt` file into `transcripts/` — the JSON output appears in `outputs/` automatically.

Custom directories:

```bash
python3 watcher.py --transcripts ./my-transcripts --outputs ./my-outputs
```

Stop with `Ctrl+C`. Files already processed (with a matching `.json` in `outputs/`) are skipped automatically.
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add autopilot watcher usage to README"
```

---

## Done

Run the full test suite one final time to confirm everything is green:

```bash
pytest tests/ -v
```

Then start your autopilot:

```bash
python3 watcher.py
```
