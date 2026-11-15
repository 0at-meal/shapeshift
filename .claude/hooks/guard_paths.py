"""PreToolUse hook: block edits to secrets and to locked test files.

Locked tests are listed one path per line in .claude/locked-tests.txt
(add a test there while fixing a bug test-first, remove it afterwards).
Exit code 2 blocks the edit and sends the message back to Claude.
"""
import json
import pathlib
import sys

event = json.load(sys.stdin)
path = event.get("tool_input", {}).get("file_path", "")

blocked = [".env", "secrets/"]
locked_file = pathlib.Path(".claude/locked-tests.txt")
locked = [
    line.strip()
    for line in (locked_file.read_text().splitlines() if locked_file.exists() else [])
    if line.strip() and not line.strip().startswith("#")
]

if any(b in path for b in blocked) or any(path.endswith(t) for t in locked):
    print(f"Blocked: {path} is protected. Change the code, not this file.", file=sys.stderr)
    sys.exit(2)
