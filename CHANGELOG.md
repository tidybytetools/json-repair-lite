# Changelog

What changed in json-repair-lite, newest first.

## 1.0.0 - 2026-11-10

- First release.
- Repairs broken or incomplete JSON, including output from language models. Already-valid JSON is reported honestly.
- Optional `--json-lines` treats each non-empty line as its own document.
- `--json` gives one clean object for scripts and AI agents. `--quiet` hides the tip line.
- A free MCP server with two read-only tools: `repair_json_text` and `repair_json_file`.
- Needs Python 3.10 or newer, plus the json-repair library.
