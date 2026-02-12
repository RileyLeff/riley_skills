---
name: dirgrab
description: "Gather codebase context with dirgrab. Walks a directory, finds relevant files (respecting git context and .gitignore), and concatenates their contents into a single output. Use when you need a code snapshot for analysis, review, or sharing with external tools like Gemini or Codex."
---

# dirgrab - Codebase Context Gathering

`dirgrab` walks a directory (or Git repo), selects the files that matter, and
concatenates their contents into a single output for LLM consumption. It
respects `.gitignore`, includes untracked files by default, and produces
deterministically-ordered output.

## Installation

If `dirgrab` is not installed, tell the user and offer these options:

```bash
# Homebrew (macOS/Linux)
brew tap rileyleff/rileytap && brew install dirgrab

# Cargo (any platform with Rust)
cargo install dirgrab
```

Source: https://github.com/rileyleff/dirgrab

## Quick Start

```bash
# Preview what files will be included (dry run — no content read)
dirgrab -l

# Output to stdout with stats
dirgrab -s

# Write to file for external tools (best for reviews)
REVIEW_DIR=$(mktemp -d /tmp/review-XXXXXXXX)
dirgrab --no-tree -o "$REVIEW_DIR/context.txt" -s

# Copy to clipboard
dirgrab -c
```

## Always Preview First

Use `-l/--list` before a full grab to verify your exclusions are right. This
prints one file path per line without reading any content — fast and free:

```bash
# Check what would be included
dirgrab -l -e '*.lock,planning/'

# Then grab for real
dirgrab --no-tree -o /tmp/context.txt -e '*.lock,planning/' -s
```

This prevents the "grabbed 200k tokens of garbage" problem.

## Token Efficiency

Use `-s` to see output statistics (printed to stderr):

```bash
dirgrab -s --no-tree 2>&1 | tail -10
```

Output includes total size, word count, approximate token count, and a
per-file token leaderboard. Common token hogs:
- **Lock files**: `Cargo.lock`, `package-lock.json` (~10k+ tokens each)
- **Planning/review artifacts**: `planning/`, old review outputs
- **Build artifacts**: `target/`, `dist/`, `node_modules/`
- **Generated/minified files**: `*.min.js`, `*.generated.*`
- **Large data files**: fixtures, CSVs, sample PDFs

## Exclusion Patterns

`-e` accepts comma-separated gitignore-style globs. This is the most concise
way to exclude multiple patterns:

```bash
# Comma-separated (preferred — one flag, multiple patterns)
dirgrab -e '*.lock,planning/,*.csv,target/'

# Multiple -e flags (also works)
dirgrab -e '*.lock' -e 'planning/'
```

**Important**: Always quote `-e` values to prevent shell glob expansion.

Suggested exclusions by task:
- **Code review**: `-e '*.lock,planning/,*.csv,docs/'`
- **Debugging**: `-e '*.lock,target/,dist/'` (keep tests)
- **Architecture overview**: `-e '*.lock,*.test.*,__tests__/'`

## Output Format

dirgrab output has this structure (important for parsing):

```
---
DIRECTORY STRUCTURE
---

<indented tree>

---
FILE CONTENTS
---

--- FILE: relative/path/to/file.rs ---
<file contents>

--- FILE: relative/path/to/other.py ---
<file contents>
```

- **Tree section**: Directory structure overview. Skipped with `--no-tree`.
  Almost always use `--no-tree` for LLM consumption — the tree is redundant
  since file headers already show the structure, and it wastes tokens.
- **File headers**: `--- FILE: <path> ---` lines separate files. Paths are
  relative to repo root (git mode) or target directory (no-git mode).
- **PDF files**: Extracted text appears inline. Failed extractions show
  `--- FILE: path (PDF extraction failed) ---`.

## Key Flags

| Flag | Description |
|------|-------------|
| `-l, --list` | Dry-run: print file paths only (no content) |
| `-c, --clipboard` | Copy output to clipboard |
| `-o [FILE]` | Write to file (defaults to `dirgrab.txt`) |
| `-s, --stats` | Show token/size stats on stderr |
| `-e PATTERN` | Exclude patterns (comma-separated or repeated) |
| `--no-tree` | Skip directory tree (recommended for LLM use) |
| `--no-headers` | Skip `--- FILE: ---` headers |
| `--tracked-only` | Only include git-tracked files |
| `--all-repo` | Include entire repo even from a subdirectory |
| `--no-git` | Ignore git context, walk filesystem directly |
| `--no-config` | Ignore config files and `.dirgrabignore` |

## Configuration

dirgrab layers config in this order (later wins):
1. Built-in defaults
2. Global config: `~/.config/dirgrab/config.toml` + `ignore`
3. Project config: `<target>/.dirgrab.toml` + `.dirgrabignore`
4. CLI flags

### .dirgrabignore

If a `.dirgrabignore` exists in the project root, dirgrab uses it
automatically. Uses gitignore syntax. Recommended starter for most projects:

```gitignore
# Lock files (huge, no signal)
*.lock
package-lock.json

# Build artifacts
target/
dist/
build/
node_modules/

# Planning/review artifacts (can confuse review models)
planning/

# Large data
*.csv
*.sqlite
```

### .dirgrab.toml

For persistent flag defaults (avoids repeating CLI flags):

```toml
[dirgrab]
exclude = ["*.lock", "target/", "planning/"]

[stats]
enabled = true
```

## Gotchas

- **Stats go to stderr**, not stdout. Use `2>&1` if you need to see stats
  alongside output, or `2>&1 | tail -10` to just check stats.
- **`-o` auto-excludes the output file** from the grab to prevent
  self-ingestion. You don't need to manually exclude `dirgrab.txt`.
- **Planning directories confuse external models**. If your repo has old
  reviews or planning docs, exclude them — models may review the *described*
  project instead of the actual code.
- **The installed version matters**. If `dirgrab --version` shows an old
  version, the cargo-installed copy may be shadowing the Homebrew one.
  Check with `which -a dirgrab`.

## Composing with External Tools

```bash
# Standard pattern for reviews (unique temp dir to avoid collisions)
REVIEW_DIR=$(mktemp -d /tmp/review-XXXXXXXX)
dirgrab --no-tree -e '*.lock,planning/' -o "$REVIEW_DIR/context.txt" -s

# Pipe to Gemini CLI
dirgrab -c --no-tree -e '*.lock' && gemini "review this code"

# Check token budget before committing to an expensive model call
dirgrab -s --no-tree -e '*.lock' 2>&1 | tail -5
# If under ~250k tokens: safe for Codex
# If under ~400k tokens: safe for Gemini
# If over: add more exclusions
```

When composing with external tools, **always use `--no-tree`** (saves tokens)
and **always use unique temp paths** (prevents cross-session collisions when
multiple Claude sessions run concurrently).
