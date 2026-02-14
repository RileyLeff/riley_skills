#!/bin/bash
# Before compaction, inject a reminder to re-read the workflow skill if a
# workflow is active. This ensures critical workflow instructions survive
# context compression.

cd "$CLAUDE_PROJECT_DIR" 2>/dev/null || exit 0

# Check for versioned architecture directories
if ls planning/v[0-9]* 1>/dev/null 2>&1; then
  # Find the latest architecture version
  LATEST_V=$(ls -d planning/v[0-9]* 2>/dev/null | sort -V | tail -1)

  cat <<EOF
{"systemMessage":"WORKFLOW SESSION ACTIVE. After compaction, you MUST re-read these files before continuing:\n1. ${LATEST_V}/WORKFLOW_STATE.md — your current progress and next step\n2. The workflow skill: skills/workflow/SKILL.md (from the riley-skills plugin)\n3. The architecture plan in ${LATEST_V}/\n4. The review skill: skills/review/SKILL.md (parallel multi-model reviews are the default)\n5. ${LATEST_V}/AGENT_WHITEBOARD.md if it exists\n\nKey rules that must survive compaction:\n- Reviews use parallel multi-model consensus (Codex + Gemini + Claude opus subagent)\n- Do NOT enter plan mode — the architecture plan is your plan\n- Graceful degradation: if a model hits rate limits, continue with the others\n- Send progress notifications via slack_notify every 3 review rounds and at phase boundaries\n- Update WORKFLOW_STATE.md after every step, review round, and phase transition"}
EOF
fi

exit 0
