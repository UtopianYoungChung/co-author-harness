#!/bin/sh
# Keep stdin intact: it contains the hook event JSON.
set -eu
fail() { echo "HOOK-INTERPRETER: $*" >&2; exit 2; }
run() {
    if "$1" -B "$root/scripts/hooks/codex_gate.py"; then exit 0; fi
    fail "harness hook failed to execute"
}
root=${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-}}
if [ -z "$root" ]; then
    root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
fi
candidate=${COAUTHOR_HOOK_PYTHON:-${CLAUDE_PLUGIN_PYTHON:-}}
if [ -n "$candidate" ]; then
    [ -x "$candidate" ] || fail "configured Python is not executable"
    run "$candidate"
fi
for name in python3 python; do
    candidate=$(command -v "$name" || true)
    case "$candidate" in ''|*WindowsApps*) continue ;; esac
    run "$candidate"
done
fail "set COAUTHOR_HOOK_PYTHON to a Python 3 interpreter with harness dependencies"
