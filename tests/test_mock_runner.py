"""Tests for mock_runner.sh – deterministic dry-run behaviour."""

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
MOCK_RUNNER = REPO_ROOT / "mock_runner.sh"
DEFAULT_FIXTURE = REPO_ROOT / "outputs" / "sample.json"
CI_FIXTURE = REPO_ROOT / "ci" / "fixtures" / "valid_output.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_mock(args: list[str], env: dict | None = None) -> subprocess.CompletedProcess:
    """Run mock_runner.sh and return the CompletedProcess result."""
    base_env = {**os.environ}
    if env:
        base_env.update(env)
    return subprocess.run(
        ["bash", str(MOCK_RUNNER)] + args,
        capture_output=True,
        text=True,
        env=base_env,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestMockRunnerSuccess:
    def test_outputs_valid_json_with_default_fixture(self, tmp_path):
        """Mock runner should produce valid JSON using the default fixture."""
        transcript = tmp_path / "meeting.txt"
        transcript.write_text("Standup: shipped feature X.\n")

        result = run_mock([str(transcript)])

        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert isinstance(data, dict)

    def test_output_matches_fixture_exactly(self, tmp_path):
        """Output must be byte-for-byte identical to the fixture (deterministic)."""
        transcript = tmp_path / "t.txt"
        transcript.write_text("Some transcript text.")

        result = run_mock([str(transcript)])

        assert result.returncode == 0
        fixture_text = DEFAULT_FIXTURE.read_text()
        assert result.stdout == fixture_text

    def test_deterministic_across_multiple_runs(self, tmp_path):
        """Repeated invocations must produce the same output."""
        transcript = tmp_path / "t.txt"
        transcript.write_text("Transcript content.")

        outputs = [run_mock([str(transcript)]).stdout for _ in range(3)]
        assert outputs[0] == outputs[1] == outputs[2]

    def test_custom_fixture_via_flag(self, tmp_path):
        """--fixture flag should override the default fixture."""
        transcript = tmp_path / "t.txt"
        transcript.write_text("Transcript.")

        result = run_mock([str(transcript), "--fixture", str(CI_FIXTURE)])

        assert result.returncode == 0
        expected = CI_FIXTURE.read_text()
        assert result.stdout == expected

    def test_custom_fixture_via_env_var(self, tmp_path):
        """MOCK_FIXTURE env var should override the default fixture."""
        transcript = tmp_path / "t.txt"
        transcript.write_text("Transcript.")

        result = run_mock([str(transcript)], env={"MOCK_FIXTURE": str(CI_FIXTURE)})

        assert result.returncode == 0
        expected = CI_FIXTURE.read_text()
        assert result.stdout == expected

    def test_flag_takes_precedence_over_env(self, tmp_path):
        """--fixture flag should win over MOCK_FIXTURE env var."""
        transcript = tmp_path / "t.txt"
        transcript.write_text("Transcript.")

        # env points at CI_FIXTURE, flag points at DEFAULT_FIXTURE
        result = run_mock(
            [str(transcript), "--fixture", str(DEFAULT_FIXTURE)],
            env={"MOCK_FIXTURE": str(CI_FIXTURE)},
        )

        assert result.returncode == 0
        assert result.stdout == DEFAULT_FIXTURE.read_text()

    def test_output_passes_schema_validation(self, tmp_path):
        """JSON produced by mock_runner.sh must pass validate_output.py."""
        transcript = tmp_path / "t.txt"
        transcript.write_text("Transcript.")
        output_file = tmp_path / "out.json"

        mock_result = run_mock([str(transcript)])
        assert mock_result.returncode == 0
        output_file.write_text(mock_result.stdout)

        validate_result = subprocess.run(
            ["python3", str(REPO_ROOT / "validate_output.py"), str(output_file)],
            capture_output=True,
            text=True,
        )
        assert validate_result.returncode == 0, (
            f"Validation failed:\n{validate_result.stderr}"
        )


class TestMockRunnerErrors:
    def test_missing_transcript_arg_exits_nonzero(self):
        """Invoking without a transcript argument should fail."""
        result = run_mock([])
        assert result.returncode != 0

    def test_nonexistent_transcript_exits_1(self, tmp_path):
        """Pointing at a non-existent transcript should exit with code 1."""
        result = run_mock([str(tmp_path / "does_not_exist.txt")])
        assert result.returncode == 1
        assert "not found" in result.stderr

    def test_nonexistent_fixture_exits_2(self, tmp_path):
        """Pointing at a non-existent fixture should exit with code 2."""
        transcript = tmp_path / "t.txt"
        transcript.write_text("Transcript.")

        result = run_mock(
            [str(transcript), "--fixture", str(tmp_path / "no_fixture.json")]
        )
        assert result.returncode == 2
        assert "not found" in result.stderr
