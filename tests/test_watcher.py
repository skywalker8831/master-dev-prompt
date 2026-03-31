from pathlib import Path
from unittest.mock import MagicMock, patch

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


def test_process_transcript_nonzero_returncode_leaves_no_json(tmp_path):
    from watcher import process_transcript

    txt = tmp_path / "fail.txt"
    txt.write_text("transcript content")
    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir()
    script = tmp_path / "run_master_dev.sh"
    script.write_text("#!/bin/bash\nexit 1")
    script.chmod(0o755)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="script failed\n")
        process_transcript(txt, outputs_dir, script)

    assert not (outputs_dir / "fail.json").exists()
    assert not (outputs_dir / "fail.tmp.json").exists()
    assert not (outputs_dir / "fail.invalid.json").exists()
    assert "script failed" in (outputs_dir / "fail.log").read_text()


def test_process_transcript_writes_log_entry_on_success(tmp_path):
    from watcher import process_transcript

    txt = tmp_path / "success.txt"
    txt.write_text("transcript content")
    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir()
    # The script path must exist so watcher can pass it to subprocess; actual
    # execution is mocked so the script body does not matter.
    script = tmp_path / "run_master_dev.sh"
    script.write_text("#!/bin/bash\nexit 0")
    script.chmod(0o755)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=VALID_OUTPUT, stderr="ok\n")
        process_transcript(txt, outputs_dir, script)

    log_text = (outputs_dir / "success.log").read_text()
    assert "=== validation ===" in log_text
    assert "VALID" in log_text
    assert (outputs_dir / "success.json").exists()


# ── TranscriptHandler ─────────────────────────────────────────────────────────

def test_transcript_handler_on_created_ignores_directory_event(tmp_path):
    from watchdog.events import FileCreatedEvent
    from watcher import TranscriptHandler

    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir()
    handler = TranscriptHandler(outputs_dir=outputs_dir)

    event = MagicMock(spec=FileCreatedEvent)
    event.is_directory = True
    event.src_path = str(tmp_path / "some_dir")

    with patch("watcher.process_transcript") as mock_proc:
        handler.on_created(event)
        mock_proc.assert_not_called()


def test_transcript_handler_on_created_ignores_non_txt(tmp_path):
    from watchdog.events import FileCreatedEvent
    from watcher import TranscriptHandler

    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir()
    (tmp_path / "notes.md").write_text("notes")
    handler = TranscriptHandler(outputs_dir=outputs_dir)

    event = MagicMock(spec=FileCreatedEvent)
    event.is_directory = False
    event.src_path = str(tmp_path / "notes.md")

    with patch("watcher.process_transcript") as mock_proc:
        handler.on_created(event)
        mock_proc.assert_not_called()


def test_transcript_handler_on_created_processes_new_txt(tmp_path):
    from watchdog.events import FileCreatedEvent
    from watcher import TranscriptHandler

    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir()
    txt = tmp_path / "meeting.txt"
    txt.write_text("transcript content")
    handler = TranscriptHandler(outputs_dir=outputs_dir)

    event = MagicMock(spec=FileCreatedEvent)
    event.is_directory = False
    event.src_path = str(txt)

    with patch("watcher.process_transcript") as mock_proc:
        handler.on_created(event)
        mock_proc.assert_called_once()
        call_args = mock_proc.call_args[0]
        assert call_args[0] == txt
        assert call_args[1] == outputs_dir


def test_transcript_handler_on_created_skips_already_processed(tmp_path):
    from watchdog.events import FileCreatedEvent
    from watcher import TranscriptHandler

    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir()
    txt = tmp_path / "done.txt"
    txt.write_text("transcript content")
    # Simulate that output already exists
    (outputs_dir / "done.json").write_text("{}")
    handler = TranscriptHandler(outputs_dir=outputs_dir)

    event = MagicMock(spec=FileCreatedEvent)
    event.is_directory = False
    event.src_path = str(txt)

    with patch("watcher.process_transcript") as mock_proc:
        handler.on_created(event)
        mock_proc.assert_not_called()
