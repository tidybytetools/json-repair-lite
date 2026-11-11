#!/usr/bin/env python3
"""json-repair-lite (MIT): repair broken or incomplete JSON, including output from language models.

The converter uses the json-repair library and the Python standard library. The MCP
server (json_repair_lite_mcp.py) also needs the mcp package.

Need it at scale or from an AI agent? Use the Apify version:
https://apify.com/tidybytetools/json-repair
"""
from __future__ import annotations

import argparse
import json
import sys

from json_repair import repair_json

__version__ = "1.0.0"
APIFY_URL = "https://apify.com/tidybytetools/json-repair"
PRO_LINE = f"Need it at scale or from an AI agent? Use the Apify version: {APIFY_URL}"


def _loads_ok(text: str):
    try:
        return True, json.loads(text)
    except Exception:
        return False, None


def repair_one(text: str) -> dict:
    raw = text.strip()
    if not raw:
        raise ValueError("The JSON text is empty.")
    if raw.startswith("\ufeff"):
        raw = raw.lstrip("\ufeff")
    ok, value = _loads_ok(raw)
    if ok:
        return {
            "wasValid": True,
            "repaired": False,
            "value": value,
            "text": json.dumps(value, ensure_ascii=False),
        }
    try:
        fixed = repair_json(raw, return_objects=False, ensure_ascii=False)
    except Exception as e:
        raise ValueError(f"Could not repair this JSON: {e}") from e
    if not str(fixed).strip():
        raise ValueError("Could not repair this JSON.")
    ok2, value = _loads_ok(str(fixed))
    if not ok2:
        raise ValueError("The repair step did not produce valid JSON.")
    return {
        "wasValid": False,
        "repaired": True,
        "value": value,
        "text": json.dumps(value, ensure_ascii=False),
    }


def split_documents(text: str, force_lines: bool) -> list[str]:
    raw = (text or "").strip()
    if not raw:
        return []
    if raw.startswith("\ufeff"):
        raw = raw.lstrip("\ufeff")
    if force_lines:
        return [ln.strip() for ln in raw.splitlines() if ln.strip()]
    ok, _ = _loads_ok(raw)
    if ok:
        return [raw]
    # A single broken object may span many lines — try the whole text first.
    try:
        repair_one(raw)
        return [raw]
    except ValueError:
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        if len(lines) > 1:
            return lines
        return [raw]


def repair_text(text: str, json_lines: bool = False) -> dict:
    docs = split_documents(text, json_lines)
    if not docs:
        raise ValueError("The JSON text is empty.")
    results = []
    errors = 0
    for i, doc in enumerate(docs, start=1):
        try:
            rec = repair_one(doc)
            rec["ok"] = True
            rec["index"] = i
            results.append(rec)
        except Exception as e:
            errors += 1
            results.append({"ok": False, "index": i, "error": str(e)})
    return {
        "count": len(results),
        "failed": errors,
        "documents": results,
    }


def run_mcp():
    """Start the stdio MCP server (needs the mcp package, which pip installs for you)."""
    try:
        import json_repair_lite_mcp
    except ImportError as e:
        print(f"error: the MCP server needs the mcp package ({e}). Run: pip install git+https://github.com/tidybytetools/json-repair-lite", file=sys.stderr)
        return 1
    json_repair_lite_mcp.main()
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv == ["mcp"]:
        return run_mcp()
    p = argparse.ArgumentParser(
        prog="json-repair-lite",
        description="Repair broken or incomplete JSON, including output from language models. Run `json-repair-lite mcp` to start the MCP server (to read a file named mcp, use ./mcp).",
        epilog=PRO_LINE,
    )
    p.add_argument("file", nargs="?", help="input file (default: stdin)")
    p.add_argument("--json-lines", action="store_true", help="treat each non-empty line as its own JSON document")
    p.add_argument("--json", action="store_true", help="machine-readable envelope: {ok, count, failed, documents}")
    p.add_argument("--indent", type=int, default=2)
    p.add_argument("-q", "--quiet", action="store_true", help="don't print the one-line note about the Apify version")
    p.add_argument("--version", action="version", version=__version__)
    a = p.parse_args(argv)
    try:
        text = open(a.file, encoding="utf-8-sig").read() if a.file else sys.stdin.read()
        bundle = repair_text(text, json_lines=a.json_lines)
        failed = bundle["failed"]
        if a.json:
            out = {"ok": failed == 0, **bundle}
            print(json.dumps(out, indent=a.indent, ensure_ascii=False))
        elif bundle["count"] == 1:
            rec = bundle["documents"][0]
            if not rec.get("ok"):
                raise ValueError(rec["error"])
            print(json.dumps(rec["value"], indent=a.indent, ensure_ascii=False))
        else:
            # JSON Lines: one compact document per line
            for rec in bundle["documents"]:
                if rec.get("ok"):
                    print(rec["text"])
                else:
                    print(json.dumps({"ok": False, "index": rec["index"], "error": rec["error"]}, ensure_ascii=False))
        if not a.quiet and not a.json and sys.stderr.isatty():
            print(PRO_LINE, file=sys.stderr)
        return 1 if failed else 0
    except Exception as e:
        if getattr(a, "json", False):
            print(json.dumps({"ok": False, "error": str(e)}))
            return 1
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
