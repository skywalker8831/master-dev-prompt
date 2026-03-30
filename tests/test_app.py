import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import app as app_module


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "ci" / "fixtures" / "valid_output.json"
VALID_RESULT = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


# ── Fake runtime helpers for integration tests ───────────────────────────────

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


# ── _prepare_claude_call tests ────────────────────────────────────────────────

def test_prepare_claude_call_raises_without_api_key(monkeypatch):
    from app import _prepare_claude_call
    
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    
    with pytest.raises(HTTPException) as exc_info:
        _prepare_claude_call("test transcript")
    
    assert exc_info.value.status_code == 500
    assert "ANTHROPIC_API_KEY not set" in exc_info.value.detail


def test_prepare_claude_call_returns_tuple_with_api_key(monkeypatch):
    from app import _prepare_claude_call
    from unittest.mock import MagicMock, patch
    
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    
    with patch("app.anthropic.Anthropic") as mock_anthropic:
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        
        client, system, user_message = _prepare_claude_call("hello world")
        
        assert client == mock_client
        mock_anthropic.assert_called_once_with(api_key="test-key")
        assert isinstance(system, str)
        assert "hello world" in user_message
        assert user_message.endswith('"""')


# ── URL validation unit tests ─────────────────────────────────────────────────

def test_validate_repo_url_valid():
    from app import _validate_repo_url

    owner, repo, url = _validate_repo_url("https://github.com/skywalker8831/master-dev-prompt")
    assert owner == "skywalker8831"
    assert repo == "master-dev-prompt"
    assert url == "https://github.com/skywalker8831/master-dev-prompt"


def test_validate_repo_url_valid_with_git_suffix():
    from app import _validate_repo_url

    owner, repo, url = _validate_repo_url("https://github.com/octocat/Hello-World.git")
    assert owner == "octocat"
    assert repo == "Hello-World"
    assert url == "https://github.com/octocat/Hello-World"


def test_validate_repo_url_valid_with_trailing_slash():
    from app import _validate_repo_url

    owner, repo, url = _validate_repo_url("https://github.com/octocat/Hello-World/")
    assert owner == "octocat"
    assert repo == "Hello-World"
    assert url == "https://github.com/octocat/Hello-World"


def test_validate_repo_url_rejects_tab_repositories():
    from app import _validate_repo_url

    with pytest.raises(HTTPException) as exc_info:
        _validate_repo_url("https://github.com/skywalker8888?tab=repositories")
    assert exc_info.value.status_code == 422
    assert "repositories list" in exc_info.value.detail


def test_validate_repo_url_rejects_repositories_path():
    from app import _validate_repo_url

    with pytest.raises(HTTPException) as exc_info:
        _validate_repo_url("https://github.com/skywalker8888/repositories")
    assert exc_info.value.status_code == 422
    assert "repositories list" in exc_info.value.detail


def test_validate_repo_url_rejects_non_github():
    from app import _validate_repo_url

    with pytest.raises(HTTPException) as exc_info:
        _validate_repo_url("https://gitlab.com/user/repo")
    assert exc_info.value.status_code == 422
    assert "Invalid GitHub repository URL" in exc_info.value.detail


def test_validate_repo_url_rejects_bare_profile():
    from app import _validate_repo_url

    with pytest.raises(HTTPException) as exc_info:
        _validate_repo_url("https://github.com/skywalker8888")
    assert exc_info.value.status_code == 422
    assert "Invalid GitHub repository URL" in exc_info.value.detail


# ── Delivery config model tests ───────────────────────────────────────────────

def test_process_request_accepts_repo_url_and_delivery():
    from app import DeliveryConfig, ProcessRequest

    req = ProcessRequest(
        transcript="some transcript",
        repo_url="https://github.com/octocat/Hello-World",
        delivery=DeliveryConfig(mode="pr", branch="main"),
    )
    assert req.repo_url == "https://github.com/octocat/Hello-World"
    assert req.delivery is not None
    assert req.delivery.mode == "pr"
    assert req.delivery.branch == "main"


def test_process_request_delivery_push_mode():
    from app import DeliveryConfig, ProcessRequest

    req = ProcessRequest(
        transcript="some transcript",
        delivery=DeliveryConfig(mode="push", branch="develop"),
    )
    assert req.delivery is not None
    assert req.delivery.mode == "push"
    assert req.delivery.branch == "develop"


def test_process_request_optional_fields_default_none():
    from app import ProcessRequest

    req = ProcessRequest(transcript="some transcript")
    assert req.repo_url is None
    assert req.delivery is None


