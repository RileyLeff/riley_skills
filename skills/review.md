---
name: review
description: >
  Run a code review using an external model (Codex or Gemini). Gathers codebase
  context with dirgrab, sends to the chosen model in read-only sandbox mode,
  and presents structured results. Supports follow-up sessions.
triggers:
  - "code review"
  - "codex review"
  - "gemini review"
  - "run a review"
  - "review the code"
  - "get a review"
  - "external review"
allowed-tools:
  - Bash
  - Read
  - Glob
  - AskUserQuestion
---

# Code Review with External Model

**Before proceeding, read these skills** from this plugin's `skills/` directory:
- `skills/external-models.md` — model capabilities and invocation details
- `skills/dirgrab.md` — how to gather codebase context

If you can't find them at a relative path, check
`~/.claude/plugins/*/riley_skills/skills/` or the `riley_skills` plugin
directory.

## User's Request

$ARGUMENTS

## Step 0: Choose Model

If the user specified a model ("codex review", "gemini review"), use that one.
Otherwise, default to **Codex** for code reviews — it's the stronger reviewer.
Use Gemini when:
- The codebase is very large (>250k tokens) and benefits from Gemini's context
- The review involves images or documents (multimodal)
- The user explicitly asks for Gemini

## Step 1: Create Temp Directory

Create a unique temp directory for this review session to avoid collisions with
other concurrent agent sessions:

```bash
REVIEW_DIR=$(mktemp -d /tmp/review-XXXXXXXX)
echo "Review temp dir: $REVIEW_DIR"
```

Use `$REVIEW_DIR/context.txt`, `$REVIEW_DIR/prompt.txt`,
`$REVIEW_DIR/output.txt`, and `$REVIEW_DIR/session_id` for all files in this
review. **Never use hardcoded paths like `/tmp/review-context.txt`** — multiple
sessions will collide.

## Step 2: Gather Context

Run `dirgrab -s --no-tree` to show per-file token breakdowns. If a
`.dirgrabignore` exists, it's used automatically.

```bash
dirgrab -s --no-tree 2>&1 | tail -15
```

If stats look reasonable (under ~250k for Codex, ~500k for Gemini), proceed.
Otherwise, ask the user what to exclude via `-e` flags.

## Step 3: Capture Codebase

Write dirgrab output to a temp file. Always use `--no-tree` (the tree wastes
tokens).

```bash
dirgrab --no-tree -o "$REVIEW_DIR/context.txt" -s 2>&1
```

## Step 4: Build Prompt

Create a prompt file wrapping the codebase. **Never pass codebase content as a
shell argument** — always build a file and pipe it.

```bash
cat > "$REVIEW_DIR/prompt.txt" << 'PROMPT_HEADER'
You are reviewing this codebase in READ-ONLY mode. Do NOT edit, write, or
modify any files. Only analyze and report.

Here is the full codebase:

<codebase>
PROMPT_HEADER

cat "$REVIEW_DIR/context.txt" >> "$REVIEW_DIR/prompt.txt"

cat >> "$REVIEW_DIR/prompt.txt" << 'PROMPT_FOOTER'
</codebase>

[REVIEW_INSTRUCTION]
PROMPT_FOOTER
```

Replace `[REVIEW_INSTRUCTION]` with the user's request, or use the default:
"Review this codebase for architecture quality, potential bugs, security issues,
and areas for improvement. Flag severity: major (must fix), minor (should fix),
or note (observation/tradeoff). Provide specific file and function references."

## Step 5: Run Review

### If Codex:
```bash
codex exec - \
  --sandbox read-only \
  -o "$REVIEW_DIR/output.txt" \
  < "$REVIEW_DIR/prompt.txt" 2>&1
```
Timeout: 600000ms. May take 2-5 minutes.

### If Gemini:

```bash
cat "$REVIEW_DIR/context.txt" | gemini "You are reviewing this codebase in
READ-ONLY mode. Do NOT edit, write, or modify any files.

[REVIEW_INSTRUCTION]" --sandbox -o text > "$REVIEW_DIR/output.txt" 2>&1
```

## Step 6: Capture Session ID

Immediately after the review command returns, capture the session UUID so
follow-ups target the correct session. **Never use `--last` or `latest`** —
parallel agent sessions will collide.

### If Codex:
```bash
SESSION_ID=$(ls -t ~/.codex/sessions/$(date -u +%Y/%m/%d)/*.jsonl 2>/dev/null \
  | head -1 \
  | grep -oE '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
echo "$SESSION_ID" > "$REVIEW_DIR/session_id"
```

### If Gemini:
```bash
SESSION_ID=$(gemini --list-sessions 2>/dev/null \
  | grep -oE '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}' \
  | tail -1)
echo "$SESSION_ID" > "$REVIEW_DIR/session_id"
```

If the UUID capture fails (empty string), warn the user that follow-ups may not
work reliably, but continue presenting the review.

## Step 7: Present Results

Read and present the review output to the user.

## Step 8: Follow-up (Optional)

If the user has follow-up questions, read the session ID from
`$REVIEW_DIR/session_id` and resume that specific session.

### Codex follow-up:
```bash
SESSION_ID=$(cat "$REVIEW_DIR/session_id")
codex exec resume "$SESSION_ID" "follow-up question" --sandbox read-only 2>&1
```

### Gemini follow-up:
```bash
SESSION_ID=$(cat "$REVIEW_DIR/session_id")
echo "follow-up question" | gemini -r "$SESSION_ID" --sandbox -o text 2>&1
```

## Step 9: File Artifacts (if in workflow)

If this review is part of a workflow session (check if `planning/reviews/`
exists), file the review output:

1. Determine the current architecture version directory (e.g., `planning/reviews/v1/`)
2. Find the next review number N
3. Save as `planning/reviews/vX/NN_MODEL_review.md`

If not in a workflow session, skip artifact filing unless the user asks for it.

## Safety Rules

- **Never** use write-mode sandbox for reviews
- **Never** pass `--full-auto` (Codex) or `--yolo` (Gemini)
- **Always** sandbox: `--sandbox read-only` (Codex) or `--sandbox` (Gemini)
- **Always** build prompts as files, never as shell arguments
- **Always** include read-only instructions in the prompt text (belt + suspenders)
