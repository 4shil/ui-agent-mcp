"""Optional REST API wrapper for MCP tools."""

from __future__ import annotations

import json

from fastapi import Body, FastAPI, HTTPException

from server import TOOLS, call_tool

app = FastAPI(title="UI Agent MCP REST API", version="1.0.0")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "tool_count": len(TOOLS)}


@app.get("/tools")
async def list_tools() -> list[dict]:
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema,
        }
        for tool in TOOLS
    ]


@app.post("/tools/{tool_name}")
async def run_tool(tool_name: str, arguments: dict = Body(default_factory=dict)) -> dict:
    if tool_name not in {tool.name for tool in TOOLS}:
        raise HTTPException(status_code=404, detail=f"Unknown tool: {tool_name}")

    payload = await call_tool(tool_name, arguments)
    if not payload:
        return {"status": "error", "error": "No response returned"}

    content = payload[0]
    try:
        return json.loads(content.text)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"Invalid tool response: {exc}") from exc
