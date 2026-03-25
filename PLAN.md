# UI Agent MCP — 26-Step Development Plan

## Overview
Build an MCP server that gives AI agents complete UI access using:
- **Florence-2** (Microsoft) — UI understanding, element detection
- **GLM-OCR** (Z.AI / zai-org) — text, table, formula extraction
- **pyautogui** — mouse/keyboard actions
- **mss** — screen capture

---

## Phase 1: Foundation (Days 1-5)
| Step | Task | Files |
|------|------|-------|
| 1 | Project init, git setup, README | `README.md`, `.gitignore` |
| 2 | Config module | `config.py` |
| 3 | Screen capture module | `screen_capture.py` |
| 4 | Basic click actions | `ui_controller.py` (part 1) |
| 5 | Type, keyboard, hotkey actions | `ui_controller.py` (part 2) |

## Phase 2: Advanced Actions (Days 6-8)
| Step | Task | Files |
|------|------|-------|
| 6 | Scroll, drag, hover actions | `ui_controller.py` (part 3) |
| 7 | App launch/close + window info | `ui_controller.py` (part 4) |
| 8 | Safety layer — cooldowns, rate limits, audit | `safety.py` |

## Phase 3: Vision (Days 9-12)
| Step | Task | Files |
|------|------|-------|
| 9 | Florence-2 setup + model loader | `vision.py` (part 1) |
| 10 | describe_ui — screen captioning | `vision.py` (part 2) |
| 11 | locate_element — object detection | `vision.py` (part 3) |
| 12 | element_finder — smart find + click | `element_finder.py` |

## Phase 4: OCR (Days 13-16)
| Step | Task | Files |
|------|------|-------|
| 13 | GLM-OCR setup + model loader | `ocr_engine.py` (part 1) |
| 14 | read_text — full text extraction | `ocr_engine.py` (part 2) |
| 15 | read_table — table parsing | `ocr_engine.py` (part 3) |
| 16 | read_form + ocr_info — form + metadata | `ocr_engine.py` (part 4) |

## Phase 5: MCP Integration (Days 17-22)
| Step | Task | Files |
|------|------|-------|
| 17 | MCP server skeleton + tool registry | `server.py` (part 1) |
| 18 | Register screen capture tools | `server.py` (part 2) |
| 19 | Register vision tools | `server.py` (part 3) |
| 20 | Register OCR tools | `server.py` (part 4) |
| 21 | Register action tools | `server.py` (part 5) |
| 22 | Register composite tools (find_and_click, etc.) | `server.py` (part 6) |

## Phase 6: Testing & Polish (Days 23-26)
| Step | Task | Files |
|------|------|-------|
| 23 | Install script + requirements | `install.sh`, `requirements.txt` |
| 24 | Integration tests | `tests/test_all.py` |
| 25 | Documentation + usage examples | `README.md` update |
| 26 | OpenClaw MCP config + final demo | `mcp_config.json` |

---

## Progress Log

- [ ] Step 1 — Project init
- [ ] Step 2 — Config
- [ ] Step 3 — Screen capture
- [ ] Step 4 — Click actions
- [ ] Step 5 — Type/keyboard
- [ ] Step 6 — Scroll/drag/hover
- [ ] Step 7 — App launch
- [ ] Step 8 — Safety
- [ ] Step 9 — Florence setup
- [ ] Step 10 — describe_ui
- [ ] Step 11 — locate_element
- [ ] Step 12 — element_finder
- [ ] Step 13 — GLM-OCR setup
- [ ] Step 14 — read_text
- [ ] Step 15 — read_table
- [ ] Step 16 — read_form
- [ ] Step 17 — MCP skeleton
- [ ] Step 18 — Screen tools
- [ ] Step 19 — Vision tools
- [ ] Step 20 — OCR tools
- [ ] Step 21 — Action tools
- [ ] Step 22 — Composite tools
- [ ] Step 23 — Install/requirements
- [ ] Step 24 — Tests
- [ ] Step 25 — Docs
- [ ] Step 26 — OpenClaw config
