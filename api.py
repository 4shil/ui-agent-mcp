"""FastAPI REST wrapper for MCP tool handlers."""

from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from config import SCREENSHOTS_DIR
from server import call_tool

app = FastAPI(title="UI Agent MCP API", version="1.0.0")
UPLOADS_DIR = SCREENSHOTS_DIR / "api_uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


class RegionRequest(BaseModel):
    x: int
    y: int
    width: int
    height: int


class LocateRequest(BaseModel):
    image_path: str
    description: str


class ClickRequest(BaseModel):
    x: int
    y: int
    button: str = "left"


class TypeRequest(BaseModel):
    text: str


class ScrollRequest(BaseModel):
    x: int
    y: int
    direction: str = "down"
    amount: int = 3


class OpenAppRequest(BaseModel):
    app_name: str = Field(..., min_length=1)


def _tool_payload_to_json(payload: list) -> dict:
    if not payload:
        return {"status": "error", "error": "No response returned"}

    content = payload[0]
    try:
        return json.loads(content.text)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"Invalid tool response: {exc}") from exc


async def _run_tool(name: str, arguments: dict) -> dict:
    payload = await call_tool(name, arguments)
    return _tool_payload_to_json(payload)


def _store_upload(image: UploadFile) -> Path:
    extension = Path(image.filename or "upload.png").suffix or ".png"
    target = UPLOADS_DIR / f"{uuid.uuid4().hex}{extension}"
    with target.open("wb") as out_file:
        shutil.copyfileobj(image.file, out_file)
    return target


@app.post("/screenshot")
async def screenshot() -> dict:
    return await _run_tool("screenshot", {})


@app.post("/screenshot-region")
async def screenshot_region(request: RegionRequest) -> dict:
    return await _run_tool("screenshot_region", request.model_dump())


@app.post("/describe")
async def describe(image: UploadFile = File(...)) -> dict:
    image_path = _store_upload(image)
    return await _run_tool("describe_ui", {"image_path": str(image_path)})


@app.post("/locate")
async def locate(description: str = Form(...), image: UploadFile = File(...)) -> dict:
    image_path = _store_upload(image)
    return await _run_tool("locate_element", {"image_path": str(image_path), "description": description})


@app.post("/ocr")
async def ocr(image: UploadFile = File(...)) -> dict:
    image_path = _store_upload(image)
    return await _run_tool("read_text", {"image_path": str(image_path)})


@app.post("/click")
async def click(request: ClickRequest) -> dict:
    return await _run_tool("click", request.model_dump())


@app.post("/type")
async def type_text(request: TypeRequest) -> dict:
    return await _run_tool("type_text", request.model_dump())


@app.post("/scroll")
async def scroll(request: ScrollRequest) -> dict:
    return await _run_tool("scroll", request.model_dump())


@app.post("/open-app")
async def open_app(request: OpenAppRequest) -> dict:
    return await _run_tool("open_app", request.model_dump())


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "ui-agent-mcp-rest"}


@app.get("/stats")
async def stats() -> dict:
    return await _run_tool("get_safety_stats", {})
