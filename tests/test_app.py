import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient


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
