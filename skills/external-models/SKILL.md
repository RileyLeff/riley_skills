---
name: external-models
description: "Coordinate fresh agents from the Codex/GPT, Claude, and Gemini model families when the user requests another model, independent opinions, a cross-model review, or a multi-model panel. Represent the current caller's own model family with a fresh built-in subagent, and invoke only the other families through persistent CLI sessions. Discover installed CLI/model capabilities at runtime, preserve agent and session identifiers for follow-ups, and do not use this for ordinary work the current agent can handle directly."
---

# Cross-model collaboration

Coordinate model families without duplicating the current family through an
external CLI. The coordinating agent's own analysis does not count as an
independent lane.

## Routing rule

First identify the current agent's model family. For a standard three-family
round, use this exact mapping:

| Coordinating family | Codex/GPT lane | Claude lane | Gemini lane |
| --- | --- | --- | --- |
| Codex/GPT | Fresh built-in subagent | Persistent Claude CLI session | Persistent Antigravity CLI session |
| Claude | Persistent Codex CLI session | Fresh built-in subagent | Persistent Antigravity CLI session |
| Gemini | Persistent Codex CLI session | Persistent Claude CLI session | Fresh built-in subagent |

A **fresh built-in subagent** means the current environment's native
spawn/delegate mechanism. It is a new agent from the coordinating model family,
not the coordinator itself and not a CLI process.

Never launch an external Codex session from a Codex/GPT coordinator, an external
Claude session from a Claude coordinator, or an external Gemini session from a
Gemini coordinator when a native subagent mechanism is available. Describe
this route as the current-family native subagent.

If native subagents are unavailable, use that family's CLI only as a fallback
and report the degraded routing explicitly.

## Choose the roster

- For a cross-model review, panel, or request for multiple independent agents
  without a specified roster, use one lane from each of the three families.
- For a request naming one provider, invoke only that provider unless the user
  also asks for a comparison or baseline.
- For a custom roster, create exactly the requested lanes.
- Launch independent lanes concurrently when the environment supports it.
- Do not ask a lane to launch the other lanes; the coordinator owns routing.

## Freshness and persistence

- Start every lane fresh for the task.
- Give each lane only the task, relevant constraints, and necessary artifacts.
  Avoid inheriting unrelated conversation history when the native subagent API
  allows control over context inheritance.
- Preserve the native subagent handle or identifier and use the environment's
  follow-up mechanism to continue with that same agent.
- Create persistent external CLI sessions by default. Capture exact session or
  conversation IDs and resume by ID, not by recency.
- Use one lane per family and task. Reuse it for challenges, clarifications,
  fixes, and follow-up review instead of silently replacing it with a new agent.

## Core rules

- Discover installed CLI versions and model capabilities at runtime. Do not
  encode a point-in-time model catalog.
- Omit model-selection flags unless the user requests a model or a verified
  task requirement calls for one.
- Pipe substantial prompts through stdin. Do not pass codebase dumps as shell
  arguments.
- Keep review and consultation lanes read-only. Grant write access only when
  the user explicitly delegates edits.
- Respect current user and project instructions about provider selection.
- Record unavailable or rate-limited lanes instead of substituting an
  unrequested family.

## Discover external surfaces

Check only the CLIs needed for external-family lanes:

    command -v codex && codex --version
    command -v agy && agy --version && agy models
    command -v claude && claude --version

Verify invocation flags with each installed CLI's current `--help` output.
Treat configured defaults and rolling model aliases as dynamic.

## Context strategy

Prefer direct filesystem access when a lane can inspect the workspace. Supply
the working directory, task, constraints, and useful entry points.

Use `dirgrab` only when the user wants a frozen context dump, a lane cannot
inspect the repository directly, or a complete snapshot is materially better
than agentic discovery. Include the whole relevant repository or subtree while
excluding low-signal space hogs when appropriate.

## Current-family native subagent lane

Use the coordinating environment's built-in subagent tool:

1. Spawn one fresh agent from the current model family.
2. Minimize inherited conversation context when supported.
3. Give it the same substantive task and evidence available to external lanes.
4. Keep it independent: do not include other lanes' conclusions in its initial
   prompt.
5. Save its agent handle for follow-up.

Do not treat the coordinator's own answer as the current-family lane.

## External Codex/GPT lane

Use this only when Codex/GPT is not the coordinating family, or when native
subagents are unavailable.

Codex persists sessions unless `--ephemeral` is passed. Start a read-only
session and capture its JSONL events:

    RUN_DIR=$(mktemp -d "${TMPDIR:-/tmp}/external-codex-XXXXXXXX")
    codex -a never exec --sandbox read-only -C "$PWD" --json -o "$RUN_DIR/last-message.txt" - < prompt.txt > "$RUN_DIR/events.jsonl"

Extract the exact identifier from the `thread.started` event:

    SESSION_ID=$(jq -r 'select(.type == "thread.started") | .thread_id' "$RUN_DIR/events.jsonl" | head -n 1)

Resume that conversation:

    codex -a never exec resume --json -o "$RUN_DIR/follow-up.txt" "$SESSION_ID" - < follow-up.txt > "$RUN_DIR/follow-up-events.jsonl"

For delegated edits, change the initial sandbox to `workspace-write`. Never
use `--ephemeral`, `--dangerously-bypass-approvals-and-sandbox`, or
`--full-auto` by default.

## External Gemini lane via Antigravity CLI

Use this only when Gemini is not the coordinating family, or when native
subagents are unavailable.

`agy` persists conversations and resumes them with
`--conversation <id>`:

    agy --print --sandbox --mode plan --print-timeout 10m < prompt.txt

Capture the exact conversation ID or resume command printed by the CLI. Resume
that conversation with:

    agy --conversation "$CONVERSATION_ID" --print --sandbox --mode plan --print-timeout 10m < follow-up.txt

Use `agy --continue` only when no concurrent session can make recency
ambiguous. Use a write-capable mode only when explicitly authorized.

## External Claude lane

Use this only when Claude is not the coordinating family, or when native
subagents are unavailable.

Create an exact session ID up front:

    SESSION_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')
    claude --print --session-id "$SESSION_ID" --permission-mode plan --output-format json < prompt.txt

Resume that conversation:

    claude --print --resume "$SESSION_ID" --permission-mode plan --output-format json < follow-up.txt

Do not pass `--no-session-persistence` unless the user explicitly wants a
disposable session. Use the configured default model unless the user or a
verified capability requirement calls for another.

## Synthesis and handoff

Keep lane outputs independent until every initial result is collected. Then:

1. Attribute findings to their model family.
2. Reconcile agreements and disagreements using evidence.
3. Distinguish the coordinator's synthesis from lane conclusions.
4. Preserve every agent/session identifier for follow-up.

Report for each lane:

- model family and whether it used a native subagent or external CLI;
- CLI version and resolved model when applicable;
- exact agent, session, or conversation identifier;
- exact resume/follow-up mechanism;
- permission mode and working directory;
- substantive result or failure state.

Keep raw logs in unique task-local directories when useful. Do not add session
logs or manifests to a repository unless the user asks.
