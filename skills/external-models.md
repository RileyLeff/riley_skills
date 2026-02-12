---
name: external-models
description: >
  Reference for invoking external AI models (Codex, Gemini) from Claude Code.
  Capabilities, flags, strengths, weaknesses, and invocation patterns. Use when
  you need to shell out to another model for reviews, multimodal analysis, agent
  tasks, or any cross-model collaboration.
triggers:
  - "use codex"
  - "use gemini"
  - "codex agent"
  - "gemini multimodal"
  - "which model"
  - "external model"
  - "invoke codex"
  - "invoke gemini"
  - "send to codex"
  - "send to gemini"
---

# External Model Reference

## Codex CLI

**Model**: gpt-5.3-codex, reasoning level xhigh (configured in `~/.codex/config.toml`)
**Context**: ~258k tokens with excellent auto-compact

### Strengths
- Strong agent — discovers codebase structure on its own without hand-holding
- Trustworthy for write access when instructed
- Excellent at following specific, well-scoped instructions
- Good at agentic exploration and bug hunting

### Weaknesses
- Can take a very long time on large prompts
- No `--approval-mode` flag — use `--sandbox` instead

### Invocation Patterns

**Read-only review** (most common):
```bash
codex exec - --sandbox read-only -o /tmp/codex-output.txt < /tmp/prompt.txt 2>&1
```

**Write access** (for edits, test writing, bug fixing):
```bash
codex exec - --sandbox workspace-write -o /tmp/codex-output.txt < /tmp/prompt.txt 2>&1
```

**Resume a session** (follow-up questions):
```bash
echo "follow-up question" | codex resume --last --sandbox read-only 2>&1
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
- Sessions persist automatically; use `codex resume --last` for follow-ups
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
- Not great at agentic search or multi-step reasoning
- Quality degrades with very large context even though window allows it

### Invocation Patterns

**Read-only review** (pipe codebase via stdin):
```bash
cat /tmp/context.txt | gemini "You are reviewing this codebase in READ-ONLY mode.
Do NOT edit, write, or modify any files. [PROMPT HERE]" --sandbox -o text 2>&1
```

**Multimodal analysis** (images, documents):
```bash
gemini "Analyze this image: [description of what to look for]" --sandbox -o text < image.png 2>&1
```

**Resume a session**:
```bash
echo "follow-up" | gemini -r latest --sandbox -o text 2>&1
```

### Key Flags
- `--sandbox` : OS-level write restriction (Seatbelt on macOS)
- `-o text` : readable output format
- `-r latest` : resume most recent session
- `-p` : non-interactive headless mode
- No `--yolo` or `-y` — never auto-approve tool calls

### Important
- **Always** provide full codebase via stdin (dirgrab output) — Gemini is bad at
  agentic file discovery
- **Always** use `--sandbox` on every invocation
- **Always** include read-only instructions in the prompt (belt and suspenders
  with sandbox)
- Make sure code is committed before dirgrab or it may miss uncommitted changes
- Sessions persist; use `-r latest` for follow-ups

---

## Claude (self-reference)

**Model**: opus-4.6
**Training cutoff**: May 2025

When orchestrating multi-model work, defer to this file for correct model names
and invocation patterns. If something here looks outdated, tell Riley — he
maintains this file.

---

## Model Selection Guide

| Task | Best Model | Why |
|------|-----------|-----|
| Code review | Codex | Strong reasoning, follows review structure well |
| Bug hunting | Codex (write mode) | Can explore and fix, not just report |
| Architecture review | Codex or Gemini | Both work; Gemini for very large codebases |
| Multimodal (images, docs, OCR) | Gemini | Best multimodal by far |
| Long-context analysis | Gemini | 1M context window |
| Test writing | Codex (write mode) | Good at following test conventions |
| Implementation | Claude (you) | That's your job |
| Quick second opinion | Gemini | Fast, low-effort |
