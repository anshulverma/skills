---
name: auto-plan
description: Use when planning a multi-step feature or grilling an existing spec. Autonomous planning agent that wraps grill-with-docs with contextual auto-answering, iterative deepening, and sub-agent orchestration. Produces fully-grilled specs, ADRs, and implementation plans.
---

# Auto Plan

Autonomous planning skill. Builds a contextual model of the user's preferences, auto-answers grilling questions where confident, prompts only when genuinely uncertain, and produces fully-grilled design artifacts.

## Overview

```dot
digraph auto_plan {
    rankdir=TB

    "Parse args + detect input mode" [shape=box]
    "Phase 0: Bootstrap" [shape=box]
    "Phase 0.5: Idea Clarification" [shape=box]
    "Phase 1: Skeleton" [shape=box]
    "Small scope?" [shape=diamond]
    "Inline fast path" [shape=box]
    "Phase 2: Grill + Deepen" [shape=box]
    "Phase 3: Artifacts" [shape=box]
    "Phase 4: Final Verification" [shape=box]
    "Done" [shape=doublecircle]

    "Parse args + detect input mode" -> "Phase 0: Bootstrap"
    "Phase 0: Bootstrap" -> "Phase 0.5: Idea Clarification" [label="topic input"]
    "Phase 0: Bootstrap" -> "Phase 1: Skeleton" [label="spec file input"]
    "Phase 0.5: Idea Clarification" -> "Phase 1: Skeleton"
    "Phase 1: Skeleton" -> "Small scope?"
    "Small scope?" -> "Inline fast path" [label="≤3 branches\nnone uncertain"]
    "Small scope?" -> "Phase 2: Grill + Deepen" [label="4+ branches\nor uncertain"]
    "Inline fast path" -> "Phase 3: Artifacts"
    "Phase 2: Grill + Deepen" -> "Phase 2: Grill + Deepen" [label="new branches\ndiscovered"]
    "Phase 2: Grill + Deepen" -> "Phase 3: Artifacts"
    "Phase 3: Artifacts" -> "Phase 4: Final Verification"
    "Phase 4: Final Verification" -> "Done"
}
```

## Configuration

**Invocation:** `/auto-plan <topic or spec-path> [--flags]`

| Flag | Default | Description |
|------|---------|-------------|
| `--max-iterations` | `5` | Maximum grill-deepen cycles |
| `--max-depth` | `3` | Maximum branch nesting levels |
| `--confidence-threshold` | `medium` | `low` (fully autonomous), `medium`, `high`, `paranoid` (ask everything) |
| `--domains` | auto | Override domain detection (e.g., `--domains backend,infra`) |
| `--skip-plan` | off | Stop after spec + ADRs |
| `--plan-only` | off | Skip grilling, produce plan from existing spec. Requires spec file input. |
| `--auto-commit` | off | Commit artifacts without asking |
| `--dry-run` | off | Show skeleton + branches only |
| `--resume` | off | Continue interrupted session from state file |
| `--redo` | — | Change a decision (e.g., `--redo "use SQLite instead of PostgreSQL"`) |
| `--harden` | off | Run the hardening meta-loop: re-examine artifacts across fresh-context passes until convergence (Phase 5). |
| `--max-passes` | `3` | Maximum hardening passes. Distinct from `--max-iterations` (in-pass grill cycles). |
| `--unattended` | off | Suppress user prompts; bubble-up questions degrade to `UNRESOLVED` so the loop never blocks. |

**Phase matrix:**

| Mode | Phases | Output |
|------|--------|--------|
| Default | 0 → 0.5 → 1 → 2 → 3 → 4 | CONTEXT.md, spec, ADRs, plan |
| `--skip-plan` | 0 → 0.5 → 1 → 2 → 3 → 4 | CONTEXT.md, spec, ADRs |
| `--plan-only` | 0 → 3 → 4 | plan |
| `--dry-run` | 0 → 0.5 → 1 | nothing (shows skeleton) |
| `--resume` | load state → continue | remaining artifacts |
| `--redo` | load state → 2 → 3 → 4 | updated artifacts |
| `--harden` | 0 → … → 4, then Phase 5 loop | artifacts + convergence CSV/PNG + report |

## Input Mode Detection

