from pathlib import Path


def test_master_prompt_requires_final_json_self_check():
    prompt_path = Path(__file__).resolve().parents[1] / "master_dev_prompt.txt"
    prompt = prompt_path.read_text(encoding="utf-8")

    assert "Before responding, do a final self-check" in prompt
    assert "valid JSON matching the exact schema and enum values" in prompt
