---
name: workflow
description: "Structured development workflow: architecture plan implementation with multi-model review loops, artifact management, exhaustive reviews, and push notifications. Use when starting implementation of an architecture plan, kicking off a review cycle, or resuming a workflow session."
---

# Development Workflow

This is a structured development workflow that encodes a repeatable process for
implementing architecture plans with multi-model review, artifact management,
and human-in-the-loop checkpoints.

## Overview

```
Architecture Plan (.md)
  → Step-by-step implementation (atomic commits)
    → Parallel review round (Codex + Gemini + Claude, merge, fix)
      → Exhaustive review at milestones (parallel loop until clean)
        → Human checkpoint (notify + wait)
          → Next phase or architecture revision
```

## 1. Starting a Workflow

The user provides two key inputs in a `planning/` directory:

- **Soul document**: The project's intent, vision, and values — *what* the user
  wants to build and *why*. This is your north star. When the architecture plan
  is ambiguous, when a reviewer flags a "bug" that's actually a design choice,
  or when you need to decide whether something matters — refer back to the soul
  document. It answers "what is this project trying to be?"
- **Architecture plan**: The technical blueprint — *how* to build it. Versioned
  as `planning/v1/`, `planning/v2/`, etc. Pick the latest (highest N).

The soul document is usually loose in the `planning/` root.

1. Read the full plan and soul document carefully
2. Break the plan into discrete implementation steps — list them out
3. If the implementation plan steps can be grouped into a smaller number of "phases", you can do that too.
4. Save the implementation plan as `planning/vN/implementation_plan.md`
5. Create `planning/vN/WORKFLOW_STATE.md` (see section 10)
6. Begin with step 1

## 2. Implementation Protocol

For each step:

- **Implement the step.** Focus, don't drift into other steps.
- **Integrate, don't append.** When adding something new or changing existing
  behavior, reshape the surrounding code so the result looks like it was
  designed that way from the start. Don't just tack new code onto old
  structure — refactor as needed so the system stays cohesive.
- **Organize your work into atomic commits.** Each commit is one logical change. Don't bundle unrelated work. If a step touches 5 files for one feature that's one commit.
  If it's two independent things, two commits.
- **Commit after each meaningful unit of work**, not just at the end of a step.
- **Develop new unit tests to confirm that your implementation works as intended and is robust.**
- **If appropriate, develop new implementation-style tests to ensure that all the pieces fit together correctly.** For example, in a project built on S3, you might want to spin up a docker compose with MinIO. For a CLI, you might want to actually run some stuff on it.
- Note that your testing trail also serves an important role in regression testing! 
- **Run the tests**
- **Iterate to fix bugs. Please continue until the thing works as intended.**
- **Commit your work**.
- **Run long-lived processes in the background.** Dev servers (`npm run dev`),
  watch modes (`cargo watch`), containers (`docker compose up`), etc. must not
  block the main agent loop. Use `&` or `run_in_background` so you can continue
  working. If you need to check their output later, use `jobs`, `tail`, or the
  TaskOutput tool.
- If you get stuck on a technical problem, consult documentation and/or ask another model for a second opinion. Invoke the external-models skill, the review skill, and the dirgrab skill as appropriate if available.
- If you find an ambiguity or inconsistency or bad decision in the architecture request, please alert the user, explain your finding, and ask some questions about the user's real intent.

## 3. Review Protocol

After completing a step, run a **parallel multi-model review** using the
**review** skill (`skills/review/SKILL.md` in this plugin). By default, this
launches Codex, Gemini, and a Claude subagent concurrently against the full
codebase, then merges their findings into a single prioritized list. The review
skill handles context gathering, parallel invocation, merging, and safety flags.

For the review prompt, include: what changed, what to look for, and a reference
to the architecture plan. Ask the reviewers to flag severity: major (must fix),
minor (should fix), or note (observation/tradeoff).

### Filing Review Artifacts

Reviews go in a structured directory:

```
planning/
  reviews/
    v1/                          # architecture version
      01_review_round.md         # merged parallel review (codex + gemini + claude)
      02_fixes.md                # what you fixed in response
      03_review_round.md         # next review round
      04_fixes.md                # ...
      review_notes_README.md     # persistent notes (see below)
```