- If args resolve to an existing `.md` file on disk → **spec file input** (skip Phase 0.5, use as skeleton)
- Otherwise → **topic string input** (full flow including Phase 0.5)

**File collision handling:** Before writing artifacts, check for existing files:
- State file exists for same topic → ask "resume or start fresh?"
- Completed artifacts exist, no state file → ask "overwrite or create -v2?"
- Nothing exists → proceed

**`--plan-only` with UNRESOLVED markers:** If the spec contains `UNRESOLVED:` markers, list them and offer: (a) plan with BLOCKED tasks, (b) resolve first, (c) abort.

## Phase 0: Bootstrap

1. Read all preference sources:
   - Claude Code memory files (`~/.claude/projects/.../memory/`)
   - CONTEXT.md, ADRs in `docs/adr/`
   - CLAUDE.md
   - Workbench APIs: `GET /api/memory/facts` (best-effort, skip if unavailable)

2. Detect domain(s) from the topic. Domain vocabulary is open: `backend`, `frontend`, `infrastructure`, `data-ml`, `devops`, `api-design`, `observability`, etc. Show detected domains in output. Override with `--domains` flag.

3. Load domain-tagged preferences. If a domain has no stored preferences, ask 2-3 calibration questions (batched), save answers as domain-tagged feedback memories.

4. If invoked mid-conversation, scan the **last 10 messages** for context relevant to the planning topic. Ignore unrelated messages.

5. Compile the **user model brief** (~1000 tokens):

```
## User Model Brief

### Base Preferences
- [3-5 bullets from base feedback memories]

### Domain Preferences: {domain}
- [2-3 bullets per detected domain]

### Active Constraints
- [from CLAUDE.md and relevant ADRs]

### Correction Patterns
- [things the user has corrected in past sessions]

### Session Directives
- [from explicit args and conversation context]
```

**Output:** `[auto-plan] Phase 0: loaded N memories, N ADRs, detected domains: x, y`

## Phase 0.5: Idea Clarification (topic input only)

**Skipped when:** input is a spec file, or `--plan-only` is set.

**Confidence override:** Always `very-high` regardless of `--confidence-threshold`. Only auto-answer when memory/ADR/CLAUDE.md explicitly covers the question. Everything else gets asked.

1. Scan last 10 messages for context already discussed
2. Identify what's unclear: purpose, constraints, success criteria, scope boundaries, trade-offs
3. Auto-answer from user model (only `very-high` confidence matches)
4. Ask remaining questions **one at a time** until confident
5. If the design space is open, propose 2-3 architectural approaches with trade-offs and recommendation
6. **Exit condition:** you can write a one-paragraph summary of what's being built and why. Confirm with the user.

**Scope decomposition:** If the topic describes 4+ independent subsystems, suggest decomposition with natural seams. Plan one sub-project at a time. User re-invokes for the rest.

**Output:** `[auto-plan] Phase 0.5: idea clarification — N questions answered, N asked`

## Phase 1: Skeleton

1. Produce a high-level spec outline: section headings, key decisions, scope boundaries
2. If input is an existing spec, extract branches from its sections
3. If invoked mid-conversation, distill conversation context into the topic description and user model brief
4. Identify **branches** — each design decision or section needing exploration. Target 5-15 grilling questions per branch. Split sections with 30+ decisions into sub-branches.
5. Assign confidence:
   - `known` — ADR/memory covers it
   - `likely` — can auto-answer from domain principles
   - `uncertain` — needs a Griller sub-agent
6. Do a broad codebase survey (read key files, or dispatch a Researcher) to produce a **codebase context summary** (~1000 tokens)

**Small scope fast path:** If ≤3 branches and none `uncertain`, handle grilling inline — no sub-agents. Still follow the grill-with-docs protocol, still produce artifacts.

**Output:** `[auto-plan] Phase 1: skeleton has N branches (N known, N likely, N uncertain)`

## Phase 2: Grill + Deepen

**Loop until:** no `uncertain` branches remain AND no unresolved questions, OR `--max-iterations` hit.

### Dispatching Grillers

For each `uncertain` or `likely` branch, spawn a Griller sub-agent via the Agent tool:

```
Agent({
  description: "Grill: {branch topic}",
  prompt: [assembled from below],
  model: "opus"
})
```

