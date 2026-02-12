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

- **review** and **dirgrab** need [dirgrab](https://github.com/rileyleff/dirgrab) installed (`brew tap rileyleff/rileytap && brew install dirgrab` or `cargo install dirgrab`)
- **review** needs [Codex CLI](https://github.com/openai/codex) and/or [Gemini CLI](https://github.com/google-gemini/gemini-cli) installed
- **slack-notify** needs [uv](https://docs.astral.sh/uv/) installed and a `SLACK_BOT_TOKEN` env var set (see the [workflow skill](skills/workflow/SKILL.md#5-human-checkpoints--notifications) for setup details)

## Contents

### MCP

#### slack-notify

Simple MCP server that lets your agent ping you on Slack. Two tools: `slack_notify` for fire-and-forget status updates, and `slack_ask` for when the agent actually needs your input — it posts a message, waits for your threaded reply, and continues. Handy for long-running workflows where you don't want to babysit a terminal.

Both tools accept an optional `channel` parameter. If not provided, they fall back to the `SLACK_CHANNEL` env var. This lets you configure channels per-project in your `CLAUDE.md` (e.g. "When using slack tools, use channel `C0123456789`") without touching env vars.

### Skills

#### workflow

Encodes my full development process for larger projects: read an architecture plan, break it into steps, implement with atomic commits, run multi-model review loops, fix bugs until clean, and notify the human at checkpoints. Designed for hands-off autonomous work, you give it a plan (specific architectural ideas) and a "soul document" (describing your overall intent), it does the rest. Getting frequent external reviews, clearing out old stuff, and pausing at major checkpoints for extensive bugfixes generally enables projects to scale a little larger if they have solid foundations. Once it's in, try the project yourself, add a new architecture file if necessary, and repeat. Will keep refining this over time.

#### review

Runs a code review using an external model (Codex or Gemini). Gathers codebase context with dirgrab, ships it off in a read-only sandbox, and brings back structured results. Supports follow-up sessions so the reviewer keeps its context. Built to avoid multi-agent collisions, let me know if you run into any issues with it.

#### external-models

Ever have your agent refuse to believe that Codex 5.N exists and insist on using GPT-4o? This is a quick reference on the latest models: what they're good at, how to invoke them, and when to pick one over another. Keeps your agent from hallucinating CLI flags.

This one is the most likely to get out of sync with specific CLI harness usage given the rate that they change, will try to keep it updated. Might need to set up some kind of recurring autonomous review + update cycle if it breaks often.

#### dirgrab

Skill for my Rust tool [dirgrab](https://github.com/rileyleff/dirgrab) that concatenates a whole directory into one big text chunk. Convenient for code review, agent invocation, or any time you need to hand an LLM your entire codebase in one shot.

#### init-project

I keep my MCPs and instruction snippets in a catalog at `~/.claude/catalog/`. This skill scans the catalog, looks at your project's tech stack, and recommends what to set up. Writes the project's `.mcp.json` and `CLAUDE.md` for you so you don't have to copy-paste configs between projects.