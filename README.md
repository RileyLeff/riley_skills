# riley_skills

My little set of Claude Code tools. Will push new ones and updates over time. If you find something broken or have an improvement to suggest, please let me know!

## Install

```bash
claude plugin marketplace add rileyleff/riley_skills
claude plugin install riley-skills
```

Or from inside Claude Code:
```
/plugin marketplace add rileyleff/riley_skills
/plugin install riley-skills
```

## Update

```bash
claude plugin marketplace update riley-skills
claude plugin update riley-skills@riley-skills
```

Some skills depend on external tools:

- **dirgrab** needs [dirgrab](https://github.com/rileyleff/dirgrab) installed (`brew tap rileyleff/rileytap && brew install dirgrab` or `cargo install dirgrab`)
- **external-models** uses whichever supported CLIs are installed: Codex CLI, Antigravity CLI (`agy`), and Claude Code

## Contents

### Skills

#### external-models

Coordinates fresh Codex/GPT, Claude, and Gemini agents for independent opinions
and cross-model analysis. The caller's own family is represented by a fresh
built-in subagent; only the other families use persistent CLI sessions. It
discovers CLI/model capabilities at runtime and preserves every agent/session
identifier for follow-up.

#### dirgrab

Skill for my Rust tool [dirgrab](https://github.com/rileyleff/dirgrab) that
concatenates a whole directory into one big text chunk. It is deliberately
reserved for portable repository/subtree context dumps rather than ordinary
local code exploration.

#### init-project

I keep my MCPs and instruction snippets in a catalog at `~/.claude/catalog/`. This skill scans the catalog, looks at your project's tech stack, and recommends what to set up. Writes the project's `.mcp.json` and `CLAUDE.md` for you so you don't have to copy-paste configs between projects.
