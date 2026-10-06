#!/usr/bin/env bash
# E2E non-Grok orchestration driver (coordinator-launched; do not run live workers in builder verify).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STATE_ROOT="${1:?usage: $0 <state_root> <fixture_worktree> [--dry-run]}"
WORKTREE="${2:?usage: $0 <state_root> <fixture_worktree> [--dry-run]}"
DRY_RUN=0
if [[ "${3:-}" == "--dry-run" ]]; then
  DRY_RUN=1
fi

export WOLF_INTELLIGENCE_STATE_ROOT="$STATE_ROOT"
mkdir -p "$STATE_ROOT" "$WORKTREE"

SANDBOX_ROOT="${WOLF_INTELLIGENCE_SANDBOX_ROOT:-$HOME/wi-sandboxes}"
if [[ ! -d "$WORKTREE/.git" ]]; then
  mkdir -p "$SANDBOX_ROOT"
  git -C "$ROOT" worktree add "$WORKTREE" -b "e2e-fixture-$(basename "$WORKTREE")" HEAD 2>/dev/null \
    || git -C "$ROOT" worktree add "$WORKTREE" HEAD
fi

mkdir -p "$WORKTREE/fixture"
cat >"$WORKTREE/fixture/hello.py" <<'PY'
def hello():
    return 'hello'
PY
cat >"$WORKTREE/fixture/test_hello.py" <<'PY'
from fixture.hello import hello

def test_hello():
    assert hello() == 'hello'
PY

OK_WORKER="$ROOT/wolf_intelligence/tests/fixtures/orch_worker_ok.py"
mkdir -p "$STATE_ROOT/orchestrator/runtime"
cat >"$STATE_ROOT/orchestrator/config.json" <<EOF
{
  "claude_paused": true,
  "worktree_cwd": "$WORKTREE",
  "worker_cmds": {
    "cursor_sub": [
      "python3", "$OK_WORKER",
      "$STATE_ROOT/orchestrator/runtime/{item_id}-{attempt}.completion.json",
      "PASS", "fixture build ok"
    ],
    "codex_sub": [
      "python3", "$OK_WORKER",
      "$STATE_ROOT/orchestrator/runtime/{item_id}-{attempt}.completion.json",
      "PASS", "fixture review ok"
    ]
  }
}
EOF

ITEM_FILE="$STATE_ROOT/fixture-hello.json"
cat >"$ITEM_FILE" <<'EOF'
{
  "id": "fixture-hello",
  "kind": "build",
  "spec": {
    "prompt": "Add fixture/hello.py with def hello() returning 'hello' and a unit test.",
    "model": "composer-2.5"
  },
  "acceptance": "hello() returns hello and unit test passes",
  "depends_on": [],
  "reviewer_gate": true,
  "timeout_s": 600,
  "max_attempts": 2
}
EOF

python3 -m wolf_intelligence orchestrate submit --file "$ITEM_FILE"

if [[ "$DRY_RUN" == "1" ]]; then
  echo '{"dry_run": true, "state_root": "'"$STATE_ROOT"'", "worktree": "'"$WORKTREE"'"}'
  python3 -m wolf_intelligence orchestrate run >/dev/null
else
  python3 -m wolf_intelligence orchestrate run >/dev/null
fi

SUMMARY="$STATE_ROOT/e2e-summary.json"
python3 - <<PY
import json
from pathlib import Path
from wolf_intelligence import orchestrator as orch

state = Path("$STATE_ROOT")
items = orch.load_items()
completions = sorted(str(p) for p in orch.COMPLETIONS_DIR.glob("*.json"))
summary = {
    "items": items,
    "completion_records": [json.loads(Path(p).read_text()) for p in completions],
    "audit_log": str(orch.AUDIT_PATH),
    "notifications": str(orch.NOTIFICATIONS_PATH),
    "grok_invocations": orch.grok_invocation_count(),
}
Path("$SUMMARY").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"summary": str(summary), "grok_invocations": summary["grok_invocations"]}))
PY
