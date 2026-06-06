---
name: external-models
description: "Reference for invoking external AI models and fresh reviewer agents (Codex/GPT, Claude/Claude Code, Gemini via Antigravity CLI). Capabilities, flags, strengths, weaknesses, and invocation patterns. Use when you need to shell out to another model, run reviews, do multimodal analysis, or coordinate one-reviewer-per-family collaboration."
---

# External Model Reference

## Codex CLI

**Model**: gpt-5.5, reasoning level xhigh
**Context**: ~258k tokens with excellent auto-compact

### Strengths
- Strong agent — discovers codebase structure on its own without hand-holding
- Trustworthy for write access when instructed
- Excellent at following specific, well-scoped instructions
- Good at agentic exploration and bug hunting
- Extremely smart, has non-overlapping intelligence with Claude
- Behaves like a "senior engineer"

### Weaknesses
- Can take a very long time on large prompts

### Notes
- No `--approval-mode` flag. Use `--sandbox` and put global approval flags
  before `exec`.

### Invocation Patterns

**Read-only review** (most common):
```bash
codex -a never exec \
  -m gpt-5.5 \
  --sandbox read-only \
  --ephemeral \
  -C "$PWD" \
  -o "$REVIEW_DIR/output.txt" \
  - \
  < "$REVIEW_DIR/prompt.txt" > "$REVIEW_DIR/codex_log.txt" 2>&1
```

**Write access** (for edits, test writing, bug fixing):
```bash
codex -a never exec \
  -m gpt-5.5 \
  --sandbox workspace-write \
  --ephemeral \
  -C "$PWD" \
  -o "$REVIEW_DIR/output.txt" \
  - \
  < "$REVIEW_DIR/prompt.txt" > "$REVIEW_DIR/codex_log.txt" 2>&1
```

**Resume a non-ephemeral session** (follow-up with a specific session ID):
```bash
codex -a never exec resume -m gpt-5.5 "$SESSION_ID" "follow-up question" 2>&1
```

### Key Flags
- `-a never` : global approval policy flag; place before `exec`
- `-` : read prompt from stdin (always use this — never pass large prompts as args)
- `--sandbox read-only` : prevent writes
- `--sandbox workspace-write` : allow edits to project files
- `--ephemeral` : avoid persistent session/state collisions for one-off reviews
- `-C "$PWD"` : run against the intended project directory
- `-o <file>` : capture final response to file
- `-m gpt-5.5` : use GPT 5.5 for serious review and implementation passes

### Important
- **Never** pass `--full-auto`
- **Always** build prompts as files, pipe via stdin (`< file`), not as shell arguments
- The review commands shown above use `--ephemeral`. Drop it deliberately only
  when you want a resumable Codex session and have a collision-safe plan.
- Can take 2-5 minutes on large codebases — use generous timeouts (600000ms)

---

## Gemini via Antigravity CLI (`agy`)

**Model**: `Gemini 3.1 Pro (High)` for serious review work
**Context**: 1M tokens, but quality degrades around ~400k tokens

### Strengths
- Best multimodal by a lot — image analysis, document processing, OCR
- Quantitative/detection tasks in images
- Enormous context window for large codebases
- Good for "read everything and tell me what you think" tasks

### Weaknesses
- Not a good agent — struggles to follow instructions reliably
- Will try to write even when told read-only (hence the sandbox flag)
- Not great at agentic search
- Quality degrades with very large context even though window allows it
- Positional prompt arguments can route to the wrong model; stdin is reliable
- No tested persistent-session workflow for review follow-ups

### Invocation Patterns

**Read-only review** (build prompt file, pipe via stdin):

```bash
agy --print \
  --sandbox \
  --model 'Gemini 3.1 Pro (High)' \
  --print-timeout 10m \
  < "$REVIEW_DIR/prompt.txt" \
  > "$REVIEW_DIR/gemini_output.txt" 2>&1
```

**Quick smoke test**:
```bash
printf 'Reply exactly: agy smoke ok' | agy --print \
  --sandbox \
  --model 'Gemini 3.1 Pro (Low)' \
  --print-timeout 60s
```

### Key Flags
- `--print` : non-interactive mode
- `--sandbox` : OS-level write restriction (Seatbelt on macOS)
- `--model 'Gemini 3.1 Pro (High)'` : use Gemini 3.1 Pro for serious review work
- `--print-timeout 10m` : allow enough time for large review prompts
- No `--output-format` / `-o` flag in `agy`
- No `--yolo` or `-y` - never auto-approve tool calls

