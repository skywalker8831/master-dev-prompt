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
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="Master Dev Prompt API")

_MODEL = "claude-sonnet-4-6"
_MAX_TOKENS = 8096


def verify_api_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
    server_key = os.getenv("SERVER_API_KEY")
    if not server_key:
        return  # no key configured → open (local dev)
    if not x_api_key or not hmac.compare_digest(x_api_key, server_key):
        raise HTTPException(status_code=401, detail="Unauthorized")

_PROMPT_PATH = Path(__file__).parent / "master_dev_prompt.txt"
_system_prompt: str | None = None

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


def _get_system_prompt() -> str:
    global _system_prompt
    if _system_prompt is None:
        if not _PROMPT_PATH.exists():
            raise RuntimeError("master_dev_prompt.txt not found")
        _system_prompt = _PROMPT_PATH.read_text()
    return _system_prompt


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
    normalized = f"https://github.com/{owner}/{repo}"
    return owner, repo, normalized


def _prepare_claude_call(transcript: str) -> tuple[anthropic.Anthropic, str, str]:
    """Return (client, system_prompt, user_message) ready for a Claude API call."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not set")
    client = anthropic.Anthropic(api_key=api_key)
    system = _get_system_prompt()
    user_message = f'{transcript}\n"""'
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
        model=_MODEL,
        max_tokens=_MAX_TOKENS,
        system=system,
        messages=[{"role": "user", "content": user_message}],
    )

    raw = message.content[0].text
    try:
        result = json.loads(raw)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Model returned invalid JSON: {e}. Raw: {raw[:200]}",
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
            model=_MODEL,
            max_tokens=_MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            for chunk in stream.text_stream:
                accumulated += chunk
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"

        try:
            result = json.loads(accumulated)
            yield f"data: {json.dumps({'done': True, 'result': result, 'repo': repo_info, 'delivery': delivery_info})}\n\n"
        except json.JSONDecodeError as e:
            yield f"data: {json.dumps({'error': str(e), 'raw': accumulated[:300]})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/", response_class=HTMLResponse)
def ui() -> HTMLResponse:
    html = Path(__file__).parent / "static" / "index.html"
    return HTMLResponse(html.read_text() if html.exists() else "<h1>UI not found</h1>", status_code=200 if html.exists() else 404)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "prompt_loaded": _PROMPT_PATH.exists()}
