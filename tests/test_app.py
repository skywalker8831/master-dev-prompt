from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

import app as app_module


def test_prepare_claude_call_appends_blank_line_before_closing_quotes(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(app_module, "_get_system_prompt", lambda: "system prompt")

    fake_client = object()
    anthropic_ctor = MagicMock(return_value=fake_client)
    monkeypatch.setattr(app_module.anthropic, "Anthropic", anthropic_ctor)

    client, system, user_message = app_module._prepare_claude_call("hello")

    assert client is fake_client
    assert system == "system prompt"
    assert user_message == 'hello\n\n"""'


def test_process_endpoint_uses_expected_prompt_format(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.delenv("SERVER_API_KEY", raising=False)
    monkeypatch.setattr(app_module, "_get_system_prompt", lambda: "system prompt")

    create = MagicMock(return_value=SimpleNamespace(content=[SimpleNamespace(text='{"ok": true}')]))
    fake_client = SimpleNamespace(messages=SimpleNamespace(create=create))
    monkeypatch.setattr(app_module.anthropic, "Anthropic", MagicMock(return_value=fake_client))

    client = TestClient(app_module.app)
    response = client.post("/process", json={"transcript": "hello"})

    assert response.status_code == 200
    assert response.json() == {"result": {"ok": True}}
    assert create.call_args.kwargs["messages"] == [{"role": "user", "content": 'hello\n\n"""'}]
