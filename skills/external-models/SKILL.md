---
name: external-models
description: "Reference for invoking external AI models (Codex, Gemini, or Claude). Capabilities, flags, strengths, weaknesses, and invocation patterns. Use when you need to shell out to another model for reviews, multimodal analysis, agent tasks, or any cross-model collaboration."
---

# External Model Reference

## Codex CLI

**Model**: gpt-5.3-codex, reasoning level xhigh (configured as default in `~/.codex/config.toml`)
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
- No `--approval-mode` flag — use `--sandbox` instead

### Invocation Patterns

**Read-only review** (most common):
```bash
codex exec - --sandbox read-only -o "$REVIEW_DIR/output.txt" < "$REVIEW_DIR/prompt.txt" 2>&1
```

**Write access** (for edits, test writing, bug fixing):
```bash
codex exec - --sandbox workspace-write -o "$REVIEW_DIR/output.txt" < "$REVIEW_DIR/prompt.txt" 2>&1
```

**Resume a session** (follow-up with a specific session ID):
```bash
codex exec resume "$SESSION_ID" "follow-up question" --sandbox read-only 2>&1
```

### Key Flags
- `-` : read prompt from stdin (always use this — never pass large prompts as args)
- `--sandbox read-only` : prevent writes
- `--sandbox workspace-write` : allow edits to project files
- `-o <file>` : capture final response to file
- Model/effort configured in `~/.codex/config.toml`, no need to pass as flags

### Important
- **Never** pass `--full-auto`
- **Always** build prompts as files, pipe via stdin (`< file`), not as shell arguments
- Sessions persist automatically; resume by UUID (see review skill) to avoid collisions
- Can take 2-5 minutes on large codebases — use generous timeouts (600000ms)

---

## Gemini CLI

**Model**: Default (no `-m` flag needed) — auto-routes between Gemini 3 Pro and Flash
**Explicit models**: `gemini-3-pro-preview`, `gemini-3-flash-preview` (only to force one)
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

### Invocation Patterns

**Read-only review** (build prompt file, pipe via stdin):

Build a prompt file containing the full codebase + instructions (same as the
Codex pattern), then pipe it. Keep the `-p` arg short — Gemini CLI fails
(exit 13) when stdin is large and the inline prompt string is long.

```bash
cat "$REVIEW_DIR/prompt.txt" | gemini -p "Follow the instructions in stdin." \
  --sandbox -o text > "$REVIEW_DIR/output.txt" 2>&1
```

**Multimodal analysis** (images, documents):
```bash
gemini "Analyze this image: [description of what to look for]" --sandbox -o text < image.png 2>&1
```

**Resume a session** (follow-up with a specific session ID):
```bash
echo "follow-up" | gemini -r "$SESSION_ID" --sandbox -o text 2>&1
```

### Key Flags
- `--sandbox` : OS-level write restriction (Seatbelt on macOS)
- `-o text` : readable output format
- `-r <UUID>` : resume a specific session by ID (prefer over `latest`)
- `-p` : non-interactive headless mode
- No `--yolo` or `-y` — never auto-approve tool calls

### Important
- **Always** provide full codebase via stdin (dirgrab output) — Gemini is bad at
  agentic file discovery
- **Always** use `--sandbox` on every invocation
- **Always** include read-only instructions in the prompt (belt and suspenders
  with sandbox)
- dirgrab includes untracked files by default — no need to commit first (only
  `--tracked-only` mode skips uncommitted files)
- Sessions persist; resume by UUID (see review skill) to avoid collisions

---

## Claude

**Model**: opus-4.6
**Training cutoff**: May 2025

If you are a claude model, consider using sub-agents instead of full-fat
separate instances of claude code. If you aren't, consider using claude in cases
that require high-fidelity tool use and agentic behavior. As of Opus 4.6,
Claude is approximately as smart as OpenAI's Codex 5.3 with xhigh reasoning
level, but Claude is drastically faster, and can iterate more rapidly as a
result.

### Strengths
- Always available — no external API, no rate limits, no cost
- Starts fresh as a subagent without implementation bias (good for reviewing
  code you just wrote)
- Fast — no network round-trip to an external CLI
- Strong at nuanced logic issues and architectural reasoning

### Weaknesses
- As the implementer, a Claude subagent shares your training data and biases —
  it may have the same blind spots you do (this is why multi-model review is
  valuable)
- No persistent session for follow-ups (unlike Codex/Gemini)

### Invocation Patterns

**Subagent review** (used in parallel review rounds):

Launch a `general-purpose` subagent via the Task tool. Read the prompt file
built in the review flow and pass its content as the subagent prompt. Have it
write its review to a file.

```
Task(
  subagent_type="general-purpose",
  run_in_background=true,
  prompt="Read the following codebase and review instructions, then write
    your review to $REVIEW_DIR/claude_output.txt using the Write tool.
    [contents of $REVIEW_DIR/prompt.txt]"
)
```

### Important
- Subagents start with a clean context — they don't inherit your conversation
  history, which is a feature for unbiased review
- For parallel reviews, launch the subagent with `run_in_background=true` so it
  runs concurrently with Codex and Gemini
- The subagent has access to Read/Write/Glob/Grep tools but not Bash by default

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
| Implementation | Claude | Smart and faster than codex, faster iteration |
| Quick second opinion | Gemini | Fast, low-effort |
