"""Stop hook: refuse "done" until the verify command passes.

The verify command is set by docs/adr/0001-stack.md; change it there first.
"""
import json
import subprocess
import sys

VERIFY_CMD = "pnpm verify"

event = json.load(sys.stdin)
if event.get("stop_hook_active"):
    sys.exit(0)  # already sent back once; avoid an endless loop

result = subprocess.run(VERIFY_CMD, shell=True, capture_output=True, text=True)
if result.returncode != 0:
    print(
        "Verify failed. Fix before finishing:\n" + result.stdout[-3000:] + result.stderr[-2000:],
        file=sys.stderr,
    )
    sys.exit(2)
