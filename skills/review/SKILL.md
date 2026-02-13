---
name: review
description: "Run a code review using parallel multi-model consensus (Codex + Gemini + Claude subagent) or a single model. Gathers codebase context with dirgrab, launches reviewers concurrently, merges findings, and presents structured results with graceful degradation."
---

# Code Review

**Before proceeding, read these skills** from this plugin's `skills/` directory:
- `skills/external-models/SKILL.md` — model capabilities and invocation details
- `skills/dirgrab/SKILL.md` — how to gather codebase context

If you can't find them at a relative path, check
`~/.claude/plugins/cache/*/riley-skills/skills/` or the `riley-skills` plugin
directory.

## User's Request

$ARGUMENTS

## Step 0: Choose Mode

**Parallel mode** (default): Run Codex, Gemini, and a Claude subagent
concurrently against the full codebase, then merge findings. Use this when:
- The user says "review" without specifying a model
- This review is invoked from the **workflow** skill
- The user explicitly asks for "parallel review"

**Single-model mode**: Run one model only. Use this when:
- The user specifies a model ("codex review", "gemini review", "claude review")
- Only one model is available (others rate-limited or not installed)

## Step 1: Create Temp Directory

Create a unique temp directory for this review session to avoid collisions with
other concurrent agent sessions:

```bash
REVIEW_DIR=$(mktemp -d /tmp/review-XXXXXXXX)
echo "Review temp dir: $REVIEW_DIR"
```

Use `$REVIEW_DIR` for all files in this review. **Never use hardcoded paths
like `/tmp/review-context.txt`** — multiple sessions will collide.

## Step 2: Gather Context

Run `dirgrab -s --no-tree` to show per-file token breakdowns. If a
`.dirgrabignore` exists, it's used automatically.

```bash
dirgrab -s --no-tree 2>&1 | tail -15
```

**Token budget check:**
- Under ~250k tokens: all three models can participate
- 250k–500k tokens: drop Codex (its 258k context is too tight), run Gemini +
  Claude subagent only
- Over ~500k tokens: ask the user what to exclude via `-e` flags

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

### Parallel Mode

Launch all available models concurrently. Each writes to its own output file.
Use background execution so they run simultaneously.

**Codex** (background bash):
```bash
codex exec - \
  --sandbox read-only \
  -o "$REVIEW_DIR/codex_output.txt" \
  < "$REVIEW_DIR/prompt.txt" 2>&1 &
CODEX_PID=$!
```
Timeout: 600000ms.

**Gemini** (background bash):
```bash
cat "$REVIEW_DIR/prompt.txt" | gemini -p "Follow the instructions in stdin." \
  --sandbox -o text > "$REVIEW_DIR/gemini_output.txt" 2>&1 &
GEMINI_PID=$!
```

**Claude subagent** (Task tool):

Launch a `general-purpose` subagent with `run_in_background=true`. The prompt
should include the full contents of `$REVIEW_DIR/prompt.txt` and instruct the
subagent to write its review to `$REVIEW_DIR/claude_output.txt`.

**Wait for all to complete:**
```bash
wait $CODEX_PID 2>/dev/null; CODEX_EXIT=$?
wait $GEMINI_PID 2>/dev/null; GEMINI_EXIT=$?
```
Check the Claude subagent's background task output as well.

**Check results:**
- If a model exited non-zero or produced empty output, log the failure and
  continue with the others
- At least one model must succeed for the round to be valid
- If all three fail, report the errors and abort

### Single-Model Mode

#### If Codex:
```bash
codex exec - \
  --sandbox read-only \
  -o "$REVIEW_DIR/codex_output.txt" \
  < "$REVIEW_DIR/prompt.txt" 2>&1
```
Timeout: 600000ms. May take 2-5 minutes.

#### If Gemini:

Pipe the prompt file via stdin with a short `-p` flag — **never** pass a long
inline prompt string, as Gemini CLI fails (exit 13) when stdin is large and the
positional prompt arg is long.

```bash
cat "$REVIEW_DIR/prompt.txt" | gemini -p "Follow the instructions in stdin." \
  --sandbox -o text > "$REVIEW_DIR/gemini_output.txt" 2>&1
```

#### If Claude subagent:

Launch a `general-purpose` subagent via the Task tool with the prompt file
content. Have it write its review to `$REVIEW_DIR/claude_output.txt`.

## Step 6: Merge Results (Parallel Mode Only)

