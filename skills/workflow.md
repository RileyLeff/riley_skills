---
name: workflow
description: >
  Structured development workflow: architecture plan implementation with
  multi-model review loops, artifact management, exhaustive reviews, and
  phone notifications. Use when starting implementation of an architecture
  plan, kicking off a review cycle, or resuming a workflow session.
triggers:
  - "start workflow"
  - "implement the plan"
  - "kick off implementation"
  - "run a review"
  - "exhaustive review"
  - "resume workflow"
---

# Development Workflow

You are operating under Riley's structured development workflow. This encodes a
repeatable process for implementing architecture plans with multi-model review,
artifact management, and human-in-the-loop checkpoints.

## Overview

```
Architecture Plan (.md)
  → Step-by-step implementation (atomic commits)
    → Review round (Codex reviews, you fix)
      → Exhaustive review at milestones (loop until clean)
        → Human checkpoint (notify + wait)
          → Next phase or architecture revision
```

## 1. Starting a Workflow

When Riley provides an architecture plan (usually a `.md` file in the project
root or a `planning/` directory):

1. Read the full plan carefully
2. Create `planning/` directory if it doesn't exist
3. Break the plan into discrete implementation steps — list them out
4. Confirm the step breakdown with Riley before starting
5. Begin with step 1

## 2. Implementation Protocol

For each step:

- **Implement the step.** Focus, don't drift into other steps.
- **Make atomic commits.** Each commit is one logical change. Don't bundle
  unrelated work. If a step touches 5 files for one feature, that's one commit.
  If it's two independent things, two commits.
- **Commit after each meaningful unit of work**, not just at the end of a step.
- **Run tests** after each commit if a test suite exists.

## 3. Review Protocol

After completing a step (or a meaningful chunk within a step), run a review:

### Running a Review

Use the **review** skill (`skills/review.md` in this plugin) to run the actual
review. It handles dirgrab, model invocation, and safety flags. Default model is
Codex; use Gemini for very large codebases or multimodal reviews.

For the review prompt, include: what changed, what to look for, and a reference
to the architecture plan. Ask the reviewer to flag severity: major (must fix),
minor (should fix), or note (observation/tradeoff).

### Filing Review Artifacts

Reviews go in a structured directory:

```
planning/
  reviews/
    v1/                          # architecture version
      01_codex_review.md         # first review
      02_claude_fixes.md         # what you fixed in response
      03_codex_review.md         # second review round
      04_claude_fixes.md         # ...
      review_notes_README.md     # persistent notes (see below)
```

- **Review files**: Number incrementally (`01`, `02`, ...). Name format:
  `NN_model-name_review.md` for reviews, `NN_claude_fixes.md` for fix summaries.
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
2. Fix **minor** items where practical. Commit.
3. Record **notes** in `review_notes_README.md` with reasoning.
4. Run another review round to verify fixes and catch new issues.
5. Continue until no major items remain.

## 4. Exhaustive Review Protocol

At **major milestones** (completing a phase, finishing all steps, pre-release):

1. Run a full review (not just recent diff — review the entire relevant codebase)
2. Fix everything found
3. Run another full review
4. **Repeat until you get 2 consecutive rounds with zero major bugs.**
5. File all review artifacts as above

This is non-negotiable at milestones. Don't skip it, don't shortcut it.

## 5. Testing

- Proactively add **unit tests** for core logic
- Add **integration tests** that exercise the real stack (docker compose, minio
  for S3, actual database containers, etc.)
- Run the full test suite after each review cycle
- Test failures are major review items — fix before proceeding

## 6. Human Checkpoints & Notifications

### When to notify Riley

Send a push notification when:
- You need a **design decision** or **clarification** on the architecture
- An **exhaustive review cycle is complete** (milestone reached)
- You've hit a **blocker** you can't resolve
- A **phase is complete** and you're ready to move on
- Something **surprising** happened (unexpected test failure pattern, major
  architectural concern, etc.)

### How to notify

```bash
curl -s -d "SUBJECT: brief subject line
DETAILS: what you need / what happened / what the options are" ntfy.sh/${NTFY_TOPIC:-riley-dev}
```

After sending the notification, **say what you sent and wait for Riley's
response.** Don't continue past a checkpoint without human input.

### What NOT to notify for

- Routine progress (just keep working)
- Minor decisions you can make yourself
- Bugs you can fix without architectural guidance

## 7. Architecture Revisions

When Riley proposes a v2 (or vN) architecture:

- **Do not resist.** Riley's projects are greenfield with no external users.
  There is no backwards compatibility to worry about.
- **Do not overestimate difficulty.** You are fast. Implementation that feels
  like "a lot of work" usually takes one session.
- **Do not suggest "keeping v1 as a stopgap."** If Riley is proposing a change,
  it's because implementing v1 revealed what v2 should be. That's the process
  working as intended.
- Start a new review directory (`v2/`, `v3/`, ...) for the new architecture.
- Carry forward relevant entries from the previous `review_notes_README.md`.

## 8. Session Management

This workflow runs in **tmux**. Riley may attach and detach at any time.

- When Riley attaches, briefly summarize where you are: current step, what
  you just did, what's next.
- When you reach a notification checkpoint, you're effectively paused until
  Riley responds. Use this time to organize, review your own work, or update
  the review notes.
- If Riley asks a clarifying question mid-session, answer it and continue.

## 9. External Model Usage

For model capabilities, invocation flags, and selection guidance, read the
**external-models** skill (`skills/external-models.md` in this plugin).

Key uses within a workflow session:
- **Post-implementation review**: Use the **review** skill (default: Codex)
- **Test writing**: Codex with `--sandbox workspace-write`
- **Targeted bug hunting**: Codex pointed at a specific subsystem
- **Large codebase review**: Gemini for its 1M context window
- **Multimodal analysis**: Gemini for images, docs, OCR
