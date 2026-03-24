from pathlib import Path
from unittest.mock import MagicMock, call, patch

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


# ── process_transcript: non-zero subprocess exit ──────────────────────────────

def test_process_transcript_handles_nonzero_exit(tmp_path):
    from watcher import process_transcript

    txt = tmp_path / "meeting.txt"
    txt.write_text("transcript content")
    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir()
    script = tmp_path / "run_master_dev.sh"

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="fatal error\n")
        process_transcript(txt, outputs_dir, script)

    assert not (outputs_dir / "meeting.json").exists()
    assert not (outputs_dir / "meeting.tmp.json").exists()
    assert (outputs_dir / "meeting.log").read_text() == "fatal error\n"


# ── TranscriptHandler ─────────────────────────────────────────────────────────

def test_transcript_handler_stores_outputs_dir_and_script(tmp_path):
    from watcher import TranscriptHandler

    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir()
    script = tmp_path / "run.sh"
    handler = TranscriptHandler(outputs_dir=outputs_dir, script=script)
    assert handler.outputs_dir == outputs_dir
    assert handler.script == script


def test_transcript_handler_on_created_processes_txt(tmp_path):
    from watcher import TranscriptHandler

    txt = tmp_path / "meeting.txt"
    txt.write_text("transcript content")
    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir()
    script = tmp_path / "run_master_dev.sh"

    handler = TranscriptHandler(outputs_dir=outputs_dir, script=script)

    event = MagicMock()
    event.is_directory = False
    event.src_path = str(txt)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=VALID_OUTPUT, stderr="")
        handler.on_created(event)

    assert mock_run.call_count == 1
    assert (outputs_dir / "meeting.json").exists()


def test_transcript_handler_on_created_ignores_directories(tmp_path):
    from watcher import TranscriptHandler

    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir()
    handler = TranscriptHandler(outputs_dir=outputs_dir)

    event = MagicMock()
    event.is_directory = True
    event.src_path = str(tmp_path / "some_dir")

    with patch("subprocess.run") as mock_run:
        handler.on_created(event)
        mock_run.assert_not_called()


def test_transcript_handler_on_created_skips_non_txt(tmp_path):
    from watcher import TranscriptHandler

    md_file = tmp_path / "notes.md"
    md_file.write_text("content")
    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir()
    handler = TranscriptHandler(outputs_dir=outputs_dir)

    event = MagicMock()
    event.is_directory = False
    event.src_path = str(md_file)

    with patch("subprocess.run") as mock_run:
        handler.on_created(event)
        mock_run.assert_not_called()


# ── main() ────────────────────────────────────────────────────────────────────

def test_main_exits_when_transcripts_dir_missing(tmp_path):
    from watcher import main

    nonexistent = tmp_path / "no_such_dir"
    with patch("sys.argv", ["watcher.py", "--transcripts", str(nonexistent), "--outputs", str(tmp_path / "out")]):
        with pytest.raises(SystemExit) as exc_info:
            main()

    assert exc_info.value.code == 1


def test_main_starts_and_stops_observer(tmp_path):
    from watcher import main

    transcripts = tmp_path / "transcripts"
    transcripts.mkdir()
    outputs = tmp_path / "outputs"

    with patch("sys.argv", ["watcher.py", "--transcripts", str(transcripts), "--outputs", str(outputs)]):
        with patch("watcher.Observer") as mock_observer_cls:
            mock_obs = MagicMock()
            mock_observer_cls.return_value = mock_obs
            with patch("time.sleep", side_effect=KeyboardInterrupt):
                main()

    mock_obs.start.assert_called_once()
    mock_obs.stop.assert_called_once()
    mock_obs.join.assert_called_once()
    assert outputs.is_dir()
