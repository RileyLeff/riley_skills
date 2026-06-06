---
name: review
description: "Run a harness-neutral review using parallel fresh reviewers from the Codex/GPT, Claude/Claude Code, and Gemini model families. Use for code, specs, implementation plans, architecture boundaries, or workflow gates. Gathers context with dirgrab, launches reviewers concurrently, merges findings, files artifacts, and supports degraded-but-valid review rounds."
---

# Code Review

**Before proceeding, read these skills** from this plugin's `skills/` directory:
- `skills/external-models/SKILL.md` — model capabilities and invocation details
- `skills/dirgrab/SKILL.md` — how to gather codebase context

If you can't find them at a relative path, check
`~/.claude/plugins/cache/*/riley-skills/skills/` or the `riley-skills` plugin
directory.

## User's Request

$ARGUMENTS

## Step 0: Choose Mode And Panel

**Parallel mode** (default): Run multiple external reviewers concurrently, then
merge findings. Use this when:
- The user says "review" without specifying a model
- This review is invoked from the **workflow** skill
- The user explicitly asks for "parallel review"

The default target panel is exactly one fresh reviewer from each model family:

- Codex/GPT
- Claude/Claude Code
- Gemini

The orchestrating implementer never counts as a reviewer. A fresh subagent in
the current harness is a transport choice for filling that harness's
model-family slot, not a fourth reviewer. Never run both a same-family subagent
and an external CLI reviewer for that same family unless the user explicitly
asks for redundancy.

Examples:

- If Codex is orchestrating: fill the Codex/GPT slot with a fresh Codex subagent
  or Codex CLI reviewer, then add Claude Opus via Claude CLI and Gemini via
  `agy`.
- If Claude is orchestrating: fill the Claude slot with a fresh Claude subagent
  or Claude CLI reviewer, then add Codex CLI and Gemini via `agy`.
- If only CLI tools are available: use Codex CLI, Claude CLI, and `agy`.

Launch independent reviewers in parallel before waiting on any single one.

**Single-model mode**: Run one model only. Use this when:
- The user specifies a model ("codex review", "gemini review", "claude review")
- Only one model is available (others rate-limited or not installed)

Review types:
- **code**: bugs, regressions, security, tests, production readiness
- **spec-plan**: contradictions, missing contracts, private leakage, feasibility
- **implementation-slice**: code vs spec/plan alignment, tests, no drift,
  no reward hacking, no mock-only implementation hidden behind passing tests
- **workflow**: process hazards, artifact quality, review-gate integrity

## Step 0.5: Load Workflow Policy

If `planning/workflow.toml` exists, read it before building the prompt. Include
these fields in the review prompt and artifact header:

- `backwards_compatibility_matters`
- `compatibility_notes`
- `use_github`
- `comms.venue` and `comms.metadata` when relevant
- `review.required_clean_rounds`, `review.allow_degraded_rounds`, and
  `review.target_reviewers`

Compatibility policy:

- If `backwards_compatibility_matters = false`, reviewers should flag legacy
  compatibility carryover, transitional shims, obsolete interfaces, and
  pre-production baggage.
- If `backwards_compatibility_matters = true`, reviewers should flag breaking
  changes, migration gaps, API/data compatibility hazards, and upgrade risks.
- If the field is absent, compatibility is unknown. Do not ask reviewers to
  enforce no-legacy mode; ask them to identify compatibility-sensitive choices
  that need a user decision.

## Step 1: Create Temp Directory

Create a unique temp directory for this review session to avoid collisions with
other concurrent agent sessions:

```bash
REVIEW_DIR=$(mktemp -d /tmp/review-XXXXXXXX)
echo "Review temp dir: $REVIEW_DIR"
```

Use `$REVIEW_DIR` for all files in this review. **Never use hardcoded paths
like `/tmp/review-context.txt`** — multiple sessions will collide.

## Step 2: Gather Context

Run `dirgrab -s --no-tree` to show per-file token breakdowns. If a
`.dirgrabignore` exists, it's used automatically.

```bash
dirgrab -s --no-tree 2>&1 | tail -15
```

