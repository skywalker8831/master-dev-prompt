import json
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

import app as app_module


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "ci" / "fixtures" / "valid_output.json"
VALID_RESULT = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


class _FakeStream:
    def __init__(self, chunks):
        self.text_stream = iter(chunks)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeMessages:
    def __init__(self, raw_text=None, chunks=None):
        self._raw_text = raw_text
        self._chunks = chunks or []

    def create(self, **kwargs):
        return SimpleNamespace(content=[SimpleNamespace(text=self._raw_text)])

    def stream(self, **kwargs):
        return _FakeStream(self._chunks)


class _FakeClient:
    def __init__(self, raw_text=None, chunks=None):
        self.messages = _FakeMessages(raw_text=raw_text, chunks=chunks)


def _install_fake_runtime(monkeypatch, fake_client):
    monkeypatch.setattr(
        app_module,
        "_prepare_claude_call",
        lambda transcript: (fake_client, "system prompt", f'{transcript}\n"""'),
    )


def test_process_endpoint_returns_schema_validated_result(monkeypatch):
    _install_fake_runtime(monkeypatch, _FakeClient(raw_text=json.dumps(VALID_RESULT)))
    client = TestClient(app_module.app)

    response = client.post("/process", json={"transcript": "hello"})

    assert response.status_code == 200
    assert response.json()["result"]["code_suggestions"]["language"] == "python"


def test_process_endpoint_rejects_schema_invalid_output(monkeypatch):
    invalid_result = {
        "design_doc": VALID_RESULT["design_doc"],
        "pm_summary": VALID_RESULT["pm_summary"],
        "actions": VALID_RESULT["actions"],
        "implementation_plan": VALID_RESULT["implementation_plan"],
    }
    _install_fake_runtime(monkeypatch, _FakeClient(raw_text=json.dumps(invalid_result)))
    client = TestClient(app_module.app)

    response = client.post("/process", json={"transcript": "hello"})

    assert response.status_code == 502
    assert "invalid output" in response.json()["detail"]
    assert "$ keys mismatch" in response.json()["detail"]


def test_process_endpoint_requires_api_key_when_configured(monkeypatch):
    monkeypatch.setenv("SERVER_API_KEY", "secret")
    _install_fake_runtime(monkeypatch, _FakeClient(raw_text=json.dumps(VALID_RESULT)))
    client = TestClient(app_module.app)

    unauthorized = client.post("/process", json={"transcript": "hello"})
    authorized = client.post("/process", json={"transcript": "hello"}, headers={"X-Api-Key": "secret"})

    assert unauthorized.status_code == 401
    assert authorized.status_code == 200


def test_stream_endpoint_emits_done_for_schema_valid_output(monkeypatch):
    chunks = [json.dumps(VALID_RESULT)[:80], json.dumps(VALID_RESULT)[80:]]
    _install_fake_runtime(monkeypatch, _FakeClient(chunks=chunks))
    client = TestClient(app_module.app)

    with client.stream("POST", "/process/stream", json={"transcript": "hello"}) as response:
        body = "".join(response.iter_text())

    assert response.status_code == 200
    assert '"done": true' in body
    assert '"language": "python"' in body


def test_stream_endpoint_emits_error_for_schema_invalid_output(monkeypatch):
    invalid_json = json.dumps({"design_doc": {}})
    _install_fake_runtime(monkeypatch, _FakeClient(chunks=[invalid_json]))
    client = TestClient(app_module.app)

    with client.stream("POST", "/process/stream", json={"transcript": "hello"}) as response:
        body = "".join(response.iter_text())

    assert response.status_code == 200
    assert '"error":' in body
    assert "$ keys mismatch" in body or "$.design_doc keys mismatch" in body