def test_delivery_config_default_branch():
    from app import DeliveryConfig

    cfg = DeliveryConfig(mode="push")
    assert cfg.branch == "main"


# ── Integration tests (TestClient + monkeypatched runtime) ────────────────────

def test_process_endpoint_returns_schema_validated_result(monkeypatch):
    _install_fake_runtime(monkeypatch, _FakeClient(raw_text=json.dumps(VALID_RESULT)))
    client = TestClient(app_module.app)

    response = client.post("/process", json={"transcript": "hello"})

    assert response.status_code == 200
    assert response.json()["result"]["code_suggestions"]["language"] == "python"


def test_process_endpoint_returns_repo_and_delivery_when_provided(monkeypatch):
    _install_fake_runtime(monkeypatch, _FakeClient(raw_text=json.dumps(VALID_RESULT)))
    client = TestClient(app_module.app)

    response = client.post(
        "/process",
        json={
            "transcript": "hello",
            "repo_url": "https://github.com/octocat/Hello-World",
            "delivery": {"mode": "pr", "branch": "main"},
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["repo"] == {"owner": "octocat", "repo": "Hello-World", "url": "https://github.com/octocat/Hello-World"}
    assert data["delivery"] == {"mode": "pr", "branch": "main"}


def test_process_endpoint_rejects_list_url(monkeypatch):
    _install_fake_runtime(monkeypatch, _FakeClient(raw_text=json.dumps(VALID_RESULT)))
    client = TestClient(app_module.app)

    response = client.post(
        "/process",
        json={"transcript": "hello", "repo_url": "https://github.com/skywalker8888?tab=repositories"},
    )

    assert response.status_code == 422
    assert "repositories list" in response.json()["detail"]


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


def test_stream_endpoint_emits_repo_and_delivery_in_done_event(monkeypatch):
    chunks = [json.dumps(VALID_RESULT)[:80], json.dumps(VALID_RESULT)[80:]]
    _install_fake_runtime(monkeypatch, _FakeClient(chunks=chunks))
    client = TestClient(app_module.app)

    with client.stream(
        "POST",
        "/process/stream",
        json={
            "transcript": "hello",
            "repo_url": "https://github.com/octocat/Hello-World",
            "delivery": {"mode": "push", "branch": "develop"},
        },
    ) as response:
        body = "".join(response.iter_text())

    assert response.status_code == 200
    assert '"done": true' in body
    assert '"owner": "octocat"' in body
    assert '"mode": "push"' in body


def test_stream_endpoint_emits_error_for_schema_invalid_output(monkeypatch):
    invalid_json = json.dumps({"design_doc": {}})
    _install_fake_runtime(monkeypatch, _FakeClient(chunks=[invalid_json]))
    client = TestClient(app_module.app)

    with client.stream("POST", "/process/stream", json={"transcript": "hello"}) as response:
        body = "".join(response.iter_text())

    assert response.status_code == 200
    assert '"error":' in body
    assert "$ keys mismatch" in body or "$.design_doc keys mismatch" in body


# ── Health and UI endpoint tests ──────────────────────────────────────────────

def test_health_endpoint_returns_ok():
    client = TestClient(app_module.app)
    
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "prompt_loaded" in data


def test_ui_endpoint_returns_html():
    client = TestClient(app_module.app)
    
    response = client.get("/")
    
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


# ── API key verification tests ────────────────────────────────────────────────

def test_verify_api_key_allows_access_when_no_key_configured(monkeypatch):
    monkeypatch.delenv("SERVER_API_KEY", raising=False)
    client = TestClient(app_module.app)
    _install_fake_runtime(monkeypatch, _FakeClient(raw_text=json.dumps(VALID_RESULT)))
    
    response = client.post("/process", json={"transcript": "hello"})
    
    assert response.status_code == 200


def test_verify_api_key_rejects_wrong_key(monkeypatch):
    monkeypatch.setenv("SERVER_API_KEY", "correct_key")
    _install_fake_runtime(monkeypatch, _FakeClient(raw_text=json.dumps(VALID_RESULT)))
    client = TestClient(app_module.app)
    
    response = client.post("/process", json={"transcript": "hello"}, headers={"X-Api-Key": "wrong_key"})
    
    assert response.status_code == 401
    assert "Unauthorized" in response.json()["detail"]


def test_stream_endpoint_requires_api_key_when_configured(monkeypatch):
    monkeypatch.setenv("SERVER_API_KEY", "secret")
    chunks = [json.dumps(VALID_RESULT)]
    _install_fake_runtime(monkeypatch, _FakeClient(chunks=chunks))
    client = TestClient(app_module.app)
    
    # Without API key
    with client.stream("POST", "/process/stream", json={"transcript": "hello"}) as response:
        pass  # Just check status
    assert response.status_code == 401
    
    # With correct API key
    with client.stream("POST", "/process/stream", json={"transcript": "hello"}, headers={"X-Api-Key": "secret"}) as response:
        pass
    assert response.status_code == 200


# ── URL validation edge cases ─────────────────────────────────────────────────

def test_validate_repo_url_handles_whitespace():
    from app import _validate_repo_url
    
    owner, repo, url = _validate_repo_url("  https://github.com/owner/repo  ")
    assert owner == "owner"
    assert repo == "repo"
    assert url == "https://github.com/owner/repo"


def test_validate_repo_url_handles_subpaths():
    from app import _validate_repo_url
    
    owner, repo, url = _validate_repo_url("https://github.com/owner/repo/tree/main/src")
    assert owner == "owner"
    assert repo == "repo"
    assert url == "https://github.com/owner/repo"


def test_validate_repo_url_accepts_repo_with_dots():
    from app import _validate_repo_url
    
    owner, repo, url = _validate_repo_url("https://github.com/owner/repo.name.js")
    assert repo == "repo.name.js"


def test_validate_repo_url_accepts_repo_with_underscore():
    from app import _validate_repo_url
    
    owner, repo, url = _validate_repo_url("https://github.com/owner/repo_name")
    assert repo == "repo_name"


def test_validate_repo_url_rejects_empty_string():
    from app import _validate_repo_url
    
    with pytest.raises(HTTPException) as exc_info:
        _validate_repo_url("")
    assert exc_info.value.status_code == 422


def test_validate_repo_url_rejects_owner_ending_with_hyphen():
    from app import _validate_repo_url
    
    with pytest.raises(HTTPException) as exc_info:
        _validate_repo_url("https://github.com/owner-/repo")
    assert exc_info.value.status_code == 422


# ── Process request validation tests ──────────────────────────────────────────

def test_process_request_rejects_invalid_delivery_mode():
    from pydantic import ValidationError as PydanticValidationError
    from app import ProcessRequest, DeliveryConfig
    
    with pytest.raises(PydanticValidationError):
        ProcessRequest(
            transcript="test",
            delivery=DeliveryConfig(mode="invalid")  # type: ignore
        )


def test_process_endpoint_handles_no_repo_url(monkeypatch):
    _install_fake_runtime(monkeypatch, _FakeClient(raw_text=json.dumps(VALID_RESULT)))
    client = TestClient(app_module.app)
    
    response = client.post("/process", json={"transcript": "hello"})
    
    assert response.status_code == 200
    data = response.json()
    assert data["repo"] is None
    assert data["delivery"] is None


def test_stream_endpoint_handles_no_repo_or_delivery(monkeypatch):
    chunks = [json.dumps(VALID_RESULT)]
    _install_fake_runtime(monkeypatch, _FakeClient(chunks=chunks))
    client = TestClient(app_module.app)
    
    with client.stream("POST", "/process/stream", json={"transcript": "hello"}) as response:
        body = "".join(response.iter_text())
    
    assert response.status_code == 200
    assert '"done": true' in body
    # repo and delivery should be null in the done event
    assert '"repo": null' in body
    assert '"delivery": null' in body


# ── Multiple chunk streaming tests ────────────────────────────────────────────

def test_stream_endpoint_emits_chunks_incrementally(monkeypatch):
    # Split the valid JSON into multiple chunks to test streaming
    full_json = json.dumps(VALID_RESULT)
    chunks = [full_json[:50], full_json[50:100], full_json[100:]]
    _install_fake_runtime(monkeypatch, _FakeClient(chunks=chunks))
    client = TestClient(app_module.app)
    
    with client.stream("POST", "/process/stream", json={"transcript": "hello"}) as response:
        events = list(response.iter_text())
    
    # Should have multiple chunk events plus the done event
    chunk_events = [e for e in events if '"chunk":' in e]
    assert len(chunk_events) >= 1


def test_stream_endpoint_stream_rejects_list_url(monkeypatch):
    chunks = [json.dumps(VALID_RESULT)]
    _install_fake_runtime(monkeypatch, _FakeClient(chunks=chunks))
    client = TestClient(app_module.app)
    
    with client.stream(
        "POST",
        "/process/stream",
        json={"transcript": "hello", "repo_url": "https://github.com/user?tab=repositories"},
    ) as response:
        pass
    
    assert response.status_code == 422