**Token budget check:**
- Under ~250k tokens: all three models can participate
- 250k–500k tokens: drop Codex (its 258k context is too tight), run Gemini +
  Claude only
- Over ~500k tokens: ask the user what to exclude via `-e` flags

## Step 3: Capture Codebase

Write dirgrab output to a temp file. Always use `--no-tree` (the tree wastes
tokens).

```bash
dirgrab --no-tree -o "$REVIEW_DIR/context.txt" -s 2>&1
```

## Step 4: Build Prompt

Create a prompt file wrapping the codebase. **Never pass codebase content as a
shell argument** — always build a file and pipe it.

```bash
cat > "$REVIEW_DIR/prompt.txt" << 'PROMPT_HEADER'
You are reviewing this codebase in READ-ONLY mode. Do NOT edit, write, or
modify any files. Only analyze and report.

Here is the full codebase:

<codebase>
PROMPT_HEADER

cat "$REVIEW_DIR/context.txt" >> "$REVIEW_DIR/prompt.txt"

cat >> "$REVIEW_DIR/prompt.txt" << 'PROMPT_FOOTER'
</codebase>

[REVIEW_INSTRUCTION]
PROMPT_FOOTER
```

Replace `[REVIEW_INSTRUCTION]` with the user's request, or use the default:
"Review this codebase for architecture quality, potential bugs, security issues,
spec/plan drift, test gaps, and areas for improvement. Flag severity: P0/P1/P2
or major (must fix), minor (should fix), or note (observation/tradeoff). Provide
specific file and function references."

Apply the compatibility policy from `planning/workflow.toml`:

- If `backwards_compatibility_matters = false`, add: "Do not preserve legacy
  compatibility or pre-production baggage. Flag any code that keeps
  compatibility with old experiments, obsolete assumptions, abandoned
  interfaces, or transitional paths that would not exist if we had known the
  current spec/plan from the start."
- If `backwards_compatibility_matters = true`, add: "Preserve compatibility for
  real users/data/APIs. Flag breaking changes, missing migrations, data-loss
  risks, undocumented API changes, and upgrade hazards."
- If unset, add: "Compatibility policy is unknown. Flag compatibility-sensitive
  decisions as questions/blockers rather than assuming old behavior can be
  removed or must be preserved."

For spec/plan reviews, include the relevant spec, implementation plan, private
boundary notes if allowed, and the exact acceptance criteria. Ask reviewers to
say explicitly whether they had enough context to assess the request.

For implementation-slice and milestone reviews, the prompt must include all of:

- the full public spec or the largest relevant unredacted excerpt if the
  codebase exceeds model context
- the full implementation plan or the largest relevant unredacted excerpt if
  the codebase exceeds model context
- the full relevant codebase snapshot, not just the diff
- the workflow policy from `planning/workflow.toml`
- a short task prompt explaining what the orchestrating agent is trying to
  implement in this section, what changed, and what "done" is supposed to mean

Ask reviewers to explicitly answer:

1. Does the implementation materially satisfy the spec and implementation plan,
   or is it only scaffolding/mocks/placeholders?
2. Are there tests or demos that merely prove the scaffolding works while core
   product behavior remains unimplemented?
3. Did the code introduce shortcuts, fake adapters, reward-hacking fixtures, or
   TODO-shaped gaps that should block acceptance?
4. Is the implementation the clean production shape implied by the current
   spec/plan and workflow compatibility policy?
5. Did the reviewer have enough spec, plan, code, and task context to make this
   judgment? If not, the round is not clean.

## Step 5: Run Review

### Parallel Mode

Launch all available models concurrently. Each writes to its own output file.
Use background execution so they run simultaneously.

**Codex GPT 5.5** (background bash):
```bash
codex -a never exec \
  -m gpt-5.5 \
  --sandbox read-only \
  --ephemeral \
  -C "$PWD" \
  -o "$REVIEW_DIR/codex_output.txt" \
  - \
  < "$REVIEW_DIR/prompt.txt" > "$REVIEW_DIR/codex_log.txt" 2>&1 &
CODEX_PID=$!
```
Timeout: 600000ms.

