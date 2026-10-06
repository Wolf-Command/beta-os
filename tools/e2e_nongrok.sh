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
mkdir -p "$STATE_ROOT"

SANDBOX_ROOT="${WOLF_INTELLIGENCE_SANDBOX_ROOT:-$HOME/wi-sandboxes}"
if [[ -f "$WORKTREE/fixture/hello.py" ]]; then
  echo "refusing stale fixture: $WORKTREE/fixture/hello.py already exists" >&2
  exit 1
fi

if [[ ! -d "$WORKTREE/.git" ]]; then
  mkdir -p "$SANDBOX_ROOT"
  git -C "$ROOT" worktree add "$WORKTREE" -b "e2e-fixture-$(basename "$WORKTREE")" HEAD 2>/dev/null \
    || git -C "$ROOT" worktree add "$WORKTREE" HEAD
fi

mkdir -p "$WORKTREE/fixture" "$STATE_ROOT/orchestrator/runtime"

START_TS="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

if [[ "$DRY_RUN" == "1" ]]; then
  OK_WORKER="$ROOT/wolf_intelligence/tests/fixtures/orch_worker_ok.py"
  cat >"$WORKTREE/fixture/hello.py" <<'PY'
def hello():
    return 'hello'
PY
  cat >"$WORKTREE/fixture/test_hello.py" <<'PY'
from fixture.hello import hello

def test_hello():
    assert hello() == 'hello'
PY
  cat >"$STATE_ROOT/orchestrator/config.json" <<EOF
{
  "claude_paused": true,
  "worktree_cwd": "$WORKTREE",
  "dry_run": true,
  "allow_fixture_workers": true,
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
else
  cat >"$STATE_ROOT/orchestrator/config.json" <<EOF
{
  "claude_paused": true,
  "worktree_cwd": "$WORKTREE"
}
EOF
fi

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

RUN_JSON="$STATE_ROOT/orchestrate-run.json"
if [[ "$DRY_RUN" == "1" ]]; then
  echo '{"dry_run": true, "state_root": "'"$STATE_ROOT"'", "worktree": "'"$WORKTREE"'"}'
fi
python3 -m wolf_intelligence orchestrate run >"$RUN_JSON"

END_TS="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

SUMMARY="$STATE_ROOT/e2e-summary.json"
python3 - <<PY
import json
from pathlib import Path
from wolf_intelligence import orchestrator as orch

state = Path("$STATE_ROOT")
run_data = json.loads(Path("$RUN_JSON").read_text(encoding="utf-8"))
workers = []
for round in run_data.get("history") or []:
    for proc in round.get("processed") or []:
        if proc.get("action") != "dispatched":
            continue
        workers.append({
            "work_item_id": proc.get("work_item_id"),
            "worker": proc.get("worker"),
            "pid": proc.get("pid"),
            "exit_code": proc.get("exit_code"),
            "status": proc.get("status"),
        })
items = orch.load_items()
completions = sorted(str(p) for p in orch.COMPLETIONS_DIR.glob("*.json"))
summary = {
    "start_timestamp": "$START_TS",
    "end_timestamp": "$END_TS",
    "dry_run": $DRY_RUN == 1,
    "items": items,
    "workers": workers,
    "completion_records": [json.loads(Path(p).read_text()) for p in completions],
    "audit_log": str(orch.AUDIT_PATH),
    "notifications": str(orch.NOTIFICATIONS_PATH),
    "grok_invocations": orch.grok_invocation_count(),
}
Path("$SUMMARY").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"summary": str(summary), "grok_invocations": summary["grok_invocations"]}))
PY