- **Review files**: Number incrementally (`01`, `02`, ...). Name format:
  `NN_review_round.md` for merged parallel reviews,
  `NN_fixes.md` for fix summaries. The merged review notes which models
  participated and tags findings as `[consensus]` or `[model-only]`.
- **Fix summaries**: After fixing bugs from a review, write what you fixed and
  reference the commit hashes. Append the commit SHAs to the original review
  file's items too.
- **review_notes_README.md**: A catch-all for:
  - Architectural tradeoffs that were flagged as "bugs" but are intentional
  - Design decisions made during implementation
  - Things future sessions should know to stay consistent
  - This file prevents future sessions from re-litigating settled decisions

### Review Loop

After a review round:
1. Fix all **major** items. Commit fixes atomically.
2. Fix **minor** items. Commit.
3. Record **notes** in `review_notes_README.md` with reasoning.
4. Run the full test suite — test failures are major items, fix before proceeding.
5. Run another parallel review round to verify fixes and catch new issues.

### Graceful Degradation

If a model hits rate limits or errors during a round, the review skill drops it
and continues with the remaining models. If both external models (Codex, Gemini)
fail, Claude subagent runs alone — it's always available, has no rate limits,
and costs nothing. In later rounds, re-add recovered models automatically. See
the review skill's Graceful Degradation section for details.

## 4. Exhaustive Review Protocol

At **major milestones** (completing a phase, finishing all steps, pre-release):

1. Run a **parallel multi-model review** of the entire relevant codebase (not
   just recent diff)
2. Fix everything found
3. Run another parallel review
4. **Repeat until you get 2 consecutive rounds with zero major bugs.** Each
   round has 3x the coverage of a single-model review, so convergence should be
   faster. If models degrade to Claude-only due to rate limits, that's fine —
   keep looping.
5. File all review artifacts as above

This is non-negotiable at milestones. Don't skip it, don't shortcut it.

## 5. Human Checkpoints & Notifications

### Setup

