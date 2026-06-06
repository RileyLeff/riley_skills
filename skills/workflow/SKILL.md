---
name: workflow
description: "Harness-neutral structured development workflow: architecture/spec implementation with parallel subagents, multi-model review loops, artifact management, exhaustive review gates, blocked-state user escalation, and optional notifications. Use when starting implementation of an architecture plan, kicking off a review cycle, or resuming a workflow session."
---

# Development Workflow

This is a structured development workflow that encodes a repeatable process for
implementing architecture plans with multi-model review, artifact management,
and human-in-the-loop checkpoints.

## Overview

```
Architecture Plan (.md)
  → Step-by-step implementation (atomic commits)
    → Parallel review round (Codex/GPT + Claude + Gemini, one reviewer per family, merge, fix)
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
2. Read or create `planning/workflow.toml` (see section 2)
3. Break the plan into discrete implementation steps — list them out
4. If the implementation plan steps can be grouped into a smaller number of "phases", you can do that too.
5. Save the implementation plan as `planning/vN/implementation_plan.md`
6. Create `planning/vN/WORKFLOW_STATE.md` (see section 11)
7. Begin with step 1

## 2. Workflow Config

Use `planning/workflow.toml` for durable machine-readable policy. Keep
`WORKFLOW_STATE.md` for human-readable progress and narrative status.

If `planning/workflow.toml` does not exist, create a minimal one when the
project intent is clear. If the compatibility or communication policy is not
clear, ask the user before starting implementation.

Recommended shape:

```toml
project_name = "my-project"
architecture_version = "v1"

# true  = preserve compatibility; reviewers flag breaking changes/migration gaps
# false = greenfield/no users; reviewers flag legacy baggage and transitional shims
# unset = unknown; ask before making compatibility-sensitive decisions
backwards_compatibility_matters = false
compatibility_notes = "Greenfield project with no users or production data."

use_github = false

[comms]
venue = "slack" # slack | current_thread | github | none
metadata = { slack_channel_id = "C0123456789" }