### Important
- **Always** provide full codebase via stdin (dirgrab output) - Gemini is bad at
  agentic file discovery, and `agy` positional prompts have been unreliable
- **Always** use `--sandbox` on every invocation
- **Always** include read-only instructions in the prompt (belt and suspenders
  with sandbox)
- dirgrab includes untracked files by default — no need to commit first (only
  `--tracked-only` mode skips uncommitted files)
- Do not use the legacy `gemini` CLI model strings here for serious reviews
  unless you have re-tested them locally. Use `agy` for Gemini 3.1 Pro.
- `agy` output may include stray copied flag text; keep the sandbox anyway and
  merge findings based on substance.

---

## Claude / Claude Code

**Model**: use the rolling Opus alias, `--model opus`
**Training cutoff**: May 2025

As of Claude Code 2.1.167, `--model opus` resolves to
`claude-opus-4-8` (Claude Opus 4.8). Prefer the alias so this skill does not
need to chase Anthropic point releases. The tested CLI does not support a
standalone `--opus` flag.

If you are in Claude Code, prefer fresh Claude subagents to fill the Claude
review slot. If you are in Codex or another harness, use Claude CLI when
available. In either case, the reviewer counts only if it starts from a clean
context and did not implement the change under review.

### Strengths
- Generally available inside Claude Code as a fresh subagent
- Starts fresh as a subagent without implementation bias (good for reviewing
  code you just wrote)
- Fast — no network round-trip to an external CLI
- Strong at nuanced logic issues and architectural reasoning

### Weaknesses
- As the implementer, a Claude subagent shares your training data and biases —
  it may have the same blind spots you do (this is why multi-model review is
  valuable)
- No persistent session for follow-ups in the recommended review flow

### Invocation Patterns

**Subagent review** (used in parallel review rounds):

Launch a `general-purpose` subagent via the Task tool. Read the prompt file
built in the review flow and pass its content as the subagent prompt. Have it
write its review to a file.

```
Task(
  subagent_type="general-purpose",
  model="opus",
  run_in_background=true,
  prompt="Read the following codebase and review instructions, then write
    your review to $REVIEW_DIR/claude_output.txt using the Write tool.
    [contents of $REVIEW_DIR/prompt.txt]"
)
```

**Always specify `model="opus"`** for review subagents. Without it, the
orchestrator may default to haiku, which is fast but too weak for catching bugs.

**Claude CLI read-only review** (when outside Claude Code or when a separate
Claude process is preferred):

```bash
claude \
  --print \
  --model opus \
  --permission-mode plan \
  --tools "" \
  --no-session-persistence \
  --max-budget-usd 5 \
  --output-format text \
  < "$REVIEW_DIR/prompt.txt" \
  > "$REVIEW_DIR/claude_output.txt" 2>&1
```

**Claude CLI tool-assisted pass** (only when you intentionally want it to
explore files itself):

```bash
claude \
  --add-dir "$PWD" \
  --model opus \
  --print \
  "Review this repository for bugs and architectural risks."
```

### Important
- Subagents start with a clean context — they don't inherit your conversation
  history, which is a feature for unbiased review
- For parallel reviews, launch the subagent with `run_in_background=true` so it
  runs concurrently with Codex and Gemini
- The subagent has access to Read/Write/Glob/Grep tools but not Bash by default
- For isolated CLI review rounds, prefer `--tools ""` when the full context is
  already in the prompt so the review stays deterministic

When orchestrating multi-model work, defer to this file for correct model names
and invocation patterns. If something here looks outdated or you find a mismatch
between real-world use and the patterns described in this skill, tell the user
and suggest filing an issue or PR at this skill's
[github repository](https://github.com/rileyleff/riley_skills).


---

## Model Selection Guide

| Task | Best Model | Why |
|------|-----------|-----|
| Code review | All three in parallel | Non-overlapping blind spots; merge for consensus |
| Bug hunting | Codex (write mode) | Can explore and fix, not just report |
| Architecture review | All three in parallel | Same as code review; Gemini shines on large codebases |
| Multimodal (images, docs, OCR) | Gemini | Best multimodal by far |
| Long-context analysis | Gemini | 1M context window |
| Test writing | Codex (write mode) | Good at following test conventions |
| Implementation | Orchestrator's native harness | Keep implementation local; use external reviewers after |
| Quick second opinion | Gemini | Fast, low-effort |
