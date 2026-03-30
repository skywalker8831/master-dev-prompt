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


def test_process_transcript_logs_and_returns_on_failure(tmp_path):
    from watcher import process_transcript

    txt = tmp_path / "meeting.txt"
    txt.write_text("transcript content")
    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir()
    script = tmp_path / "run_master_dev.sh"
    script.write_text("#!/bin/bash\necho 'should not run'")
    script.chmod(0o755)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="ignored", stderr="boom\n")

        process_transcript(txt, outputs_dir, script)

    assert not (outputs_dir / "meeting.json").exists()
    assert not (outputs_dir / "meeting.tmp.json").exists()
    assert not (outputs_dir / "meeting.invalid.json").exists()
    log_text = (outputs_dir / "meeting.log").read_text()
    assert "boom" in log_text


def test_transcript_handler_ignores_directories(monkeypatch, tmp_path):
    from watcher import TranscriptHandler

    handler = TranscriptHandler(outputs_dir=tmp_path)
    mock_process = MagicMock()
    monkeypatch.setattr("watcher.process_transcript", mock_process)

    handler.on_created(MagicMock(is_directory=True, src_path=str(tmp_path / "new.txt")))

    mock_process.assert_not_called()


def test_transcript_handler_processes_new_txt(monkeypatch, tmp_path):
    from watcher import TranscriptHandler

    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir()
    script = tmp_path / "run_master_dev.sh"
    handler = TranscriptHandler(outputs_dir=outputs_dir, script=script)
    mock_process = MagicMock()
    monkeypatch.setattr("watcher.process_transcript", mock_process)

    txt = tmp_path / "meeting.txt"
    txt.write_text("hello")

    handler.on_created(MagicMock(is_directory=False, src_path=str(txt)))

    mock_process.assert_called_once_with(txt, outputs_dir, script)