[review]
required_clean_rounds = 2
allow_degraded_rounds = true
target_reviewers = ["codex", "claude", "gemini"]
```

Compatibility policy:

- If `backwards_compatibility_matters = false`, do not carry pre-production
  compatibility baggage. Prefer the clean production design we would choose if
  we had known the current spec and implementation lessons from the start.
- If `backwards_compatibility_matters = true`, preserve public/user-facing
  compatibility. Reviewers should flag breaking changes, migration gaps, data
  loss, API drift, and upgrade hazards.
- If the field is absent, treat compatibility as **unknown**. Do not delete or
  break compatibility-sensitive behavior until the user clarifies.

Communication policy:

- Prefer `comms.venue` and `comms.metadata` from `planning/workflow.toml`.
- If absent, fall back to project-local instructions such as `CLAUDE.md`,
  `AGENTS.md`, `.codex`, or the current conversation.
- If `use_github = true`, use GitHub branches/PRs/comments/checks where the
  current harness has access. Otherwise keep artifacts local.

## 3. Implementation Protocol

For each step:

- **Implement the step.** Focus, don't drift into other steps.
- **Integrate, don't append.** When adding something new or changing existing
  behavior, reshape the surrounding code so the result looks like it was
  designed that way from the start. Don't just tack new code onto old
  structure — refactor as needed so the system stays cohesive.
- **Apply the configured compatibility policy.** When
  `backwards_compatibility_matters = false`, carry no legacy baggage: before
  accepting code, ask whether the result is what you would build if you had
  known everything learned during implementation from the start. When
  `backwards_compatibility_matters = true`, preserve compatibility and add
  migration/upgrade paths as needed. When unset, ask before making
  compatibility-sensitive changes.
- **Parallelize deliberately.** At the start of substantial work, identify
  independent side tasks that can run in parallel: codebase exploration,
  focused implementation with disjoint write sets, fixture/test generation,
  spec cross-checks, and external review. Fresh subagents in the current harness
  may fill the orchestrator's model-family review slot when they start from a
  fresh context and did not implement the change under review.
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
  working. If you need to check their output later, use the harness's background
  task output tool, `jobs`, `tail`, or the relevant process log.
- If you get stuck on a technical problem, consult documentation and/or ask another model for a second opinion. Invoke the external-models skill, the review skill, and the dirgrab skill as appropriate if available.
- If you find an ambiguity, inconsistency, or spec/plan mismatch that cannot be
  resolved from the project's clear intent, mark the workflow state **Blocked**,
  write the blocker into `WORKFLOW_STATE.md`, and contact the user using
  `planning/workflow.toml` comms settings when available. Prefer the configured
  Slack channel when `comms.venue = "slack"`; otherwise use the current session
  or configured GitHub venue.

## 4. Review Protocol

After completing a step, run a **parallel multi-model review** using the
**review** skill (`skills/review/SKILL.md` in this plugin). By default, this
launches available external reviewers concurrently, then merges their findings
into a single prioritized list. The target panel is exactly one fresh reviewer
from each of the Codex/GPT, Claude, and Gemini families when available. If the
orchestrator can spawn a fresh subagent from its own family, that subagent fills
that family slot; do not also launch a separate external CLI reviewer from the
same family unless the user explicitly asks for redundancy. The review skill
handles context gathering, parallel invocation, merging, degradation, and safety
flags.

For the review prompt, include: what changed, what to look for, and a reference
to the architecture plan and `planning/workflow.toml`. For implementation-slice
reviews, also include the full public spec, the full implementation plan, the
full relevant codebase snapshot, and a short prompt explaining what this section
was supposed to accomplish. Ask the reviewers to flag severity: P0/P1/P2 or
major (must fix), minor (should fix), or note (observation/tradeoff).

Every implementation-slice and milestone review must explicitly ask whether the
work is materially implemented versus merely scaffolded, mocked, fixture-driven,
or shaped to satisfy superficial tests. A review is not clean if reviewers lacked
the spec, implementation plan, code, or task intent needed to judge that.

Pass the compatibility policy into every review prompt:

- `false`: ask reviewers to reject legacy compatibility/pre-production baggage
  and judge whether the implementation is the best clean production shape given
  what is now known.
- `true`: ask reviewers to protect compatibility and flag migration/API/data
  upgrade hazards.
- unset: ask reviewers to flag compatibility-sensitive choices as questions,
  not as automatic failures.

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
  participated, whether the round was degraded, the active compatibility policy,
  and tags findings as `[consensus]` or `[model-only]`.
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
1. Fix all P0/P1/P2 or **major** items. Commit fixes atomically.
2. Fix **minor** items when they are real quality issues. Commit.
3. Record intentional tradeoffs and non-actionable **notes** in
   `review_notes_README.md` with reasoning.
4. Run the full required test/validation suite — failures are major items.
5. Run another parallel review round to verify fixes and catch new issues.
6. If a reviewer surfaces a genuine spec/plan inconsistency that cannot be
   resolved from project intent, mark the workflow **Blocked** and contact the
   user instead of guessing.

### Graceful Degradation

If a model hits rate limits or errors during a round, the review skill drops it
and continues with the remaining reviewers. A degraded round with one or two
successful external reviewers is valid, but must be labeled degraded and still
counts toward the same two-clean-round gate only if it is actually clean. In
later rounds, re-add recovered models automatically. See the review skill's
Graceful Degradation section for details.

## 5. Exhaustive Review Protocol

At **major milestones** (completing a phase, finishing all steps, pre-release):

1. Run a **parallel multi-model review** of the full relevant codebase against
   the full public spec, implementation plan, workflow policy, and a prompt that
   states what the milestone was supposed to deliver.
2. Fix everything found
3. Run another parallel review
4. **Repeat until you get 2 consecutive clean valid rounds.** Clean means no
   P0/P1/P2 or major findings, no required test failures, no unresolved
   spec/plan contradictions, no unresolved security/privacy/data-boundary
   issues, no mock-only/scaffold-only/reward-hacked implementation gaps, and no
   reviewer saying there was insufficient context for the requested judgment.
5. If a round is degraded because a reviewer hit rate limits or failed, it may
   still count if at least one external reviewer succeeded and the result is
   clean. Label it degraded, keep trying to restore the full panel, and do not
   weaken the requirement for two consecutive clean rounds.
6. File all review artifacts as above

This is non-negotiable at milestones. Don't skip it, don't shortcut it.

## 6. Human Checkpoints & Notifications

### Setup

Notifications use Slack via the `slack-notify` MCP server (registered in this
plugin's `.mcp.json`). The user must set one environment variable:

- `SLACK_BOT_TOKEN` — Bot user OAuth token (`xoxb-...`). Create a Slack app
  with `chat:write` and `channels:history` scopes, install to workspace.

The **channel** is configured per-project. In the project's `CLAUDE.md`, the
`AGENTS.md`, `.codex` project instructions, or equivalent project-local agent
instructions, the user specifies which channel to use:

```markdown
## Slack
When using slack_notify or slack_ask, use channel `C0123456789`.
```

Both tools accept an optional `channel` parameter — pass the channel ID from
`planning/workflow.toml` when configured. If no channel is provided and a
`SLACK_CHANNEL` env var is set, the tools fall back to that.

If the MCP tools (`slack_notify`, `slack_ask`) are not available in the current
session, fall back to the current harness's user-question mechanism instead.

### When to notify the user

Send a notification when:
- You need a **design decision** or **clarification** on the architecture
- An **exhaustive review cycle is complete** (milestone reached)
- You've hit a **blocker** you can't resolve
- A spec, implementation plan, tests, or code reality conflict cannot be
  resolved from project intent
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

## 7. Architecture Revisions

When the user proposes a v2 (or vN) architecture:

- **Follow `backwards_compatibility_matters`.** If it is `true`, protect
  compatibility and require migration/upgrade plans. If it is `false`, do not
  preserve earlier failed approaches for compatibility. If it is unset, ask.
- **Use what implementation taught you.** When compatibility does not matter,
  revised architecture should describe the best clean production shape from
  today's understanding.
- **Do not overestimate difficulty.** You are very talented. Implementation that would take a human "a lot of work" is much more efficient when you're doing it.
- **Do not suggest "keeping v1 as a stopgap."** If the user is proposing a change, it's because implementing v1 revealed what v2 should be. That's the process
  working as intended.
- Start a new review directory (`v2/`, `v3/`, ...) for the new architecture.
- Carry forward relevant entries from the previous `review_notes_README.md`.

## 8. Session Management

The user may step away and return at any time (tmux detach/attach, closing a
terminal, etc.).

- When the user returns, briefly summarize where you are: current step, what
  you just did, what's next.
- When you reach a notification checkpoint, you're effectively paused until
  the user responds. Use this time to organize, review your own work, or
  update the review notes.
- If the user asks a clarifying question mid-session, answer it and continue.

## 9. External Model Usage

For model capabilities, invocation flags, and selection guidance, read the
**external-models** skill (`skills/external-models/SKILL.md` in this plugin).

Key uses within a workflow session:
- **Post-implementation review**: Use the **review** skill — runs a fresh
  Codex/GPT, Claude, and Gemini reviewer in parallel when available, with at
  most one reviewer per model family
- **Test writing**: Codex with `--sandbox workspace-write`
- **Targeted bug hunting**: Codex pointed at a specific subsystem
- **Large codebase review**: Gemini for its 1M context window
- **Multimodal analysis**: Gemini for images, docs, OCR

## 10. Agent Whiteboard

If you have a note or observation about the project that you think would be
useful for a future agent to know, append it to the whiteboard for the current
architecture version: `planning/vN/AGENT_WHITEBOARD.md` (e.g.,
`planning/v3/AGENT_WHITEBOARD.md`). Entries should be in chronological order
(new observations at the bottom), and include the agent's name, the current
phase + step, and the observation.

## 11. Workflow State

Maintain a `planning/vN/WORKFLOW_STATE.md` file that tracks progress on disk.
This survives compaction, session restarts, and makes it easy for the user (or a
new agent) to see exactly where things stand.

Do not use `WORKFLOW_STATE.md` for durable policy knobs. Put compatibility,
communication, GitHub, and review-gate settings in `planning/workflow.toml` and
summarize the active values in `WORKFLOW_STATE.md` only for readability.

**Create it at workflow start. Update it after every step completion, review
round, and phase transition.** Format:

```markdown
# vN Workflow State