**Gemini 3.1 Pro via `agy`** (background bash):
```bash
agy --print \
  --sandbox \
  --model 'Gemini 3.1 Pro (High)' \
  --print-timeout 10m \
  < "$REVIEW_DIR/prompt.txt" \
  > "$REVIEW_DIR/gemini_output.txt" 2>&1 &
GEMINI_PID=$!
```

**Claude Opus reviewer** (subagent or CLI):

In Claude Code, launch a `general-purpose` subagent with
`run_in_background=true` and `model="opus"`. The prompt should include the
full contents of `$REVIEW_DIR/prompt.txt` and instruct the subagent to write its
review to `$REVIEW_DIR/claude_output.txt`. **Always specify
`model="opus"`** so Claude Code uses the latest Opus alias (currently Claude
Opus 4.8 in Claude Code 2.1.167). Without it, the orchestrator may default to a
weaker model.

Outside Claude Code, use Claude CLI:

```bash
claude \
  --print \
  --model opus \
  --permission-mode plan \
  --tools "" \
  --no-session-persistence \
  --max-budget-usd 5 \
  --output-format text \
  < "$REVIEW_DIR/prompt.txt" \
  > "$REVIEW_DIR/claude_output.txt" 2>&1 &
CLAUDE_PID=$!
```

**Same-family subagent rule:**

If the current harness supports spawning subagents, prefer a fresh read-only
subagent for the orchestrator's own model family. Give it the same prompt and
require a written output artifact. This counts as that family slot because it
starts from a clean context and did not implement the change under review.

**Wait for all to complete:**
```bash
wait $CODEX_PID 2>/dev/null; CODEX_EXIT=$?
wait $GEMINI_PID 2>/dev/null; GEMINI_EXIT=$?
if [ -n "${CLAUDE_PID:-}" ]; then wait $CLAUDE_PID 2>/dev/null; CLAUDE_EXIT=$?; fi
```
When a family slot is handled by a subagent instead of a CLI process, there may
be no shell PID. Check its output artifact before merging.

**Check results:**
- If a model exited non-zero or produced empty output, log the failure and
  continue with the others
- At least one model must succeed for the round to be valid
- If all three fail, report the errors and abort
- A degraded round can count toward an exhaustive gate if at least one external
  reviewer succeeded, but record the degradation and try to re-add failed
  reviewers in the next round

### Single-Model Mode

#### If Codex:
```bash
codex -a never exec \
  -m gpt-5.5 \
  --sandbox read-only \
  --ephemeral \
  -C "$PWD" \
  -o "$REVIEW_DIR/codex_output.txt" \
  - \
  < "$REVIEW_DIR/prompt.txt" > "$REVIEW_DIR/codex_log.txt" 2>&1
```
Timeout: 600000ms. May take 2-5 minutes.

#### If Gemini:

Pipe the prompt file via stdin. Do not use positional prompt arguments for
`agy`; they have routed to the wrong model in local smoke tests.

```bash
agy --print \
  --sandbox \
  --model 'Gemini 3.1 Pro (High)' \
  --print-timeout 10m \
  < "$REVIEW_DIR/prompt.txt" \
  > "$REVIEW_DIR/gemini_output.txt" 2>&1
```

#### If Claude:

Launch a `general-purpose` subagent via the Task tool with `model="opus"`
when inside Claude Code. Otherwise use Claude CLI with `--model opus` and
`--tools ""`. Have it write its review to `$REVIEW_DIR/claude_output.txt`.

## Step 6: Merge Results (Parallel Mode Only)

Read all successful output files and synthesize into a single merged finding
list. This is done by you (the orchestrating Claude), not by an external model.

**Merge rules:**
- **Deduplicate**: Same bug described differently by multiple models → one entry.
  Credit all models that found it.
- **Tag consensus**: Findings flagged by 2+ models → mark `[consensus]`. These
  are high-confidence issues.
- **Tag single-model**: Findings from only one model → mark with the source
  (e.g., `[codex-only]`, `[gemini-only]`, `[claude-only]`). These are worth
  investigating but may be false positives.
- **Normalize severity**: Use major (must fix) / minor (should fix) / note
  (observation/tradeoff). If models disagree on severity, use the highest.
