"""Free MCP server for json-repair-lite (stdio).

Run:  uvx --from git+https://github.com/tidybytetools/json-repair-lite json-repair-lite mcp
  or: uvx --from git+https://github.com/tidybytetools/json-repair-lite json-repair-lite-mcp
"""
import os
from typing import Annotated
from pydantic import Field
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
import json_repair_lite as lite

MAX_BYTES = 5_000_000  # 5 MB is plenty for JSON documents

mcp = FastMCP("json-repair-lite")

READ_ONLY = dict(
    readOnlyHint=True,       # only reads; never writes or changes anything
    destructiveHint=False,
    idempotentHint=True,     # same input always gives the same JSON
    openWorldHint=False,     # no network; works on the text or local file you give it
)

JSON_LINES_HELP = (
    "json_lines: if true, each non-empty line is a separate document. If false (default), "
    "the whole text is tried as one JSON value first. If that cannot be repaired and there "
    "are several lines, each line is then tried on its own."
)


def _check_file(path: str) -> str:
    path = os.path.expanduser(path)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"file not found: {path}")
    if os.path.getsize(path) > MAX_BYTES:
        raise ValueError("file is bigger than 5 MB")
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _bundle_or_raise(text: str, json_lines: bool) -> dict:
    bundle = lite.repair_text(text, json_lines=json_lines)
    if bundle["count"] == 1:
        rec = bundle["documents"][0]
        if not rec.get("ok"):
            raise ValueError(rec["error"])
        return {k: rec[k] for k in ("wasValid", "repaired", "value", "text")}
    return bundle


@mcp.tool(
    title="Repair broken JSON text",
    annotations=ToolAnnotations(title="Repair broken JSON text", **READ_ONLY),
)
def repair_json_text(
    text: Annotated[str, Field(description="The JSON text to repair. May be one value, or several JSON Lines.")],
    json_lines: Annotated[bool, Field(description="If true, treat each non-empty line as its own JSON document.")] = False,
) -> dict:
    """Repair broken or incomplete JSON, including output from language models.

    Use this when you have JSON in the conversation that may be missing quotes,
    have trailing commas, or be cut off. It is plain code, not an AI model: it
    can close missing brackets and fix common syntax issues, but it cannot invent
    the data you meant to write. Already-valid JSON is returned as-is, with
    wasValid true and repaired false. Do not use it for a file on disk (use
    repair_json_file for files).

    json_lines: if true, each non-empty line is a separate document. If false
    (default), the whole text is tried as one JSON value first. If that cannot be
    repaired and there are several lines, each line is then tried on its own.

    For one document, returns {"wasValid", "repaired", "value", "text"}. For
    several documents, returns {"count", "failed", "documents": [...]}.
    """
    return _bundle_or_raise(text, json_lines)


@mcp.tool(
    title="Repair JSON in a local file",
    annotations=ToolAnnotations(title="Repair JSON in a local file", **READ_ONLY),
)
def repair_json_file(
    path: Annotated[str, Field(description="Full path to a UTF-8 .json or .jsonl file, up to 5 MB.")],
    json_lines: Annotated[bool, Field(description="If true, treat each non-empty line as its own JSON document.")] = False,
) -> dict:
    """Read a local JSON file and repair it if it is broken or incomplete.

    Use this when the JSON is in a file on this computer, so you don't have to
    paste it. The file is only read, never changed. Files larger than 5 MB are
    rejected; use the Apify version for bigger jobs. Do not use it for files that
    are not JSON text.

    path: full path to a UTF-8 text file, up to 5 MB.
    json_lines: if true, each non-empty line is a separate document. If false
    (default), the whole text is tried as one JSON value first.

    Returns the same object as repair_json_text.
    """
    text = _check_file(path)
    return _bundle_or_raise(text, json_lines)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
