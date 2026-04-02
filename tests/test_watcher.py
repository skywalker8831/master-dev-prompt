import sys
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


def test_process_transcript_handles_nonzero_returncode(tmp_path):
    from watcher import process_transcript

    txt = tmp_path / "meeting.txt"
    txt.write_text("transcript content")
    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir()
    script = tmp_path / "run_master_dev.sh"
    script.write_text("#!/bin/bash\nexit 1")
    script.chmod(0o755)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error message\n")
        process_transcript(txt, outputs_dir, script)

    assert not (outputs_dir / "meeting.json").exists()
    assert not (outputs_dir / "meeting.tmp.json").exists()
    log_text = (outputs_dir / "meeting.log").read_text()
    assert "error message" in log_text


def test_transcript_handler_on_created_skips_directory_events(tmp_path):
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


def test_transcript_handler_on_created_skips_non_txt_files(tmp_path):
    from watchdog.events import FileCreatedEvent
    from watcher import TranscriptHandler

    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir()
    handler = TranscriptHandler(outputs_dir=outputs_dir)

    md_file = tmp_path / "notes.md"
    md_file.write_text("hello")
    event = MagicMock(spec=FileCreatedEvent)
    event.is_directory = False
    event.src_path = str(md_file)

    with patch("watcher.process_transcript") as mock_proc:
        handler.on_created(event)
        mock_proc.assert_not_called()


def test_transcript_handler_on_created_processes_txt_file(tmp_path):
    from watchdog.events import FileCreatedEvent
    from watcher import TranscriptHandler

    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir()
    handler = TranscriptHandler(outputs_dir=outputs_dir)

    txt_file = tmp_path / "new_meeting.txt"
    txt_file.write_text("hello")
    event = MagicMock(spec=FileCreatedEvent)
    event.is_directory = False
    event.src_path = str(txt_file)

    with patch("watcher.process_transcript") as mock_proc:
        handler.on_created(event)
        mock_proc.assert_called_once_with(txt_file, outputs_dir, handler.script)


def test_main_exits_when_transcripts_dir_missing(tmp_path):
    from watcher import main

    missing_dir = tmp_path / "no_transcripts"
    with patch("sys.argv", ["watcher.py", "--transcripts", str(missing_dir), "--outputs", str(tmp_path / "out")]):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code == 1


def test_main_starts_and_stops_on_keyboard_interrupt(tmp_path):
    from watcher import main

    transcripts_dir = tmp_path / "transcripts"
    transcripts_dir.mkdir()
    outputs_dir = tmp_path / "outputs"

    mock_observer = MagicMock()
    mock_observer.start.return_value = None
    mock_observer.stop.return_value = None
    mock_observer.join.return_value = None

    def _fake_sleep(_):
        raise KeyboardInterrupt

    with patch("sys.argv", ["watcher.py", "--transcripts", str(transcripts_dir), "--outputs", str(outputs_dir)]):
        with patch("watcher.Observer", return_value=mock_observer):
            with patch("time.sleep", side_effect=_fake_sleep):
                main()

    mock_observer.start.assert_called_once()
    mock_observer.stop.assert_called_once()
    mock_observer.join.assert_called_once()