- **Preserve specifics**: Keep file paths, line numbers, and function references
  from the most detailed report.
- **Escalate uncertainty**: If a reviewer says it lacked context, or identifies
  a genuine spec/plan inconsistency that cannot be resolved from project intent,
  mark it as a blocker rather than smoothing it over.
- **Compatibility policy check**: If backwards compatibility is disabled, treat
  legacy-compatibility carryover, transitional scaffolding, or obsolete
  experiment support as major. If compatibility is enabled, treat breaking
  changes or missing migrations as major. If unknown, mark compatibility
  questions as blockers when they affect acceptance.

Write the merged output to `$REVIEW_DIR/merged_review.md`.

**Header for merged review:**
```markdown
# Review Round — [date]

**Review Type**: code | spec-plan | implementation-slice | workflow
**Backwards Compatibility Matters**: true | false | unknown
**Models**: Codex/GPT, Claude, Gemini (or whichever participated; one per family)
**Degraded**: no | yes — reason
**Context**: ~Nk tokens
**Clean Result**: clean | not clean | blocked

## Findings

### Major
...

### Minor
...

### Notes
...
```

## Step 7: Session IDs

The default review commands are one-off. Codex uses `--ephemeral`, Claude CLI
uses `--no-session-persistence`, Claude subagents do not expose a portable
session ID here, and `agy` does not have a tested persistent-session workflow.
Do not capture or rely on session IDs in the normal parallel review flow.

## Step 8: Present Results

**Parallel mode**: Present the merged review from Step 6. Note which models
participated and if any were unavailable (e.g., "Codex hit rate limits; this
round used Gemini + Claude only").

**Single-model mode**: Read and present the model's output directly.

Clean means:
- no P0/P1/P2 or major findings
- no failing required tests or required validation gaps
- no unresolved spec/implementation-plan contradictions
- no unresolved data/security/privacy boundary findings
- compatibility policy satisfied, or compatibility policy unknown and no
  compatibility-sensitive blocker remains
- no reviewer reported insufficient context for the requested judgment

## Step 9: Follow-up (Optional)

If the user has follow-up questions, build a new focused prompt that includes
the follow-up question, the prior reviewer output, and only the needed
code/context. If you intentionally ran Codex without `--ephemeral` and captured
a session UUID, you may resume that session with `codex -a never exec resume`,
but do not use `--last` or `latest` in parallel review workflows.

Follow-ups are mostly relevant for single-model mode. In parallel mode, the
merged review usually has enough context to act on directly.

## Step 10: File Artifacts (if in workflow)

If this review is part of a workflow session (check if `planning/reviews/`
exists), file the review output:

1. Determine the current architecture version directory (e.g.,
   `planning/reviews/v1/`)
2. Find the next review number N
3. **Parallel mode**: Save merged review as
   `planning/reviews/vX/NN_review_round.md`
4. **Single-model mode**: Save as `planning/reviews/vX/NN_MODEL_review.md`

If not in a workflow session, skip artifact filing unless the user asks for it.

## Graceful Degradation

External models can hit rate limits or fail. Handle this without stopping:

| Situation | Action |
|-----------|--------|
| Codex rate-limited or fails | Drop Codex, continue with Gemini + Claude |
| Gemini / `agy` rate-limited or fails | Drop Gemini, continue with Codex + Claude |
| Claude unavailable/fails | Continue with Codex/GPT + Gemini or whichever external reviewers remain |
| Only one reviewer type succeeds | Valid but degraded; record it, keep the two-clean-round gate, and try to restore the full panel next round |

Log which models participated in each round. If degraded, note it when
presenting results so the user knows the round had reduced coverage.

In a multi-round review loop (workflow exhaustive review), if a model recovers
in a later round, add it back. Don't permanently exclude a model because it
failed once.

## Safety Rules

- **Never** use write-mode sandbox for reviews
- **Never** pass `--full-auto` to Codex
- **Always** sandbox: `--sandbox read-only` (Codex) or `--sandbox` (`agy`)
- **Always** build prompts as files, never as shell arguments
- **Always** include read-only instructions in the prompt text (belt + suspenders)
