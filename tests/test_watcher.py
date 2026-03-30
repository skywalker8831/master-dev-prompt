from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "ci" / "fixtures" / "valid_output.json"
VALID_OUTPUT = FIXTURE_PATH.read_text(encoding="utf-8")


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
        mock_run.return_value = MagicMock(returncode=0, stdout=VALID_OUTPUT, stderr="")
        process_transcript(txt, outputs_dir, script)
        assert mock_run.call_count == 1
        runner_args = mock_run.call_args_list[0][0][0]
        assert runner_args == [str(script), str(txt)]
        assert (outputs_dir / "meeting.json").read_text() == VALID_OUTPUT


def test_process_transcript_writes_invalid_output_on_schema_failure(tmp_path):
    from watcher import process_transcript

    txt = tmp_path / "meeting.txt"
    txt.write_text("transcript content")
    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir()
    script = tmp_path / "run_master_dev.sh"
    script.write_text("#!/bin/bash\necho '{}'")
    script.chmod(0o755)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="{}", stderr="runner stderr\n")

        process_transcript(txt, outputs_dir, script)

    assert not (outputs_dir / "meeting.json").exists()
    assert not (outputs_dir / "meeting.tmp.json").exists()
    assert (outputs_dir / "meeting.invalid.json").read_text() == "{}"
    log_text = (outputs_dir / "meeting.log").read_text()
    assert "runner stderr" in log_text
    assert "=== validation ===" in log_text
    assert "INVALID: $ keys mismatch" in log_text


# ── Test process_transcript failure scenarios ─────────────────────────────────

def test_process_transcript_handles_script_failure(tmp_path):
    from watcher import process_transcript
    
    txt = tmp_path / "meeting.txt"
    txt.write_text("transcript content")
    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir()
    script = tmp_path / "run_master_dev.sh"
    script.write_text("#!/bin/bash\nexit 1")
    script.chmod(0o755)
    
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Script error\n")
        
        process_transcript(txt, outputs_dir, script)
    
    # Should not create output file when script fails
    assert not (outputs_dir / "meeting.json").exists()
    assert not (outputs_dir / "meeting.tmp.json").exists()
    assert not (outputs_dir / "meeting.invalid.json").exists()
    # Log file should contain stderr
    log_text = (outputs_dir / "meeting.log").read_text()
    assert "Script error" in log_text


def test_process_transcript_logs_valid_output(tmp_path):
    from watcher import process_transcript
    
    txt = tmp_path / "meeting.txt"
    txt.write_text("transcript content")
    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir()
    script = tmp_path / "run_master_dev.sh"
    script.write_text("#!/bin/bash\necho '{}'")
    script.chmod(0o755)
    
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=VALID_OUTPUT, stderr="")
        
        process_transcript(txt, outputs_dir, script)
    
    # Check that log contains validation success
    log_text = (outputs_dir / "meeting.log").read_text()
    assert "=== validation ===" in log_text
    assert "VALID:" in log_text


# ── Test TranscriptHandler ────────────────────────────────────────────────────

def test_transcript_handler_ignores_directories(tmp_path):
    from watcher import TranscriptHandler
    from watchdog.events import DirCreatedEvent
    
    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir()
    handler = TranscriptHandler(outputs_dir=outputs_dir)
    
    # Create a directory event
    dir_event = DirCreatedEvent(str(tmp_path / "subdir"))
    
    # This should not raise and should not process anything
    handler.on_created(dir_event)


def test_transcript_handler_processes_new_txt_file(tmp_path):
    from watcher import TranscriptHandler
    from watchdog.events import FileCreatedEvent
    
    txt = tmp_path / "meeting.txt"
    txt.write_text("transcript content")
    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir()
    script = tmp_path / "run_master_dev.sh"
    script.write_text("#!/bin/bash\necho '{}'")
    script.chmod(0o755)
    
    handler = TranscriptHandler(outputs_dir=outputs_dir, script=script)
    
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=VALID_OUTPUT, stderr="")
        
        event = FileCreatedEvent(str(txt))
        handler.on_created(event)
    
    # Should have called the script
    assert mock_run.call_count == 1


def test_transcript_handler_skips_non_txt_file(tmp_path):
    from watcher import TranscriptHandler
    from watchdog.events import FileCreatedEvent
    
    md_file = tmp_path / "notes.md"
    md_file.write_text("some notes")
    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir()
    script = tmp_path / "run_master_dev.sh"
    
    handler = TranscriptHandler(outputs_dir=outputs_dir, script=script)
    
    with patch("subprocess.run") as mock_run:
        event = FileCreatedEvent(str(md_file))
        handler.on_created(event)
    
    # Should not have called the script for non-txt files
    assert mock_run.call_count == 0


