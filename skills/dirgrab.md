---
name: dirgrab
description: >
  Gather codebase context with dirgrab. Walks a directory, finds relevant files
  (respecting git context and .gitignore), and concatenates their contents into
  a single output. Use when you need a code snapshot for analysis, review, or
  sharing with external tools.
triggers:
  - "grab the code"
  - "get codebase context"
  - "code snapshot"
  - "prepare for code review"
  - "dirgrab"
  - "gather context"
allowed-tools:
  - Bash
  - Read
---

# dirgrab - Codebase Context Gathering

`dirgrab` is a CLI tool that walks a directory, finds relevant files (respecting
git context and .gitignore), and concatenates their contents into a single
output. It's useful for gathering code context to share with LLMs or external
tools.

## Basic Usage

```bash
# Output to stdout
dirgrab

# Copy to clipboard (good for piping to other tools like Gemini CLI)
dirgrab -c

# Write to a temp file (best for passing to other tools)
dirgrab -o /tmp/codebase.txt
```

## Token Efficiency

When gathering code for LLM consumption, token count matters. Use `-s` to see
output statistics including approximate token counts:

```bash
dirgrab -s
```

This prints per-file token breakdowns, helping you identify files that are
hogging tokens. Common culprits:
- Lock files (`package-lock.json`, `Cargo.lock`, `*.lock`)
- Planning/documentation directories (`planning/`, `docs/`, `*.md`)
- Build artifacts (`dist/`, `build/`, `target/`)
- Generated files (`*.generated.*`, `*.min.js`)
- Large data files or fixtures

## Exclusion Patterns

Use `-e` to exclude files/directories with gitignore-style globs:

```bash
dirgrab -c -s -e "*.lock" -e "package-lock.json" -e "planning/**"
```

Choose exclusions based on what's relevant for the task:
- For a code review: exclude tests, docs, lock files
- For debugging: maybe include tests but exclude unrelated directories
- For architecture overview: exclude implementation details, keep structure

## Key Flags

| Flag | Description |
|------|-------------|
| `-c, --clipboard` | Copy output to clipboard |
| `-o [FILE]` | Write to file (defaults to `dirgrab.txt` if no path given) |
| `-s, --stats` | Show token/size statistics (helps identify bloat) |
| `-e PATTERN` | Exclude pattern (can be used multiple times) |
| `--no-tree` | Skip directory structure overview |
| `--no-headers` | Skip `--- FILE: name ---` headers |
| `--tracked-only` | Only include git-tracked files |

## .dirgrabignore

If a `.dirgrabignore` file exists in the project root, dirgrab uses it
automatically (gitignore syntax). Good for projects where you always want
the same exclusions.

## Composing with Other Tools

dirgrab gathers context that gets piped to other tools:

```bash
# Save to file for a review skill
dirgrab --no-tree -o /tmp/review-context.txt -s

# Pipe to Gemini CLI directly
dirgrab -c -s -e "*.lock" && gemini "review this code"

# Save and reference
dirgrab -o /tmp/code.txt -s && cat /tmp/code.txt | some-other-tool
```

When composing with external tools, use `-c` (clipboard) or `-o` (file output)
to capture the output cleanly.
