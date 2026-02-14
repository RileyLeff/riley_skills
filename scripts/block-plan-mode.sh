#!/bin/bash
# Block EnterPlanMode when an active workflow exists (planning/vN/ directory).
# If no workflow is detected, allow plan mode to proceed normally.

cd "$CLAUDE_PROJECT_DIR" 2>/dev/null || exit 0

# Check for versioned architecture directories
if ls planning/v[0-9]* 1>/dev/null 2>&1; then
  echo '{"hookSpecificOutput":{"permissionDecision":"deny"},"systemMessage":"You are in an active workflow session with an existing architecture plan. Do NOT enter plan mode — the architecture plan is your plan. Follow it directly. If you need to re-orient, re-read the workflow skill and the architecture plan instead."}' >&2
  exit 2
fi

# No workflow detected — allow plan mode
exit 0