def test_transcript_handler_skips_already_processed(tmp_path):
    from watcher import TranscriptHandler
    from watchdog.events import FileCreatedEvent
    
    txt = tmp_path / "meeting.txt"
    txt.write_text("transcript content")
    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir()
    # Pre-create the output file
    (outputs_dir / "meeting.json").write_text("{}")
    script = tmp_path / "run_master_dev.sh"
    
    handler = TranscriptHandler(outputs_dir=outputs_dir, script=script)
    
    with patch("subprocess.run") as mock_run:
        event = FileCreatedEvent(str(txt))
        handler.on_created(event)
    
    # Should not have called the script for already processed files
    assert mock_run.call_count == 0


# ── Test get_output_path edge cases ───────────────────────────────────────────

def test_get_output_path_handles_hyphenated_name(tmp_path):
    from watcher import get_output_path
    txt = tmp_path / "my-long-meeting-name.txt"
    outputs_dir = tmp_path / "outputs"
    result = get_output_path(txt, outputs_dir)
    assert result == outputs_dir / "my-long-meeting-name.json"


def test_get_output_path_handles_underscored_name(tmp_path):
    from watcher import get_output_path
    txt = tmp_path / "meeting_2024_01_15.txt"
    outputs_dir = tmp_path / "outputs"
    result = get_output_path(txt, outputs_dir)
    assert result == outputs_dir / "meeting_2024_01_15.json"


# ── Test should_process edge cases ────────────────────────────────────────────

def test_should_process_returns_true_for_txt_in_nested_path(tmp_path):
    from watcher import should_process
    nested_dir = tmp_path / "nested" / "dir"
    nested_dir.mkdir(parents=True)
    txt = nested_dir / "meeting.txt"
    txt.write_text("hello")
    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir()
    assert should_process(txt, outputs_dir) is True


def test_should_process_handles_uppercase_txt_extension(tmp_path):
    from watcher import should_process
    txt = tmp_path / "meeting.TXT"
    txt.write_text("hello")
    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir()
    # Python's Path.suffix preserves case
    assert should_process(txt, outputs_dir) is False  # .TXT != .txt


# ── Test main function ────────────────────────────────────────────────────────

def test_main_exits_when_transcripts_dir_not_found(tmp_path):
    import sys
    from unittest.mock import patch as mock_patch
    
    with mock_patch.object(sys, "argv", ["watcher.py", "--transcripts", str(tmp_path / "nonexistent")]):
        with pytest.raises(SystemExit) as exc_info:
            from watcher import main
            main()
    
    assert exc_info.value.code == 1


def test_main_creates_outputs_dir_if_missing(tmp_path):
    import sys
    import threading
    from unittest.mock import patch as mock_patch
    
    transcripts_dir = tmp_path / "transcripts"
    transcripts_dir.mkdir()
    outputs_dir = tmp_path / "outputs"
    
    # Use threading to stop the watcher after a short time
    def stop_after_delay():
        import time
        time.sleep(0.1)
        # Raise KeyboardInterrupt in main thread
        import _thread
        _thread.interrupt_main()
    
    with mock_patch.object(sys, "argv", ["watcher.py", "--transcripts", str(transcripts_dir), "--outputs", str(outputs_dir)]):
        stopper = threading.Thread(target=stop_after_delay, daemon=True)
        stopper.start()
        
        from watcher import main
        
        # Main should catch KeyboardInterrupt and exit gracefully
        try:
            main()
        except KeyboardInterrupt:
            pass
    
    # The outputs directory should have been created
    assert outputs_dir.exists()


def test_main_uses_default_directories(tmp_path, monkeypatch):
    import os
    import sys
    import threading
    from unittest.mock import patch as mock_patch
    
    # Change to tmp_path and create required directories
    monkeypatch.chdir(tmp_path)
    (tmp_path / "transcripts").mkdir()
    (tmp_path / "outputs").mkdir()
    
    def stop_after_delay():
        import time
        time.sleep(0.1)
        import _thread
        _thread.interrupt_main()
    
    with mock_patch.object(sys, "argv", ["watcher.py"]):
        stopper = threading.Thread(target=stop_after_delay, daemon=True)
        stopper.start()
        
        from watcher import main
        
        try:
            main()
        except KeyboardInterrupt:
            pass
    
    # Should have run without error with default directories
