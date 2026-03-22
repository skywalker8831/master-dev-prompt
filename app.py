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
from pathlib import Path
from typing import Annotated

import anthropic
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


def verify_api_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
    server_key = os.getenv("SERVER_API_KEY")
    if not server_key:
        return  # no key configured → open (local dev)
    if not x_api_key or not hmac.compare_digest(x_api_key, server_key):
        raise HTTPException(status_code=401, detail="Unauthorized")


def _prepare_claude_call(transcript: str) -> tuple[anthropic.Anthropic, str, str]:
    """Return (client, system_prompt, user_message) ready for a Claude API call."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not set")
    client = anthropic.Anthropic(api_key=api_key)
    system = load_system_prompt()
    user_message = build_user_message(transcript)
    return client, system, user_message


class ProcessRequest(BaseModel):
    transcript: str


class ProcessResponse(BaseModel):
    result: dict


@app.post("/process", response_model=ProcessResponse)
def process_transcript(
    req: ProcessRequest,
    _: Annotated[None, Depends(verify_api_key)],
) -> ProcessResponse:
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

    return ProcessResponse(result=result)


@app.post("/process/stream")
def process_transcript_stream(
    req: ProcessRequest,
    _: Annotated[None, Depends(verify_api_key)],
) -> StreamingResponse:
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
            yield f"data: {json.dumps({'done': True, 'result': result})}\n\n"
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