Read all successful output files and synthesize into a single merged finding
list. This is done by you (the orchestrating Claude), not by an external model.

**Merge rules:**
- **Deduplicate**: Same bug described differently by multiple models → one entry.
  Credit all models that found it.
- **Tag consensus**: Findings flagged by 2+ models → mark `[consensus]`. These
  are high-confidence issues.
- **Tag single-model**: Findings from only one model → mark with the source
  (e.g., `[codex-only]`, `[gemini-only]`, `[claude-only]`). These are worth
  investigating but may be false positives.
- **Normalize severity**: Use major (must fix) / minor (should fix) / note
  (observation/tradeoff). If models disagree on severity, use the highest.
- **Preserve specifics**: Keep file paths, line numbers, and function references
  from the most detailed report.

Write the merged output to `$REVIEW_DIR/merged_review.md`.

**Header for merged review:**
```markdown
# Review Round — [date]

**Models**: Codex, Gemini, Claude (or whichever participated)
**Context**: ~Nk tokens

## Findings

### Major
...

### Minor
...

### Notes
...
```

## Step 7: Capture Session IDs

For Codex and Gemini only (Claude subagent doesn't have persistent sessions).
**Never use `--last` or `latest`** — parallel sessions will collide.

### Codex:
```bash
SESSION_ID=$(ls -t ~/.codex/sessions/$(date -u +%Y/%m/%d)/*.jsonl 2>/dev/null \
  | head -1 \
  | grep -oE '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
echo "$SESSION_ID" > "$REVIEW_DIR/codex_session_id"
```

### Gemini:
```bash
SESSION_ID=$(gemini --list-sessions 2>/dev/null \
  | grep -oE '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}' \
  | tail -1)
echo "$SESSION_ID" > "$REVIEW_DIR/gemini_session_id"
```

If a UUID capture fails (empty string), warn the user that follow-ups for that
model may not work reliably, but continue.

## Step 8: Present Results

**Parallel mode**: Present the merged review from Step 6. Note which models
participated and if any were unavailable (e.g., "Codex hit rate limits; this
round used Gemini + Claude only").

**Single-model mode**: Read and present the model's output directly.

## Step 9: Follow-up (Optional)

If the user has follow-up questions, resume the relevant model's session.

### Codex follow-up:
```bash
SESSION_ID=$(cat "$REVIEW_DIR/codex_session_id")
codex exec resume "$SESSION_ID" "follow-up question" --sandbox read-only 2>&1
```

### Gemini follow-up:
```bash
SESSION_ID=$(cat "$REVIEW_DIR/gemini_session_id")
echo "follow-up question" | gemini -r "$SESSION_ID" --sandbox -o text 2>&1
```

Follow-ups are mostly relevant for single-model mode. In parallel mode, the
merged review usually has enough context to act on directly.

## Step 10: File Artifacts (if in workflow)

If this review is part of a workflow session (check if `planning/reviews/`
exists), file the review output:

1. Determine the current architecture version directory (e.g.,
   `planning/reviews/v1/`)
2. Find the next review number N
3. **Parallel mode**: Save merged review as
   `planning/reviews/vX/NN_review_round.md`
4. **Single-model mode**: Save as `planning/reviews/vX/NN_MODEL_review.md`

If not in a workflow session, skip artifact filing unless the user asks for it.

## Graceful Degradation

External models can hit rate limits or fail. Handle this without stopping:

| Situation | Action |
|-----------|--------|
| Codex rate-limited or fails | Drop Codex, continue with Gemini + Claude |
| Gemini rate-limited or fails | Drop Gemini, continue with Codex + Claude |
| Both external models fail | Claude subagent only (always available, no rate limits, no API cost) |
| Claude subagent fails | This shouldn't happen (in-process), but fall back to whichever external model is available |

Log which models participated in each round. If degraded, note it when
presenting results so the user knows the round had reduced coverage.

In a multi-round review loop (workflow exhaustive review), if a model recovers
in a later round, add it back. Don't permanently exclude a model because it
failed once.

## Safety Rules

- **Never** use write-mode sandbox for reviews
- **Never** pass `--full-auto` (Codex) or `--yolo` (Gemini)
- **Always** sandbox: `--sandbox read-only` (Codex) or `--sandbox` (Gemini)
- **Always** build prompts as files, never as shell arguments
- **Always** include read-only instructions in the prompt text (belt + suspenders)
