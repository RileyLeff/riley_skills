---
name: dirgrab
description: "Create a portable, usually whole-repository or whole-subtree context dump with dirgrab when the user explicitly wants a code snapshot or an external model cannot inspect the workspace directly. Include all files needed to understand the task while excluding low-signal space hogs when appropriate. Do not use for ordinary local exploration, targeted file reading, or every review by default."
---

# dirgrab context dumps

`dirgrab` concatenates a repository or directory into one deterministic text
snapshot for another model or tool. Its purpose is broad context transfer, not
routine local file discovery.

## Use it when

- the user asks for a whole-codebase or portable context dump;
- an external model cannot inspect the workspace directly;
- a frozen snapshot is useful for reproducibility or sharing; or
- understanding the task genuinely requires most of a repository or coherent
  subtree.

Do not invoke it merely because a task involves code. Prefer `rg`, `git
diff`, and direct file reads for local analysis. Do not regenerate an unchanged
snapshot for every follow-up.

## Installation

If `dirgrab` is missing, tell the user and offer:

    brew tap rileyleff/rileytap && brew install dirgrab

or:

    cargo install dirgrab

Source: https://github.com/rileyleff/dirgrab

## Workflow

### 1. Choose the context boundary

Use the whole repository when cross-cutting understanding matters or the user
asked for the full project. Otherwise use the complete relevant subtree. Do not
reduce context to a handful of files if that would hide architecture,
configuration, tests, or call sites needed to understand the task.

`TARGET_PATH` defaults to the current directory:

    dirgrab -l "$TARGET_PATH"

Always preview the file list before producing the content dump.

### 2. Exclude low-signal space hogs

Choose exclusions based on the task rather than applying a universal minimal
set. Common candidates include:

- lock files when dependency resolution is not under review;
- build and cache directories such as `target/`, `dist/`, `build/`, and
  `node_modules/`;
- generated or minified outputs;
- large datasets, databases, archives, media, and extracted artifacts;
- old planning or review artifacts when they could confuse the receiving
  model.

Keep lock files, generated code, fixtures, or planning documents when they are
material to the question. Quote exclusion globs so the shell does not expand
them.

Example:

    dirgrab -l "$TARGET_PATH" -e '*.lock,target/,dist/,build/,node_modules/'

### 3. Capture the snapshot

For LLM consumption, file headers already preserve structure, so
`--no-tree` is normally efficient:

    SNAPSHOT_DIR=$(mktemp -d "${TMPDIR:-/tmp}/dirgrab-XXXXXXXX")
    dirgrab "$TARGET_PATH" --no-tree -e '*.lock,target/,dist/,build/,node_modules/' -o "$SNAPSHOT_DIR/context.txt" -s

`-s` reports approximate tokens and the largest files. There is no fixed token
ceiling: the point of this tool is to move broad context. If the dump is
unwieldy, remove obvious low-signal hogs or split it into coherent subtrees
instead of arbitrarily truncating important source.

### 4. Preserve the right working state

Git mode includes untracked files by default, which is usually correct for
reviewing active work. Use `--tracked-only` only when the user explicitly
wants a clean tracked snapshot. Respect project `.dirgrabignore` and
`.dirgrab.toml` files when present.

## Useful flags

| Flag | Purpose |
| --- | --- |
| `-l, --list` | Preview included files without reading content |
| `-o [FILE]` | Write the snapshot to a file |
| `-s, --stats` | Report size, token estimate, and largest files |
| `-e PATTERN` | Exclude comma-separated gitignore-style patterns |
| `--no-tree` | Omit the redundant directory tree |
| `--no-pdf` | Skip PDF text extraction when documents are irrelevant |
| `--tracked-only` | Exclude untracked working files |
| `--all-repo` | Expand a subtree target to the repository root |

Use `dirgrab --help` for the installed version's complete option set.

## External-model handoff

Tell the receiving model:

- what task it is solving;
- that the snapshot is a point-in-time repository or subtree dump;
- what was intentionally excluded; and
- whether untracked working files are included.

Keep unique output paths for concurrent calls. Do not place snapshots inside
the captured tree unless using `-o`, which automatically excludes its own
output file.
