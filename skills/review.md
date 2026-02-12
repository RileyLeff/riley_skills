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

**Before proceeding, read the external-models skill** at the plugin path
`skills/external-models.md` (relative to this file) for model capabilities and
invocation details. If you can't find it at a relative path, check
`~/.claude/plugins/*/riley_skills/skills/external-models.md` or the
`riley_skills` plugin directory.

## User's Request

$ARGUMENTS

## Step 0: Choose Model

If the user specified a model ("codex review", "gemini review"), use that one.
Otherwise, default to **Codex** for code reviews — it's the stronger reviewer.
Use Gemini when:
- The codebase is very large (>250k tokens) and benefits from Gemini's context
- The review involves images or documents (multimodal)
- The user explicitly asks for Gemini

## Step 1: Gather Context

Run `dirgrab -s --no-tree` to show per-file token breakdowns. If a
`.dirgrabignore` exists, it's used automatically.

```bash
dirgrab -s --no-tree 2>&1 | tail -15
```

If stats look reasonable (under ~250k for Codex, ~500k for Gemini), proceed.
Otherwise, ask the user what to exclude via `-e` flags.

## Step 2: Capture Codebase

Write dirgrab output to a temp file. Always use `--no-tree` (the tree wastes
tokens).

```bash
dirgrab --no-tree -o /tmp/review-context.txt -s 2>&1
```

## Step 3: Build Prompt

Create a prompt file wrapping the codebase. **Never pass codebase content as a
shell argument** — always build a file and pipe it.

```bash
cat > /tmp/review-prompt.txt << 'PROMPT_HEADER'
You are reviewing this codebase in READ-ONLY mode. Do NOT edit, write, or
modify any files. Only analyze and report.

Here is the full codebase:

<codebase>
PROMPT_HEADER

cat /tmp/review-context.txt >> /tmp/review-prompt.txt

cat >> /tmp/review-prompt.txt << 'PROMPT_FOOTER'
</codebase>

[REVIEW_INSTRUCTION]
PROMPT_FOOTER
```

Replace `[REVIEW_INSTRUCTION]` with the user's request, or use the default:
"Review this codebase for architecture quality, potential bugs, security issues,
and areas for improvement. Flag severity: major (must fix), minor (should fix),
or note (observation/tradeoff). Provide specific file and function references."

## Step 4: Run Review

### If Codex:
```bash
codex exec - \
  --sandbox read-only \
  -o /tmp/review-output.txt \
  < /tmp/review-prompt.txt 2>&1
```
Timeout: 600000ms. May take 2-5 minutes.

### If Gemini:
```bash
cat /tmp/review-prompt.txt | gemini \
  "$(cat /tmp/review-prompt.txt)" \
  --sandbox -o text > /tmp/review-output.txt 2>&1
```

Actually, for Gemini, the simpler pattern is:
```bash
cat /tmp/review-context.txt | gemini "You are reviewing this codebase in
READ-ONLY mode. Do NOT edit, write, or modify any files.

[REVIEW_INSTRUCTION]" --sandbox -o text > /tmp/review-output.txt 2>&1
```

## Step 5: Present Results

Read and present the review output to the user.

## Step 6: Follow-up (Optional)

If the user has follow-up questions:

### Codex follow-up:
```bash
echo "follow-up question" | codex resume --last --sandbox read-only 2>&1
```

### Gemini follow-up:
```bash
echo "follow-up question" | gemini -r latest --sandbox -o text 2>&1
```

## Step 7: File Artifacts (if in workflow)

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