**Griller prompt assembly:**
1. Task brief: "You are grilling the '{branch topic}' branch of this design. Follow the Griller Protocol below."
2. Read and paste contents of `GRILLER-PROTOCOL.md` from this skill's directory
3. Read and paste contents of `GRILLER-RESPONSE-TEMPLATE.md` from this skill's directory
4. User model brief (~1000 tokens)
5. Full CONTEXT.md content
6. Curated codebase context for this branch (relevant file excerpts only)
7. Settled decisions as constraints: "These decisions are settled. Do not re-decide them: [list]"

**Parallel dispatch strategy:**
- First iteration: dispatch all branches in parallel (can't predict overlap upfront)
- Subsequent iterations: sequence branches that touched the same types/interfaces in prior rounds. Truly independent branches stay parallel.

### Collecting Results

After Grillers return, the orchestrator:

1. **Reads each response** holistically (structured by the response template, not brittle parsing)
2. **Accepts** high-confidence auto-answers → fold into decision log
3. **Shows** medium-confidence auto-answers to the user with rationale → batch-confirm
4. **Prompts** for unresolved questions (batched, with recommendations):
   ```
   I have N questions I couldn't resolve from your preferences:

   1. [Topic] I'd pick: [answer]. Reasoning: [why]. Agree?
   2. [Topic] Genuinely uncertain — two approaches:
      a) [option A]
      b) [option B]
      Which do you prefer?
   ```
5. **Saves** user corrections as domain-tagged feedback memories immediately
6. **Adds** discovered new branches to the queue
7. **Fetches** requested files (from Files Needed sections) — reads directly if path is known, dispatches a Researcher if open-ended
8. **Detects conflicts** across parallel Grillers — contradictory decisions become a new branch

### Conflict Resolution

Three layers:
1. **Prevention:** settled decisions passed as constraints to every Griller
2. **Detection:** post-collection scan for contradictions. Conflicting decisions → new branch in next iteration.
3. **Sequencing:** branches that overlapped in prior rounds get sequenced in subsequent iterations

### Researcher Sub-Agents

When a Griller needs codebase context the orchestrator didn't anticipate, or when the orchestrator needs to answer a factual question:

- **Known file path** → orchestrator reads directly (no sub-agent)
- **Open-ended exploration** → dispatch a Researcher:

```
Agent({
  description: "Research: {question}",
  prompt: "Explore the codebase to answer: {question}. Use whatever search and exploration tools are available. Return findings as structured facts.",
  model: "sonnet"
})
```

Researchers are dispatched as general-purpose agents (not Explore type) for full tool access. The prompt constrains to read-only behavior.

### depends_on Inference

When the orchestrator passes settled decisions `[dec-001, dec-003]` as constraints to a Griller, and the Griller's answer references one of those constraints, the orchestrator records the dependency: `{id: "dec-012", depends_on: ["dec-001"]}`. This is fuzzy matching by the orchestrator reading the Griller's reasoning — not exact string matching. A wrong link just means an extra branch gets re-grilled on `--redo` (safe).

### Sub-Agent Failure Handling

- **Garbage response** (no recognizable sections) → log warning, re-queue the branch
- **Timeout** → same as garbage
- **Partial results** (some sections present) → accept what's there, treat missing as unresolved
- **Repeated failure** (same branch fails 2+ times) → mark as `failed` in state file, surface in report, continue with other branches

### Max-Iterations Reached

If `--max-iterations` is hit with uncertain branches remaining:
- Produce **partial artifacts** with `UNRESOLVED: [question — recommended: answer]` markers
- **No implementation plan** produced (can't plan unresolved design)
- Planning report flags unresolved branches
- User can re-run `/auto-plan <spec-path>` to continue grilling

**Output per iteration:** `[auto-plan] Phase 2/iter N: N decisions resolved, N unresolved, N new branches`

### State File

After each iteration, write full state as JSON to `docs/auto-plan/reports/YYYY-MM-DD-<topic>-state.json`. **Full rewrite each time** (not incremental — avoids JSON corruption). Create `docs/auto-plan/reports/` directory if it doesn't exist. This is the source of truth — survives context compression and session interruption.

State file structure:
```json
{
  "topic": "...",
  "domains": ["..."],
  "iteration": 3,
  "phase": "grill-deepen",
  "user_model_brief": "...",
  "branches": [
    {"id": "b001", "topic": "...", "confidence": "...", "depth": 1, "parent": null, "status": "resolved|uncertain|failed"}
  ],
  "decisions": [
    {"id": "d001", "question": "...", "answer": "...", "confidence": "...", "source": "...", "domain": "...", "branch": "b001", "depends_on": [], "status": "resolved|invalidated"}
  ],
  "unresolved": [],
  "preference_updates": [],
  "artifacts": {"context_md": "...", "spec": "...", "adrs": [], "plan": "..."}
}
```

State file is **always kept** (not deleted on completion). Required for `--redo` and `--resume`.

**`--harden` extension.** When `--harden` is set, the state gains one top-level `harden` object.
The full-rewrite-each-pass discipline is unchanged (the whole file is re-serialized after every
mutation; never patched in place).

```json
"harden": {
  "enabled": true,
  "max_passes": 3,
  "current_pass": 2,
  "convergence_status": "in_progress",
  "snapshots_dir": "docs/auto-plan/reports/snapshots",
  "passes": [
    {
      "pass": 1,
      "started_at": "2026-06-05T10:00:00Z",
      "completed_at": "2026-06-05T10:08:00Z",
      "status": "complete",
      "snapshot_path": "docs/auto-plan/reports/snapshots/pass-1",
      "judge_verdict": "NOT CONVERGED",
      "judge_rationale": "Spec gained an error-handling section; 2 ADRs revised.",
      "fingerprint": ["d014", "d015", "spec:error-handling"],
      "gaps_filled": ["partial-write recovery", "retry semantics"],
      "questions_bubbled_up": [],
      "decisions_delta": {"added": ["d014", "d015"], "modified": ["d007"], "invalidated": []},
      "metrics": {"material_changes": 2, "minor_changes": 4, "open_gaps": 0,
                  "pending_questions": 0, "unresolved_markers": 0, "instability_score": 2}
    }
  ]
}
```

`convergence_status` ∈ `in_progress | converged | max_passes_reached | oscillation | failed | interrupted`.
`current_pass` and `convergence_status` sit at the top of the `harden` object for quick inspection.
**Two-phase write:** each pass entry is written as `status:"running"` (with `judge_verdict:null`)
*before* the Pass agent runs, then updated to `status:"complete"` *after* the judge verdicts — the
`running`→`complete` transition is how an interrupted pass is detected.

**Snapshots.** Plain file copies (not git commits, not a concatenated history file) under
`docs/auto-plan/reports/snapshots/pass-N/`, preserving original artifact filenames including any
`adr/NNNN-*.md`. Each `pass-N/` holds the full pre-overwrite artifact set. Retention: keep the last
2 pass directories, pruning older ones as each new pass starts (the per-pass changelog in state is
the permanent audit trail). The artifact filename date prefix is frozen at Pass 1's date so paths
never churn across multi-day runs.

**Output:** `[auto-plan] State saved to docs/auto-plan/reports/YYYY-MM-DD-<topic>-state.json`

## Phase 3: Artifacts

Produce artifacts in dependency order. Each passes its own review before the next begins.

### Commit Strategy

If `--auto-commit` is set, commit each artifact after it passes review. Otherwise, ask once at the start of Phase 3: "I'll commit each artifact separately as it passes review. OK?" If yes, commit without asking again.

### 1. CONTEXT.md Updates

Applied incrementally during Phase 2. No separate write step.

### 2. Spec

1. Read `WRITER-SPEC-PROTOCOL.md` from this skill's directory
2. Dispatch a Writer sub-agent:

```
Agent({
  description: "Write spec: {topic}",
  prompt: [
    "Write a design spec following the Writer Spec Protocol below.",
    contents of WRITER-SPEC-PROTOCOL.md,
    "Resolved decisions:", [full decision log from state],
    "User model brief:", [brief],
    "CONTEXT.md:", [content]
  ],
  model: "opus"
})
```

3. Dispatch a Reviewer sub-agent:

```
Agent({
  description: "Review spec: {topic}",
  prompt: [
    "Review this spec against the checklist below.",
    contents of SPEC-REVIEW-CHECKLIST.md,
    "Decision log (every decision must appear in the spec):", [decisions],
    "CONTEXT.md:", [content],
    "Spec to review:", [spec content]
  ],
  model: "opus"
})
```

4. If FAIL → Writer fixes → Reviewer re-reviews → loop until PASS
5. Save to `docs/auto-plan/specs/YYYY-MM-DD-<topic>-design.md`
6. Commit (if approved)

### 3. ADRs

For each ADR candidate that meets all three criteria (hard to reverse + surprising + real trade-off):

1. Writer sub-agent produces the ADR (short: title + 1-3 sentences)
2. Save to `docs/adr/NNNN-<slug>.md` (next sequential number)
3. Commit

### 4. Implementation Plan

**Skipped when:** `--skip-plan` is set, or spec has UNRESOLVED markers (unless user chose "plan with BLOCKED tasks").

1. Read `WRITER-PLAN-PROTOCOL.md` from this skill's directory
2. Dispatch Writer sub-agent with spec + plan protocol
3. Dispatch Reviewer with `PLAN-REVIEW-CHECKLIST.md`
4. Fix → re-review → loop until PASS
5. Save to `docs/auto-plan/plans/YYYY-MM-DD-<topic>.md`
6. Commit

**Output:** `[auto-plan] Phase 3: spec PASS, N ADRs written, plan PASS`

## Phase 4: Final Verification

Dispatch a Reviewer sub-agent with `FINAL-REVIEW-CHECKLIST.md` and all produced artifacts.

```
Agent({
  description: "Final review: {topic}",
  prompt: [
    "Cross-cutting review of all artifacts.",
    contents of FINAL-REVIEW-CHECKLIST.md,
    "Spec:", [content],
    "Plan:", [content],
    "ADRs:", [content],
    "CONTEXT.md:", [content]
  ],
  model: "opus"
})
```

If FAIL → fix affected artifacts → re-review → loop until PASS.

**Output:** `[auto-plan] Phase 4: final verification PASS`

## Phase 5: Hardening Meta-Loop

**Enabled by:** `--harden`. **Skipped otherwise.** Phase 5 wraps Phases 0–4. Pass 1 is the
normal full run (interactive — Phase 0.5 talks to the user) and produces the baseline artifacts
(**Snapshot-0**). Passes 2…`--max-passes` re-examine the full artifact set in fresh, isolated
context, fill gaps, and harden the plan until convergence.

**Pass vs Iteration.** A **Pass** is one full re-examination of the artifact set in fresh context
(bounded by `--max-passes`, default 3). An **Iteration** is a grill-deepen cycle *inside* a single
pass (bounded by `--max-iterations`). The two loops are orthogonal and nest.

**Input modes.** `--harden` accepts a topic string (Pass 1 = full run including Phase 0.5) and an
existing spec file (Pass 1 = grill that spec). Either way, Pass 1's Phase 4 output is Snapshot-0.

**Flag composition.** Legal with `--skip-plan`, `--plan-only`, `--resume`, `--confidence-threshold`,
`--auto-commit`, `--unattended`. **Illegal with `--dry-run`** — hard error: "`--harden` cannot
combine with `--dry-run`" (dry-run produces no artifacts to converge on). `--redo` is independent:
it runs its own cascade and does **not** auto-re-harden; re-hardening requires an explicit
`--harden` re-invocation.

**Cost notice.** Before the loop, print one line and do **not** block for confirmation
(escalations still pause for the user):
`[auto-plan --harden] up to N passes, each re-examines the full artifact set; stopping at convergence.`

### The Loop

```
pass ← 1
run Phases 0–4 normally          # interactive; produces baseline artifacts = Snapshot-0
while pass < max_passes:
    pass ← pass + 1
    write state: harden.passes[] += {pass, status:"running", judge_verdict:null}   # full rewrite
    snapshot current artifacts → docs/auto-plan/reports/snapshots/pass-(pass-1)/
    result ← dispatch Hardening Pass agent (fresh context)
    if result is failure:
        retry once; on 2nd failure → status:"failed", keep last-good artifacts, break
    if result has Bubble-Up Questions and interactive and not --unattended:
        answers ← ask user (batched, deduped); save as feedback memories + settled decisions
        # answers are applied by the NEXT pass (record-and-defer) — no mid-pass re-dispatch
    else if result has Bubble-Up Questions:
        record each as UNRESOLVED with its recommended answer        # unattended / low threshold
    apply result.Edits in place; full-rewrite state (decisions delta, status:"complete")
    verdict ← dispatch Convergence judge (fresh context)             # independent diff
    metrics ← compute instability_score from verdict + state
    write state: harden.passes[pass].{judge_verdict, metrics, fingerprint}; full rewrite
    if converged(verdict): status ← "converged"; break
    if oscillation(pass fingerprints): status ← "oscillation"; break
if pass == max_passes and not converged: status ← "max_passes_reached"
emit report + convergence CSV + convergence PNG
```

`converged(verdict)` is true iff `verdict.material_changes == 0` AND `verdict.open_gaps == 0` AND no
`UNRESOLVED:` marker remains in any artifact AND no bubble-up question is pending an answer — i.e.
exactly `instability_score == 0`.

### Dispatching the Hardening Pass agent

```
Agent({
  description: "Harden pass {N}: {topic}",
  prompt: [
    "Harden the full artifact set following the Hardening Pass Protocol below.",
    contents of HARDENING-PASS-PROTOCOL.md,
    contents of HARDENING-PASS-RESPONSE-TEMPLATE.md,
    contents of SPEC-REVIEW-CHECKLIST.md, PLAN-REVIEW-CHECKLIST.md, FINAL-REVIEW-CHECKLIST.md,
    "Current artifacts (spec, ADRs, plan, CONTEXT.md):", [content],
    "Decision log + unresolved (from state):", [content],
    "Settled decisions (constraints — do not re-decide):", [list],
    "User model brief:", [brief],
    "Prior-pass change summaries:", [summaries],
    "Confidence threshold:", [--confidence-threshold]
  ],
  model: "opus"
})
```

The Pass agent does a **single-context review-and-patch**: it reads all artifacts itself, proposes
**material-only** edits as full-file replacement bodies, and spawns no sub-agents. It never writes
to disk. **Ordering (orchestrator-owned):** `snapshot → apply edits (overwrite) → full-rewrite
state → dispatch judge`. The snapshot strictly precedes the overwrite so an interrupted pass is
recoverable.

### Collecting Pass Results

Read the Pass agent's response (structured by `HARDENING-PASS-RESPONSE-TEMPLATE.md`) by its seven
section headers:

1. **Edits** — apply each full-file body in place (after snapshotting).
2. **Decisions Changed** — fold into the decision log (`decisions_delta`).
3. **Gaps Filled** — record in the pass's `gaps_filled`.
4. **Unresolved Resolved** — remove the corresponding `UNRESOLVED:` markers.
5. **ADR Candidates** — write any that meet all three ADR criteria.
6. **Bubble-Up Questions** — handle per Escalation below.
7. **Material Change Assessment** — the Pass agent's self-report; input to the judge (cross-check only).

### Dispatching the Convergence judge

```
Agent({
  description: "Judge convergence: pass {N}",
  prompt: [
    "Decide whether the loop has converged, following the checklist below.",
    contents of CONVERGENCE-JUDGE-CHECKLIST.md,
    "Snapshot (pass N-1):", [content],
    "Current artifacts (pass N):", [content],
    "Pass agent Material Change Assessment:", [content]
  ],
  model: "opus"
})
```

The judge **independently diffs** snapshot vs current and emits `Verdict` / `Changes` / `Open Gaps`
/ `Rationale`. The Pass agent's self-report is a cross-check only. It runs after **every** pass —
including Pass 1, which diffs against Snapshot-0. Ambiguous changes are classified **material**
(conservative bias).

### Escalation / Bubble-Up

Pass agents are non-interactive; only the orchestrator talks to the user. On collecting a pass's
`Bubble-Up Questions`, the orchestrator asks the user immediately (batched, with recommendations,
**deduped** against already-answered/deferred questions), saves each answer as a domain-tagged
feedback memory and a settled decision (`source: "user/bubble-up"`), and the **next** pass applies
them (record-and-defer). Applying an answer is itself a material change, so a pass that only raised
questions is never converged.

**Confidence gating** (by `--confidence-threshold`):

| Threshold | Bubble-up behavior |
|-----------|--------------------|
| `low` | Never bubble up; every low-confidence question becomes `UNRESOLVED` with a recommended answer. |
| `medium` (default) | Bubble up only genuinely-novel material trade-offs; routine gaps become `UNRESOLVED`. |
| `high` | Bubble up all material low-confidence questions. |
| `paranoid` | Bubble up every low-confidence question. |

**Unattended runs.** When `--unattended` is set, or no interactive channel is detected (running as
a sub-agent / scheduled), bubble-up is disabled: every would-be question becomes `UNRESOLVED` with a
recommended answer and the loop continues without blocking. An `UNRESOLVED` marker is
"answered: deferred" — it does not block convergence and is not re-asked.

**Contradiction with a settled decision.** If a user's bubble-up answer contradicts a settled
decision, reuse the `--redo` cascade: mark the contradicted decision `invalidated`, walk
`depends_on` to re-queue affected gaps, apply the >60%-invalidated "consider re-planning" warning,
and continue under the corrected constraint.

### Termination

| Condition | Detected by | Emitted | `convergence_status` |
|-----------|-------------|---------|----------------------|
| Convergence | judge: 0 material + 0 gaps + 0 UNRESOLVED + 0 pending | final hardened artifacts | `converged` |
| Pass budget exhausted | orchestrator: `pass == max_passes`, not converged | most-hardened artifacts + surviving `UNRESOLVED` markers + "did not converge" banner | `max_passes_reached` |
| Oscillation | orchestrator: pass-N fingerprint == pass-(N-2) | the version with fewer open gaps; tie → latest | `oscillation` |
| Hard failure | Pass agent garbage/timeout twice | last-good artifacts | `failed` |

A retried (failed-then-redispatched) pass does **not** consume the `--max-passes` budget.
Oscillation compares the per-pass material-change **fingerprint** sets stored in state (not raw
text), so minor edits don't mask a ping-pong. Oscillation detection is orchestrator-owned; the
judge stays stateless and pairwise.

### Convergence Metric and Chart

Each pass yields an **instability score**:

```
instability_score = material_changes + open_gaps + pending_questions + unresolved_markers
```

It reaches 0 exactly at convergence — the numeric form of the stop condition. Per-pass metrics are
stored in `harden.passes[].metrics` and written to
`docs/auto-plan/reports/YYYY-MM-DD-<topic>-convergence.csv` on every run (no dependencies). CSV
columns: `pass,material_changes,minor_changes,open_gaps,pending_questions,unresolved_markers,instability_score`.

A best-effort PNG at `docs/auto-plan/reports/YYYY-MM-DD-<topic>-convergence.png` plots the
instability score (plus component lines) against pass number, titled `Convergence — <topic>`.
Rendering mirrors the `dot -Tpng` best-effort pattern: try `python3` + matplotlib (from the CSV),
else `gnuplot`, else skip the PNG and embed an ASCII sparkline of the instability score in the
report with a note that no renderer was found.

**Output per pass:** `[auto-plan] Phase 5/pass N: instability=K (material M, gaps G, pending P, unresolved U) — <verdict>`

## --redo Support

```
/auto-plan docs/auto-plan/specs/topic-design.md --redo "use SQLite instead of PostgreSQL"
```

1. Load state file for the spec
2. Find decisions affected by the redo directive (orchestrator judgment — "use SQLite" affects anything that referenced PostgreSQL)
3. Mark affected decisions as `invalidated`
4. Walk `depends_on` links — any branch that produced or consumed an invalidated decision gets re-queued as `uncertain`
5. **Cascade check:** if >60% of decisions are invalidated, suggest starting fresh instead
6. Run Phase 2 with the new constraint injected into every Griller's brief
7. Re-generate affected artifacts
8. Run Phase 4

`--redo` is **independent of the hardening meta-loop**: it operates on the decision log, does not
run inside a pass, creates no snapshots, and does not auto-re-harden. To re-harden after a `--redo`,
re-invoke with `--harden`.

## --resume Support

```
/auto-plan docs/auto-plan/specs/topic-design.md --resume
```

1. Load state file
2. Check current phase and progress
3. Continue from where interrupted — if mid-Phase 2, resume the grilling loop; if between phases, start the next phase

**`--harden` re-entry.** If the state has a `harden` object, read `harden.convergence_status` and
`harden.current_pass`. If the last `passes[]` entry is `status:"running"` (interrupted mid-pass),
restore the artifacts from its snapshot, then re-run that pass. If `status:"complete"` but not
converged, start the next pass. If terminal (`converged` / `max_passes_reached` / `oscillation` /
`failed`), the meta-loop is done — fall through to normal completion.

Also triggered automatically: if the skill detects a state file for the topic on startup (without `--resume` flag), ask "Found interrupted session. Resume or start fresh?"

## Planning Report

At the end of execution, produce and commit `docs/auto-plan/reports/YYYY-MM-DD-<topic>-report.md`:

```markdown
# Planning Report: {topic}

## Execution Stats
- Duration: Nm
- Sub-agents spawned: N (N grillers, N writers, N reviewers, N researchers)
- Grilling iterations: N
- Hardening passes: N         (only when --harden; omit otherwise)
- Questions auto-answered: N
- Questions asked to user: N
- Branches explored: N
- Max depth reached: N
- Conflicts detected: N

## Decision Log
| # | Question | Answer | Confidence | Source | Domain | Branch |
|---|----------|--------|------------|--------|--------|--------|
| 1 | ... | ... | ... | ... | ... | ... |

## Hardening Passes

_Only when `--harden` was used. `Convergence: <status> after N passes`, followed by:_

| Pass | Material? | Gaps Filled | Questions Bubbled Up | Verdict Rationale | Snapshot |
|------|-----------|-------------|----------------------|-------------------|----------|
| 1 | yes | 2 | 0 | spec gained error-handling section | `snapshots/pass-1/` |
| 2 | no (minor) | 0 | 1 | only wording changes | `snapshots/pass-2/` |

![convergence](YYYY-MM-DD-<topic>-convergence.png)

_(If no PNG renderer was found, embed an ASCII sparkline of the instability score instead and note
the PNG was skipped. The convergence CSV is always written.)_

## Branch Tree

[ASCII tree]

(see .dot file for graphviz source)

## Preference Updates
- [list of preferences saved/updated]

## Artifacts Produced
- [list of files written]
```

### Branch Tree Visualization

Three formats:

1. **ASCII tree** in the report (always produced):
```
Skeleton (N branches)
├── Branch A (N decisions) [auto-answered]
│   └── Sub-branch (N decisions) [discovered]
├── Branch B (N decisions) [user input]
└── Branch C (N decisions) [from ADR]
```

2. **Graphviz .dot file** at `docs/auto-plan/reports/YYYY-MM-DD-<topic>-tree.dot`:
   Color coding: palegreen=auto-answered, lightskyblue=user input, lightgray=ADR/memory, lightyellow=discovered, lightcoral=unresolved, salmon=failed

3. **Rendered PNG** via `dot -Tpng` (best-effort — skip if graphviz not installed, note in report)

## Preference Store

**Writing preferences:** When the user corrects an auto-answer or confirms a surprising one, save immediately as a domain-tagged feedback memory:

```markdown
---
name: preference-{slug}
description: {one line}
metadata:
  type: feedback
  domains: [{domain list}]
---

{preference content}
**Why:** {reason from user}
**How to apply:** {when this preference kicks in}
```

Write to `~/.claude/projects/.../memory/`. Update MEMORY.md index.

**Reading preferences:** Check Claude Code memory files first (primary), then workbench `GET /api/memory/facts` (supplemental, best-effort).

## Output File Layout

```
docs/auto-plan/
  specs/YYYY-MM-DD-<topic>-design.md
  plans/YYYY-MM-DD-<topic>.md
  reports/
    YYYY-MM-DD-<topic>-report.md
    YYYY-MM-DD-<topic>-tree.dot
    YYYY-MM-DD-<topic>-tree.png         (best-effort)
    YYYY-MM-DD-<topic>-state.json       (always kept)
    YYYY-MM-DD-<topic>-convergence.csv  (--harden only; always written)
    YYYY-MM-DD-<topic>-convergence.png  (--harden only; best-effort)
    snapshots/pass-N/                   (--harden only; last 2 retained)
docs/adr/NNNN-<slug>.md
```
