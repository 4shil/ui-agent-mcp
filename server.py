# server.py — MCP Server for UI Agent

import asyncio
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types
from config import SERVER_NAME, SERVER_VERSION
from screen_capture import capture
from vision import vision
from ocr_engine import ocr
from ui_controller import controller
from element_finder import element_finder
from safety import safety

app = Server(SERVER_NAME, version=SERVER_VERSION)

TOOLS = [
    # Screen
    types.Tool(name="screenshot", description="Capture full screen",
               inputSchema={"type": "object", "properties": {}}),
    types.Tool(name="screenshot_region", description="Capture screen region",
               inputSchema={"type": "object", "properties": {
                   "x": {"type": "integer"}, "y": {"type": "integer"},
                   "width": {"type": "integer"}, "height": {"type": "integer"}},
                   "required": ["x", "y", "width", "height"]}),
    types.Tool(name="get_screen_info", description="Screen dimensions",
               inputSchema={"type": "object", "properties": {}}),
    # Vision
    types.Tool(name="describe_ui", description="Describe screen in natural language",
               inputSchema={"type": "object", "properties": {"image_path": {"type": "string"}}, "required": ["image_path"]}),
    types.Tool(name="describe_ui_detailed", description="Detailed screen description",
               inputSchema={"type": "object", "properties": {"image_path": {"type": "string"}}, "required": ["image_path"]}),
    types.Tool(name="locate_element", description="Find element by description → x,y",
               inputSchema={"type": "object", "properties": {
                   "image_path": {"type": "string"}, "description": {"type": "string"}},
                   "required": ["image_path", "description"]}),
    types.Tool(name="locate_all", description="Find all matching elements",
               inputSchema={"type": "object", "properties": {
                   "image_path": {"type": "string"}, "description": {"type": "string"}},
                   "required": ["image_path", "description"]}),
    types.Tool(name="detect_all", description="Detect all objects/icons",
               inputSchema={"type": "object", "properties": {"image_path": {"type": "string"}}, "required": ["image_path"]}),
    # OCR
    types.Tool(name="read_text", description="Extract all text via GLM-OCR",
               inputSchema={"type": "object", "properties": {"image_path": {"type": "string"}}, "required": ["image_path"]}),
    types.Tool(name="read_text_region", description="OCR specific region",
               inputSchema={"type": "object", "properties": {
                   "image_path": {"type": "string"}, "x": {"type": "integer"}, "y": {"type": "integer"},
                   "width": {"type": "integer"}, "height": {"type": "integer"}},
                   "required": ["image_path", "x", "y", "width", "height"]}),
    types.Tool(name="read_table", description="Extract tables as markdown",
               inputSchema={"type": "object", "properties": {"image_path": {"type": "string"}}, "required": ["image_path"]}),
    types.Tool(name="read_formula", description="Extract formulas as LaTeX",
               inputSchema={"type": "object", "properties": {"image_path": {"type": "string"}}, "required": ["image_path"]}),
    types.Tool(name="read_form", description="Extract form fields",
               inputSchema={"type": "object", "properties": {"image_path": {"type": "string"}}, "required": ["image_path"]}),
    # Mouse
    types.Tool(name="click", description="Click at coordinates",
               inputSchema={"type": "object", "properties": {
                   "x": {"type": "integer"}, "y": {"type": "integer"},
                   "button": {"type": "string", "default": "left"}}, "required": ["x", "y"]}),
    types.Tool(name="double_click", description="Double-click at coordinates",
               inputSchema={"type": "object", "properties": {
                   "x": {"type": "integer"}, "y": {"type": "integer"}}, "required": ["x", "y"]}),
    types.Tool(name="right_click", description="Right-click at coordinates",
               inputSchema={"type": "object", "properties": {
                   "x": {"type": "integer"}, "y": {"type": "integer"}}, "required": ["x", "y"]}),
    types.Tool(name="hover", description="Move mouse without clicking",
               inputSchema={"type": "object", "properties": {
                   "x": {"type": "integer"}, "y": {"type": "integer"}}, "required": ["x", "y"]}),
    types.Tool(name="scroll", description="Scroll at coordinates",
               inputSchema={"type": "object", "properties": {
                   "x": {"type": "integer"}, "y": {"type": "integer"},
                   "direction": {"type": "string", "default": "down"},
                   "amount": {"type": "integer", "default": 3}}, "required": ["x", "y"]}),
    types.Tool(name="drag", description="Drag between points",
               inputSchema={"type": "object", "properties": {
                   "x1": {"type": "integer"}, "y1": {"type": "integer"},
                   "x2": {"type": "integer"}, "y2": {"type": "integer"},
                   "duration": {"type": "number", "default": 0.5}}, "required": ["x1", "y1", "x2", "y2"]}),
    types.Tool(name="get_mouse_position", description="Current mouse coords",
               inputSchema={"type": "object", "properties": {}}),
    # Keyboard
    types.Tool(name="type_text", description="Type into focused element",
               inputSchema={"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}),
    types.Tool(name="press_key", description="Press single key",
               inputSchema={"type": "object", "properties": {"key": {"type": "string"}}, "required": ["key"]}),
    types.Tool(name="hotkey", description="Press key combo",
               inputSchema={"type": "object", "properties": {"keys": {"type": "array", "items": {"type": "string"}}}, "required": ["keys"]}),
    types.Tool(name="type_and_enter", description="Type then press Enter",
               inputSchema={"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}),
    # Composite
    types.Tool(name="find_and_click", description="Find element and click it",
               inputSchema={"type": "object", "properties": {
                   "description": {"type": "string"},
                   "button": {"type": "string", "default": "left"}}, "required": ["description"]}),
    types.Tool(name="type_into", description="Find field and type into it",
               inputSchema={"type": "object", "properties": {
                   "description": {"type": "string"}, "text": {"type": "string"},
                   "press_enter": {"type": "boolean", "default": False}}, "required": ["description", "text"]}),
    types.Tool(name="wait_for_element", description="Wait for element to appear",
               inputSchema={"type": "object", "properties": {
                   "description": {"type": "string"}, "timeout": {"type": "integer", "default": 10}}, "required": ["description"]}),
    # Apps
    types.Tool(name="open_app", description="Launch application",
               inputSchema={"type": "object", "properties": {"app_name": {"type": "string"}}, "required": ["app_name"]}),
    types.Tool(name="close_app", description="Close application",
               inputSchema={"type": "object", "properties": {"app_name": {"type": "string"}}, "required": ["app_name"]}),
    types.Tool(name="get_focused_window", description="Get focused app info",
               inputSchema={"type": "object", "properties": {}}),
    # Safety
    types.Tool(name="get_safety_stats", description="Action stats and safety status",
               inputSchema={"type": "object", "properties": {}}),
]


@app.list_tools()
async def list_tools():
    return TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: dict):
    handlers = {
        "screenshot": lambda: capture.screenshot(),
        "screenshot_region": lambda: capture.screenshot_region(arguments["x"], arguments["y"], arguments["width"], arguments["height"]),
        "get_screen_info": lambda: capture.get_screen_info(),
        "describe_ui": lambda: vision.describe_ui(arguments["image_path"]),
        "describe_ui_detailed": lambda: vision.describe_detailed(arguments["image_path"]),
        "locate_element": lambda: vision.locate_element(arguments["image_path"], arguments["description"]),
        "locate_all": lambda: vision.locate_all(arguments["image_path"], arguments["description"]),
        "detect_all": lambda: vision.detect_all(arguments["image_path"]),
        "read_text": lambda: ocr.read_text(arguments["image_path"]),
        "read_text_region": lambda: ocr.read_text_region(arguments["image_path"], arguments["x"], arguments["y"], arguments["width"], arguments["height"]),
        "read_table": lambda: ocr.read_table(arguments["image_path"]),
        "read_formula": lambda: ocr.read_formula(arguments["image_path"]),
        "read_form": lambda: ocr.read_form(arguments["image_path"]),
        "click": lambda: controller.click(arguments["x"], arguments["y"], button=arguments.get("button", "left")),
        "double_click": lambda: controller.double_click(arguments["x"], arguments["y"]),
        "right_click": lambda: controller.right_click(arguments["x"], arguments["y"]),
        "hover": lambda: controller.hover(arguments["x"], arguments["y"]),
        "scroll": lambda: controller.scroll(arguments["x"], arguments["y"], direction=arguments.get("direction", "down"), amount=arguments.get("amount", 3)),
        "drag": lambda: controller.drag(arguments["x1"], arguments["y1"], arguments["x2"], arguments["y2"], duration=arguments.get("duration", 0.5)),
        "get_mouse_position": lambda: controller.get_mouse_position(),
        "type_text": lambda: controller.type_text(arguments["text"]),
        "press_key": lambda: controller.press_key(arguments["key"]),
        "hotkey": lambda: controller.hotkey(*arguments["keys"]),
        "type_and_enter": lambda: controller.type_and_enter(arguments["text"]),
        "find_and_click": lambda: element_finder.find_and_click(arguments["description"], button=arguments.get("button", "left")),
        "type_into": lambda: element_finder.type_into(arguments["description"], arguments["text"], press_enter=arguments.get("press_enter", False)),
        "wait_for_element": lambda: element_finder.wait_for(arguments["description"], timeout=arguments.get("timeout", 10)),
        "open_app": lambda: controller.open_app(arguments["app_name"]),
        "close_app": lambda: controller.close_app(arguments["app_name"]),
        "get_focused_window": lambda: controller.get_focused_window(),
        "get_safety_stats": lambda: safety.get_stats(),
    }

    try:
        result = handlers[name]() if name in handlers else {"status": "error", "error": f"Unknown: {name}"}
        safety.record_action(name, result.get("status", "ok"), arguments)
    except Exception as e:
        result = {"status": "error", "error": str(e)}
        safety.record_action(name, "error", {"error": str(e)})

    return [types.TextContent(type="text", text=json.dumps(result, indent=2))]


async def main():
    print(f"[MCP] {SERVER_NAME} v{SERVER_VERSION} | Florence-2 + GLM-OCR")
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
