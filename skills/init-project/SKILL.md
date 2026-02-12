---
name: init-project
description: "Initialize a project for Claude Code: scan the MCP and snippet catalog, ask which ones apply, and write the project's .mcp.json and CLAUDE.md. Use at the start of a new project or when reconfiguring an existing one."
---

# Project Initialization

Set up a project's Claude Code configuration by selecting from the user's
personal catalog of MCP servers and instruction snippets.

## Catalog Location

The catalog lives at `~/.claude/catalog/`:

```
~/.claude/catalog/
  mcps/        # MCP server configs (one JSON file per server)
  snippets/    # CLAUDE.md instruction blocks (one .md file per topic)
```

## Process

### Step 1: Scan the catalog

Read all files in `~/.claude/catalog/mcps/` and `~/.claude/catalog/snippets/`.
For each MCP, read the JSON to understand what it provides. For each snippet,
read the markdown to understand what instructions it contains.

Also check if the catalog README exists (`~/.claude/catalog/README.md`) for
any additional context about the available items.

### Step 2: Inspect the project

Look at what's already in the project to inform your recommendations:

- Check for existing `.mcp.json` — don't overwrite, merge.
- Check for existing `CLAUDE.md` or `.claude/CLAUDE.md` — don't overwrite,
  append new snippets.
- Look at the project's tech stack: `Cargo.toml` (Rust), `pyproject.toml`
  (Python), `package.json` (Node/Svelte), `docker-compose.*` (containers),
  `*.kicad_pro` (KiCad), `.blend` files (Blender), etc.

### Step 3: Recommend and ask

Present the user with:

1. **Auto-detected recommendations** based on the project's tech stack
   (e.g., if you see `svelte.config.js`, recommend the svelte MCP).
2. **The full list** of available catalog items, so they can add anything
   you didn't auto-detect.

Use `AskUserQuestion` with `multiSelect: true` to let the user pick. Group
MCPs and snippets into separate questions.

### Step 4: Write configs

**For MCPs** — merge selected server configs into the project's `.mcp.json`:

```json
{
  "mcpServers": {
    // ... merged from selected catalog entries
  }
}
```

If `.mcp.json` already exists, merge new servers into it without removing
existing ones.

**For snippets** — append selected snippet content to the project's
`CLAUDE.md` (create it if it doesn't exist). Add a blank line between
each snippet block. If the project already has a `CLAUDE.md`, append to
the end — don't duplicate content that's already there.

### Step 5: Confirm

Show the user what was written:
- Which MCP servers were added to `.mcp.json`
- Which snippets were added to `CLAUDE.md`
- Any env vars they need to set (check the catalog README for requirements)

## Catalog Format

The catalog is a personal collection of reusable configs. Nothing in it is
active by default — this skill (or manual setup) copies items into per-project
config files.

### Setting up the catalog

```bash
mkdir -p ~/.claude/catalog/mcps ~/.claude/catalog/snippets
```

Optionally add a `~/.claude/catalog/README.md` documenting what's available
and any env var requirements. This skill reads the README for additional context
when making recommendations.

### MCP entries (`mcps/`)

Each file is a JSON object with one key (the server name) whose value is a
standard MCP server config. The key becomes the server name in the project's
`.mcp.json` under `"mcpServers"`.

**HTTP server** (e.g. `github.json`):
```json
{
  "github": {
    "type": "http",
    "url": "https://api.githubcopilot.com/mcp/",
    "headers": {
      "Authorization": "Bearer ${GITHUB_PERSONAL_ACCESS_TOKEN}"
    }
  }
}
```

**stdio server** (e.g. `slack-notify.json`):
```json
{
  "slack-notify": {
    "command": "uv",
    "args": ["run", "--directory", "/path/to/server", "slack-notify"],
    "env": {
      "SLACK_BOT_TOKEN": "${SLACK_BOT_TOKEN}",
      "SLACK_CHANNEL": "${SLACK_CHANNEL}"
    }
  }
}
```

Environment variables use `${VAR_NAME}` syntax — Claude Code resolves them
at runtime. Document required env vars in the catalog README so the init skill
can remind the user to set them.

### Snippet entries (`snippets/`)

Each file is a markdown document containing instructions to append to a
project's `CLAUDE.md`. One file per topic (e.g. `rust-conventions.md`,
`testing-policy.md`). The file's content is copied verbatim — no templating.

## Notes

- The catalog is a personal reference, not a runtime system. This skill
  reads it and writes standard Claude Code config files.
- If the catalog directory doesn't exist or is empty, tell the user and
  explain where to create it (see "Setting up the catalog" above).
- Don't add MCPs the user didn't select. Auto-detection is for
  *recommendations*, not auto-installation.
- For MCPs with env var requirements (like `SLACK_BOT_TOKEN`), remind
  the user to set them — via `.envrc`, `.zshenv`, or similar.