Notifications use Slack via the `slack-notify` MCP server (registered in this
plugin's `.mcp.json`). The user must set one environment variable:

- `SLACK_BOT_TOKEN` — Bot user OAuth token (`xoxb-...`). Create a Slack app
  with `chat:write` and `channels:history` scopes, install to workspace.

The **channel** is configured per-project. In the project's `CLAUDE.md`, the
user specifies which channel to use:

```markdown
## Slack
When using slack_notify or slack_ask, use channel `C0123456789`.
```

Both tools accept an optional `channel` parameter — pass the channel ID from
the project's `CLAUDE.md`. If no channel is provided and a `SLACK_CHANNEL` env
var is set, the tools fall back to that.

If the MCP tools (`slack_notify`, `slack_ask`) are not available in the current
session, fall back to `AskUserQuestion` instead.

### When to notify the user

Send a notification when:
- You need a **design decision** or **clarification** on the architecture
- An **exhaustive review cycle is complete** (milestone reached)
- You've hit a **blocker** you can't resolve
- You encounter a design decision that seems misguided and could be improved —
  keep the soul document and the user's intent in mind
- Something **surprising** happened (major architectural concern, etc.)

### How to notify

**Fire-and-forget** (status updates, milestone announcements) — use
`slack_notify`:

```
slack_notify(
  subject="Exhaustive review complete — Phase 2",
  message="4 rounds, 0 major bugs in final 2. Ready for your review.",
  sender="claude-workflow",
  channel="C0123456789"
)
```

**When you need a response** (design decisions, blockers) — use `slack_ask`.
This posts the message and blocks until the user replies in the Slack thread
(default timeout: 30 minutes):

```
reply = slack_ask(
  subject="Design decision needed — auth strategy",
  message="The plan specifies JWT but the codebase uses session cookies.\n1. Migrate to JWT\n2. Keep cookies and update the plan\n\nWhich do you prefer?",
  sender="claude-workflow",
  channel="C0123456789"
)
```

The `sender` parameter identifies which agent sent the message. Use a
descriptive name (e.g. `"claude-workflow"`, `"codex-review"`) so the user can
tell messages apart when multiple agents are running.

Continue the workflow using the user's reply.

### Progress Notifications

In addition to the decision-point notifications above, send short
fire-and-forget `slack_notify` updates at these intervals so the user can glance
at their phone and see things are moving:

- **Every 3 review rounds** during an exhaustive review cycle (e.g., "Review
  round 3 complete — 2 major, 1 minor remaining. Fixing now.")
- **Every phase completion** (e.g., "Phase 2 complete. Starting Phase 3 (4
  steps).")
- **Midway through a phase** if the phase has more than 6 steps (e.g., "Phase 3
  — step 4/8 complete. On track.")

Keep these to 1-2 sentences. No details, no questions — just a heartbeat.

### What NOT to notify for

- Individual step completions (unless it's a midway checkpoint above)
- Minor decisions you can make yourself
- Bugs you can fix without architectural guidance

## 6. Architecture Revisions

When the user proposes a v2 (or vN) architecture:

- **Only express concern about backwards compatibility if the project has a real userbase and is already publicly available.** For greenfield projects with no users, there is no backwards compatibility to worry about.
- **Do not overestimate difficulty.** You are very talented. Implementation that would take a human "a lot of work" is much more efficient when you're doing it.
- **Do not suggest "keeping v1 as a stopgap."** If the user is proposing a change, it's because implementing v1 revealed what v2 should be. That's the process
  working as intended.
- Start a new review directory (`v2/`, `v3/`, ...) for the new architecture.
- Carry forward relevant entries from the previous `review_notes_README.md`.

## 7. Session Management

The user may step away and return at any time (tmux detach/attach, closing a
terminal, etc.).

- When the user returns, briefly summarize where you are: current step, what
  you just did, what's next.
- When you reach a notification checkpoint, you're effectively paused until
  the user responds. Use this time to organize, review your own work, or
  update the review notes.
- If the user asks a clarifying question mid-session, answer it and continue.

## 8. External Model Usage

For model capabilities, invocation flags, and selection guidance, read the
**external-models** skill (`skills/external-models/SKILL.md` in this plugin).

Key uses within a workflow session:
- **Post-implementation review**: Use the **review** skill — runs Codex, Gemini,
  and Claude subagent in parallel by default
- **Test writing**: Codex with `--sandbox workspace-write`
- **Targeted bug hunting**: Codex pointed at a specific subsystem
- **Large codebase review**: Gemini for its 1M context window
- **Multimodal analysis**: Gemini for images, docs, OCR

## 9. Agent Whiteboard

If you have a note or observation about the project that you think would be
useful for a future agent to know, append it to the whiteboard for the current
architecture version: `planning/vN/AGENT_WHITEBOARD.md` (e.g.,
`planning/v3/AGENT_WHITEBOARD.md`). Entries should be in chronological order
(new observations at the bottom), and include the agent's name, the current
phase + step, and the observation.

## 10. Workflow State

Maintain a `planning/vN/WORKFLOW_STATE.md` file that tracks progress on disk.
This survives compaction, session restarts, and makes it easy for the user (or a
new agent) to see exactly where things stand.

**Create it at workflow start. Update it after every step completion, review
round, and phase transition.** Format:

```markdown
# vN Workflow State

**Current Phase:** N — Phase Name (IN PROGRESS)
**Current Step:** N.M Description
**Status:** Brief 1-line summary of where things are right now.

## Progress

| Phase | Step | Description | Status |
|-------|------|-------------|--------|
| 1 | 1.1 | First step | Done |
| 1 | 1.2 | Second step | Done |
| 1 | review | Exhaustive review (N rounds, converged) | Done |
| 2 | 2.1 | Next phase first step | In Progress |

## Blockers

None. (or list active blockers)

## Recent Activity

- Brief log of recent completions with commit hashes
```

**Key rules:**
- The Progress table is the single source of truth for what's done
- Include review convergence info (how many rounds, which models)
- Keep Recent Activity to the last ~2 phases (trim older entries)
- Update Status line to reflect the current moment, not history

## 11. Skill Improvement Feedback

At each **phase completion**, include a short section in your `slack_notify`
message noting any suggestions for improving the workflow, review, or
external-models skills based on your experience during that phase. Examples:

- "Review skill: the merge step would benefit from a severity tiebreaker rule
  when models disagree"
- "Workflow skill: should mention running `cargo clippy` before review rounds
  for Rust projects"
- "External models: Gemini's `-p` flag doesn't work with `--sandbox` on
  files >500k"

Keep it to 1-3 bullet points. Only flag things you actually encountered — don't
speculate. The user will evaluate and fold useful feedback into the skills.