**Current Phase:** N — Phase Name (IN PROGRESS)
**Current Step:** N.M Description
**Status:** Brief 1-line summary of where things are right now.
**Workflow Config:** planning/workflow.toml loaded; compatibility=false; comms=slack

## Progress

| Phase | Step | Description | Status |
|-------|------|-------------|--------|
| 1 | 1.1 | First step | Done |
| 1 | 1.2 | Second step | Done |
| 1 | review | Exhaustive review (N rounds, converged) | Done |
| 2 | 2.1 | Next phase first step | In Progress |

## Blockers

None. (or list active blockers, the attempted resolutions, and how the user was
contacted)

## Recent Activity

- Brief log of recent completions with commit hashes
```

**Key rules:**
- The Progress table is the single source of truth for what's done
- Include review convergence info (how many rounds, which models)
- If blocked, set `Status` to `Blocked`, describe exactly what decision or
  inconsistency blocks progress, and do not mark the step done
- Keep Recent Activity to the last ~2 phases (trim older entries)
- Update Status line to reflect the current moment, not history

## 12. Skill Improvement Feedback

At each **phase completion**, if you ran into friction, unexpected behavior, or
missing guidance in the workflow, review, or external-models skills, you may
include a short feedback section in your `slack_notify` message. This is
optional — only include it if you actually have something to report. Examples:

- "Review skill: the merge step would benefit from a severity tiebreaker rule
  when models disagree"
- "Workflow skill: should mention running `cargo clippy` before review rounds
  for Rust projects"
- "External models: `agy` positional prompts routed to the wrong model during
  smoke testing; stdin should stay mandatory"

Keep it to 1-3 bullet points. Only flag things you actually encountered — don't
speculate or pad. If everything worked smoothly, skip this section entirely.
The user will evaluate and fold useful feedback into the skills.
