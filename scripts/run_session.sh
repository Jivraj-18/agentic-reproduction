#!/usr/bin/env bash
# Run one reproducer as its own Claude Code session inside its sandbox, and record its cost.
#
# The session starts in the sandbox folder and is given only file tools and Bash (--tools), with no
# MCP servers, skills or slash commands from the user's own setup; web tools and subagents are disallowed. Its full transcript (stream-json) is saved for the path and hard-coding audits,
# and the final result event's cost and token counts go to eval/cost_<run>.json.
#
# Usage: scripts/run_session.sh <paper_dir> <run_name> <model> [budget_usd]
#   e.g. scripts/run_session.sh work/paperA r_opus claude-opus-5-5
set -euo pipefail
# Auth: the long-lived token from `claude setup-token`, read from a file outside the repo (never printed).
token_file="$HOME/.claude/reproducer_oauth_token"
if [ -z "${CLAUDE_CODE_OAUTH_TOKEN:-}" ] && [ -f "$token_file" ]; then
  CLAUDE_CODE_OAUTH_TOKEN=$(tr -d '[:space:]' < "$token_file"); export CLAUDE_CODE_OAUTH_TOKEN
fi
[ -n "${CLAUDE_CODE_OAUTH_TOKEN:-}" ] || { echo "No setup-token: put it in $token_file" >&2; exit 2; }
paper=$(cd "$1" && pwd); run=$2; model=$3; budget=${4:-15}
sandbox="$paper/sandbox/$run"
mkdir -p "$paper/eval/transcripts"
transcript="$paper/eval/transcripts/$run.jsonl"
start=$(date +%s)
(cd "$sandbox" && claude -p "Read TASK.md in this folder and complete the task exactly as it describes." \
  --model "$model" \
  --output-format stream-json --verbose \
  --tools "Read,Write,Edit,Glob,Grep,Bash,PowerShell" \
  --allowedTools "Read" "Write" "Edit" "Glob" "Grep" "Bash" "PowerShell" \
  --disallowedTools "WebFetch" "WebSearch" "Agent" "Task" \
  --strict-mcp-config --disable-slash-commands \
  --max-budget-usd "$budget" \
  < /dev/null > "$transcript")
end=$(date +%s)
python=$(dirname "$0")/../.venv/Scripts/python.exe
"$python" -I - "$transcript" "$paper/eval/cost_$run.json" "$model" "$((end - start))" <<'EOF'
import json, sys
transcript, out, model, wall = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
result = None
for line in open(transcript, encoding="utf-8"):
    try:
        ev = json.loads(line)
    except ValueError:
        continue
    if ev.get("type") == "result":
        result = ev
rec = {"model": model, "wall_seconds": wall}
if result:
    rec.update({k: result.get(k) for k in ("subtype", "is_error", "total_cost_usd", "duration_ms", "duration_api_ms",
                                           "num_turns", "usage", "modelUsage")})
json.dump(rec, open(out, "w", encoding="utf-8"), indent=1)
print(out, "cost $%s" % rec.get("total_cost_usd"), "turns", rec.get("num_turns"), "wall %ds" % wall)
EOF
