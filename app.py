# Master Developer Prompt — FastAPI Server
# Dependencies: pip install fastapi uvicorn anthropic python-dotenv
#
# Usage:
#   export ANTHROPIC_API_KEY=sk-...
#   uvicorn app:app --reload
#
# Then POST to http://localhost:8000/process with JSON body:
#   { "transcript": "your meeting transcript here" }

import hmac
import json
import os
import re
from pathlib import Path
from typing import Annotated, Literal

import anthropic
import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from master_dev_runtime import (
    MAX_TOKENS,
    MODEL,
    PROMPT_PATH,
    ValidationError,
    build_user_message,
    load_system_prompt,
    parse_and_validate_output,
)

load_dotenv()

app = FastAPI(title="Master Dev Prompt API")
_GITHUB_API_BASE_URL = "https://api.github.com"


def verify_api_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
    server_key = os.getenv("SERVER_API_KEY")
    if not server_key:
        return  # no key configured → open (local dev)
    if not x_api_key or not hmac.compare_digest(x_api_key, server_key):
        raise HTTPException(status_code=401, detail="Unauthorized")

# Matches https://github.com/<owner>/<repo> with optional .git suffix or sub-paths.
# Owner: GitHub usernames start/end with alphanumeric and may contain hyphens.
# Repo: may additionally contain underscores and dots.
_GITHUB_REPO_RE = re.compile(
    r"^https://github\.com/"
    r"([A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)"   # owner
    r"/"
    r"([A-Za-z0-9_.-]+?)"                               # repo
    r"(?:\.git)?(?:/.*)?$"
)


def _ensure_private_repo(owner: str, repo: str) -> None:
    """Reject public GitHub repositories.

    When GitHub returns repo metadata, public repos are rejected and private
    repos are allowed. A GitHub token is required so private repo visibility
    can be verified reliably. Once authenticated, 404 and other non-200
    responses are treated as verification failures.
    """
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise HTTPException(
            status_code=503,
            detail="GITHUB_TOKEN is required to verify private GitHub repositories.",
        )
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "master-dev-prompt",
    }

    try:
        response = httpx.get(
            f"{_GITHUB_API_BASE_URL}/repos/{owner}/{repo}",
            headers=headers,
            timeout=5.0,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail="Unable to verify repository visibility with GitHub.",
        ) from exc

    if response.status_code == 200:
        if not response.json().get("private", False):
            raise HTTPException(
                status_code=422,
                detail="Only private GitHub repositories are supported.",
            )
        return

    if response.status_code in {401, 403}:
        raise HTTPException(
            status_code=502,
            detail="Unable to verify repository visibility with the current GitHub credentials.",
        )

    raise HTTPException(
        status_code=422,
        detail="Repository not found or unable to verify that this GitHub repository is private.",
    )

def _validate_repo_url(url: str) -> tuple[str, str, str]:
    """Validate a GitHub repository URL and return (owner, repo, normalized_url).

    Raises HTTPException 422 when the URL points to a repositories list
    rather than a specific repository, or is not a valid GitHub repo URL.
    """
    stripped = url.strip().rstrip("/")
    if "?tab=repositories" in stripped or stripped.endswith("/repositories"):
        raise HTTPException(
            status_code=422,
            detail=(
                "That link is your repositories list, not a specific repository. "
                "Please provide the URL of the one repo you want to work on "
                "(e.g. https://github.com/<owner>/<repo-name>)."
            ),
        )
    m = _GITHUB_REPO_RE.match(stripped)
    if not m:
        raise HTTPException(
            status_code=422,
            detail=(
                "Invalid GitHub repository URL. "
                "Expected format: https://github.com/<owner>/<repo-name>"
            ),
        )
    owner, repo = m.group(1), m.group(2)
    _ensure_private_repo(owner, repo)
    normalized = f"https://github.com/{owner}/{repo}"
    return owner, repo, normalized


def _prepare_claude_call(transcript: str) -> tuple[anthropic.Anthropic, str, str]:
    """Return (client, system_prompt, user_message) ready for a Claude API call."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not set")
    client = anthropic.Anthropic(api_key=api_key)
    system = load_system_prompt()
    user_message = build_user_message(transcript)
    return client, system, user_message


class DeliveryConfig(BaseModel):
    mode: Literal["pr", "push"]
    branch: str = "main"


class ProcessRequest(BaseModel):
    transcript: str
    repo_url: str | None = None
    delivery: DeliveryConfig | None = None


class ProcessResponse(BaseModel):
    result: dict
    repo: dict | None = None
    delivery: dict | None = None


@app.post("/process", response_model=ProcessResponse)
def process_transcript(
    req: ProcessRequest,
    _: Annotated[None, Depends(verify_api_key)],
) -> ProcessResponse:
    repo_info: dict | None = None
    if req.repo_url:
        owner, repo_name, normalized_url = _validate_repo_url(req.repo_url)
        repo_info = {"owner": owner, "repo": repo_name, "url": normalized_url}

    client, system, user_message = _prepare_claude_call(req.transcript)

    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system,
        messages=[{"role": "user", "content": user_message}],
    )

    raw = message.content[0].text
    try:
        result = parse_and_validate_output(raw)
    except ValidationError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Model returned invalid output: {exc}. Raw: {raw[:200]}",
        )

    return ProcessResponse(
        result=result,
        repo=repo_info,
        delivery=req.delivery.model_dump() if req.delivery else None,
    )


@app.post("/process/stream")
def process_transcript_stream(
    req: ProcessRequest,
    _: Annotated[None, Depends(verify_api_key)],
) -> StreamingResponse:
    repo_info: dict | None = None
    if req.repo_url:
        owner, repo_name, normalized_url = _validate_repo_url(req.repo_url)
        repo_info = {"owner": owner, "repo": repo_name, "url": normalized_url}

    delivery_info = req.delivery.model_dump() if req.delivery else None
    client, system, user_message = _prepare_claude_call(req.transcript)

    def generate():
        accumulated = ""
        with client.messages.stream(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            for chunk in stream.text_stream:
                accumulated += chunk
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"

        try:
            result = parse_and_validate_output(accumulated)
            yield f"data: {json.dumps({'done': True, 'result': result, 'repo': repo_info, 'delivery': delivery_info})}\n\n"
        except ValidationError as exc:
            yield f"data: {json.dumps({'error': str(exc), 'raw': accumulated[:300]})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/", response_class=HTMLResponse)
def ui() -> HTMLResponse:
    html = Path(__file__).parent / "static" / "index.html"
    return HTMLResponse(html.read_text() if html.exists() else "<h1>UI not found</h1>", status_code=200 if html.exists() else 404)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "prompt_loaded": PROMPT_PATH.exists()}
