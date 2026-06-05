# auto-plan Hardening Meta-Loop (`--harden`) — Design Spec

## Context

`auto-plan` today runs Phases 0–4 exactly once and emits a spec, ADRs, and an implementation
plan. A single pass produces good artifacts but never re-reads them with fresh eyes: gaps the
first run left unspecified, cross-artifact inconsistencies, and weakly-hardened edge cases go
uncaught. This feature adds an opt-in `--harden` meta-loop that re-examines the generated
artifacts in cleared context across multiple **passes**, filling gaps and hardening the plan
until a pass produces no meaningful change.

## Goals

1. **Iterative hardening** — re-run the whole flow over the existing artifacts, pass after pass, to fill gaps and harden the design rather than regenerate it.
2. **Fresh-context passes** — each pass runs in a fresh, isolated sub-agent so prior reasoning never contaminates the new read.
3. **Numeric convergence** — every pass yields an instability score that reaches 0 exactly at convergence, plotted as a best-effort PNG chart beside the report.
4. **Escalate, never guess** — a low-confidence pass bubbles its questions up to the interactive orchestrator, which asks the user; unattended runs degrade to UNRESOLVED instead of blocking.
5. **Bounded and safe** — the loop always terminates (convergence, pass budget, oscillation, or hard failure) and never corrupts artifacts mid-pass.
6. **Convention-consistent** — opt-in flag, fragment-per-sub-agent, single full-rewrite state file, best-effort rendering — all matching existing `auto-plan` conventions.

## Architecture

```
auto-plan --harden <topic | spec>
  │
  ▼
PASS 1  ── normal Phases 0→0.5→1→2→3→4 (interactive) ──► baseline artifacts = Snapshot-0
  │
  ▼  ┌──────────────────────── outer orchestrator loop (Phase 5) ────────────────────────┐
  │  │  pass = 2,3,…,max_passes                                                            │
  │  │   1. snapshot current artifacts → reports/snapshots/pass-(n-1)/                     │
  │  │   2. dispatch Hardening Pass agent (fresh ctx) ── reads full artifact set + log     │
  │  │      └─► returns proposed edits + bubble-up questions + material assessment         │
  │  │   3. if bubble-up questions → orchestrator asks user (batched), saves answers,      │
  │  │      records as settled decisions for the NEXT pass                                 │
  │  │   4. orchestrator applies edits in place; full-rewrites state                       │
  │  │   5. dispatch Convergence judge (fresh ctx) ── independent diff snapshot vs current │
  │  │      └─► Verdict CONVERGED / NOT CONVERGED + per-change classification + open gaps  │
  │  │   6. compute instability score; append metrics to state                            │
  │  │   7. stop if converged ∥ oscillation ∥ max_passes; else loop                        │
  │  └────────────────────────────────────────────────────────────────────────────────────┘
  ▼
emit final artifacts + planning report + convergence CSV + convergence PNG
```

The orchestrator is thin: it owns file I/O, snapshots, the state file, user prompts, oscillation
detection, and the loop. Each pass and each judge call is a fresh isolated sub-agent that spawns
no agents of its own.

## Invocation and Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--harden` | off | Enable the hardening meta-loop. Bare boolean. |
| `--max-passes` | `3` | Maximum number of hardening passes. Distinct from `--max-iterations` (in-pass grill cycles). |
| `--unattended` | off | Suppress all user prompts; bubble-up questions degrade to UNRESOLVED so the loop never blocks. |

**Pass vs Iteration.** A **Pass** is one full re-examination of the artifact set in fresh
context (bounded by `--max-passes`). An **Iteration** is a grill-deepen cycle *inside* a single
pass (bounded by the existing `--max-iterations`). The two loops are orthogonal and nest.

**Input modes.** `--harden` accepts both a topic string (Pass 1 is a full run including Phase
0.5) and an existing spec file (Pass 1 grills that spec). Either way, Pass 1's Phase 4 output is
the baseline (Snapshot-0).

**Flag composition.**

| Combined with | Behavior |
|---------------|----------|
| `--skip-plan` | Legal — passes harden spec + ADRs only. |
| `--plan-only` | Legal — Pass 1 is the existing `--plan-only` flow; passes harden the plan. |
| `--resume` | Legal — re-enters the meta-loop at the recorded pass. |
| `--confidence-threshold` | Legal — gates bubble-up frequency (see Escalation). |
| `--auto-commit` | Legal — commits once per pass. |
| `--unattended` | Legal — forces UNRESOLVED-degradation regardless of threshold. |
| `--dry-run` | **Illegal** — hard error: "`--harden` cannot combine with `--dry-run`" (dry-run produces no artifacts to converge on). |
| `--redo` | Independent — `--redo` runs its own cascade and does not auto-re-harden; re-hardening requires an explicit `--harden` re-invocation. |

## Phase 5: Hardening Meta-Loop

Phase 5 wraps Phases 0–4. Pass 1 runs the existing flow unchanged and is the only interactive
pass. Passes 2…`max_passes` execute the loop body below.

```
pass ← 1
run Phases 0–4 normally        # interactive; produces baseline artifacts
snapshot baseline as Snapshot-0
while pass < max_passes:
    pass ← pass + 1
    write state: passes[] += {pass, status:"running", judge_verdict:null}   # full rewrite
    snapshot current artifacts → reports/snapshots/pass-(pass-1)/
    result ← dispatch Hardening Pass agent (fresh context)
    if result is failure:
        retry once; on 2nd failure → stop (status:"failed"), keep last-good, break
    if result.bubble_up_questions and interactive and not unattended:
        answers ← ask user (batched, deduped); save as feedback memories + settled decisions
        # answers are applied by the NEXT pass (record-and-defer)
    else if result.bubble_up_questions:
        record each as UNRESOLVED with recommended answer        # unattended / low threshold
    apply result.edits in place; full-rewrite state (decisions delta, status:"complete")
    verdict ← dispatch Convergence judge (fresh context)         # independent diff
    metrics ← compute instability score from verdict + state
    write state: passes[pass].{judge_verdict, metrics, fingerprint}; full rewrite
    if converged(verdict): status ← "converged"; break
    if oscillation(pass fingerprints): status ← "oscillation"; break
if pass == max_passes and not converged: status ← "max_passes_reached"
emit report + convergence CSV + convergence PNG
```

**`converged(verdict)`** is true iff: `verdict.material_changes == 0` AND `verdict.open_gaps == 0`
AND no `UNRESOLVED` marker remains in any artifact AND no pending bubble-up question awaits an
answer. This is exactly `instability_score == 0`.

**Cost notice.** Before the loop, the orchestrator prints one line:
`[auto-plan --harden] up to N passes, each re-examines the full artifact set; stopping at convergence.`
It does not block for confirmation (the user values autonomy); escalations still pause for input.

## Hardening Pass Agent

A single sub-agent that hardens the whole artifact set in one cleared context. It performs a
**review-and-patch**, not a re-plan: it does **not** re-invoke `auto-plan` and spawns **no**
sub-agents of its own (this caps nesting and keeps the operation a hardening pass rather than a
regeneration).

**Inputs (assembled by the orchestrator into the agent prompt):**
- The full current artifact set as text: spec, all ADRs, plan, CONTEXT.md.
- The `decisions` and `unresolved` arrays from the state file.
- The settled-decisions list (passed as constraints; the agent treats them as facts).
- The user model brief.
- The prior-pass change summaries.
- `HARDENING-PASS-PROTOCOL.md`, `HARDENING-PASS-RESPONSE-TEMPLATE.md`, and the three review
  checklists (`SPEC-REVIEW-CHECKLIST.md`, `PLAN-REVIEW-CHECKLIST.md`, `FINAL-REVIEW-CHECKLIST.md`)
  as the standard it hardens against.

**Behavior:**
- It proposes edits only for **material** changes (per CONTEXT.md). Standalone minor edits
  (wording/formatting) are forbidden — this is what guarantees convergence and prevents endless
  cosmetic churn. A minor tweak may ride along only with a material edit to the same section.
- Edits are returned as **full-file replacement bodies** for each artifact it touches (reliable
  to apply in a pure-Markdown environment; the orchestrator computes its own diff against the
  snapshot).
- It never writes to disk. The orchestrator applies edits after snapshotting (ordering below).
- For each gap: if it can resolve at or above the run's `--confidence-threshold`, it makes the
  edit and lists the source under Gaps Filled; otherwise it records a Bubble-Up Question with a
  recommendation and leaves the gap intact.
- If it needs a file it wasn't given, it lists it under Bubble-Up Questions (Files Needed); the
  orchestrator fetches it (direct read or a Researcher) and re-dispatches the same pass.
- If it disagrees with a settled decision, it records the conflict under Bubble-Up Questions
  (flagged `conflict-with-settled: dNNN`); it never edits an artifact to contradict a settled
  decision.
- Model: **opus** (the hardest reasoning in the loop — cross-artifact consistency).

**Ordering guarantee (orchestrator-owned):** for each pass —
`snapshot → apply edits (overwrite) → full-rewrite state → dispatch judge`. The snapshot strictly
precedes the overwrite so an interrupted pass is always recoverable from its snapshot.

### HARDENING-PASS-RESPONSE-TEMPLATE.md (contract)

The Pass agent responds with exactly these section headers; the orchestrator's Phase 5 collection
logic parses them. Changing a header here requires updating SKILL.md's collection logic (contract).

```
### Edits
- [artifact: spec|adr-NNNN|plan|context] | [section/anchor] | [full replacement body] | Why: [reason]
### Decisions Changed
- [d-id or NEW] | [question] | [old answer → new answer] | Confidence | Source
### Gaps Filled
- [gap] | [how filled] | Source: [...]
### Unresolved Resolved
- [original UNRESOLVED question] | Resolution: [...] | Confidence
### ADR Candidates
- Title | Context | Decision | Alternatives
### Bubble-Up Questions
- [question] | Recommended: [...] | Confidence: low | Why uncertain: [...]   (may carry conflict-with-settled / Files Needed)
### Material Change Assessment
- material_change: yes|no | Summary: [one line] | Remaining gaps: [...]
```

## Convergence Judge

A fresh sub-agent dispatched after every pass (including Pass 1, which diffs against Snapshot-0).
It decides whether the loop stops.

**Inputs:** the pass-(N-1) snapshot, the current pass-N artifacts, and the Pass agent's
self-reported Material Change Assessment.

**Method:** the judge **independently diffs** snapshot vs current and classifies each change
itself; the Pass agent's self-report is only a cross-check (a discrepancy is logged). It applies
the rubric in `CONVERGENCE-JUDGE-CHECKLIST.md`:

- **Material change:** adds/removes/alters a decision; changes scope (adds/drops a requirement or
  task); changes an interface/type/signature/schema; adds/removes/alters an edge case or its
  handling; resolves or introduces an `UNRESOLVED` marker; adds/removes/alters an ADR or its
  decision; changes a numeric threshold/limit/default.
- **Minor change:** wording, formatting, reordering, typo, clarifying restatement that preserves
  meaning, whitespace.
- **Conservative bias:** when a change is ambiguous, classify it as **material** (one cheap extra
  pass is preferred over shipping an under-hardened artifact).

Model: **opus**.

### CONVERGENCE-JUDGE-CHECKLIST.md response format

```
### Verdict: CONVERGED or NOT CONVERGED

### Changes
| # | Artifact | Change summary | Classification: material/minor | Why |

### Open Gaps
- [gap the judge itself spotted that this pass missed]   (feeds the next pass)

### Rationale
[1–3 sentences tying the verdict to the stop condition]
```

The orchestrator emits `CONVERGED` only when the judge reports zero material rows AND empty Open
Gaps AND (orchestrator-checked) no UNRESOLVED markers and no pending bubble-up questions.

## Escalation / Bubble-Up

Pass agents are non-interactive; only the orchestrator talks to the user. A low-confidence pass
returns `### Bubble-Up Questions`; the orchestrator handles them.

**Handling (record-and-defer).** On collecting a pass's questions, the orchestrator asks the user
immediately (batched, with recommendations, deduped against already-answered/deferred questions),
saves each answer as a domain-tagged feedback memory and as a settled decision
(`source: "user/bubble-up"`), and the **next** pass applies them — there is no mid-pass
re-dispatch. Applying an answer is itself a material change, so a pass that only raised questions
is never "converged."

**Confidence gating** (by `--confidence-threshold`):

| Threshold | Bubble-up behavior |
|-----------|--------------------|
| `low` | Never bubble up; every low-confidence question becomes UNRESOLVED with a recommended answer. |
| `medium` (default) | Bubble up only genuinely-novel material trade-offs; routine gaps become UNRESOLVED. |
| `high` | Bubble up all material low-confidence questions. |
| `paranoid` | Bubble up every low-confidence question. |

The gate is enforced orchestrator-side (it can suppress a question into UNRESOLVED) and is also
advisory to the pass.

**Unattended runs.** When `--unattended` is set, or the orchestrator detects no interactive
channel (running as a sub-agent / scheduled), bubble-up is disabled: every would-be question
becomes UNRESOLVED with a recommended answer, and the loop continues to convergence without
blocking. An UNRESOLVED marker is "answered: deferred" — it does not block convergence and is not
re-asked.

**Contradiction with a settled decision.** If a user's bubble-up answer contradicts a settled
decision, the orchestrator reuses the existing `--redo` cascade: mark the contradicted decision
`invalidated`, walk `depends_on` to re-queue affected gaps, apply the >60%-invalidated
"consider re-planning" warning, and continue the loop under the corrected constraint.

## Convergence Metric and Chart

**Metric.** Each pass yields an **instability score**:

```
instability_score = material_changes + open_gaps + pending_questions + unresolved_markers
```

It reaches 0 exactly at convergence — the numeric form of the stop condition. The components are
tracked individually. Per-pass metrics are stored in `harden.passes[].metrics` and written to
`docs/auto-plan/reports/YYYY-MM-DD-<topic>-convergence.csv` on every run (no dependencies).

CSV columns: `pass,material_changes,minor_changes,open_gaps,pending_questions,unresolved_markers,instability_score`.

**Chart.** A best-effort PNG at `docs/auto-plan/reports/YYYY-MM-DD-<topic>-convergence.png`: a
line chart with pass number on the x-axis and instability score (plus component lines) on the
y-axis, titled `Convergence — <topic>`, showing the descent to 0. Rendering mirrors the existing
`dot -Tpng` best-effort pattern:

1. Try `python3` with matplotlib (render from the CSV).
2. Else try `gnuplot` (render from the CSV).
3. Else skip the PNG, and the report embeds an ASCII sparkline of the instability score plus a
   note that the PNG was skipped (no renderer found).

The planning report's Hardening Passes section embeds the PNG (`![convergence](...-convergence.png)`)
when present, and always includes the metrics table.

## State Schema Extension

The existing state JSON gains one top-level `harden` object. The full-rewrite-each-pass
discipline is unchanged (the whole file is re-serialized after every state mutation; never
patched in place).

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

`convergence_status` ∈ `in_progress | converged | max_passes_reached | oscillation | failed | interrupted`
(`failed` = a pass hard-failed twice; `interrupted` = a pass was started but never completed,
recoverable via `--resume`).
`current_pass` and `convergence_status` sit at the top of the `harden` object for quick
inspection. Each pass entry is written twice: as `status:"running"` (with `judge_verdict:null`)
before the Pass agent runs, then updated to `status:"complete"` after the judge verdicts — the
`running`→`complete` transition is how an interrupted pass is detected.

**Snapshots.** Plain file copies (not git commits, not a concatenated history file) under
`docs/auto-plan/reports/snapshots/pass-N/`, preserving original artifact filenames including any
`adr/NNNN-*.md`. Each `pass-N/` holds the full pre-overwrite artifact set. Retention: keep the
last 2 pass directories; prune older ones as each new pass starts (the per-pass changelog in
state is the permanent audit trail). The artifact filename date prefix is frozen at Pass 1's date
so paths never churn across multi-day runs.

**`--resume`.** Reads `harden.convergence_status` and `harden.current_pass`. If the last `passes[]`
entry is `status:"running"` (interrupted), restore artifacts from its snapshot, then re-run that
pass. If `status:"complete"` but not converged, start the next pass. If terminal
(`converged`/`max_passes_reached`/`oscillation`/`failed`), the loop is done.

## Termination and Failure

| Condition | Detected by | Emitted | `convergence_status` |
|-----------|-------------|---------|----------------------|
| Convergence | judge: 0 material + 0 gaps + 0 UNRESOLVED + 0 pending | final hardened artifacts | `converged` |
| Pass budget exhausted | orchestrator: `pass == max_passes`, not converged | most-hardened artifacts with surviving UNRESOLVED markers + "did not converge" banner | `max_passes_reached` |
| Oscillation | orchestrator: pass-N fingerprint == pass-(N-2) | the version with fewer open gaps; tie → latest | `oscillation` |
| Hard failure | Pass agent garbage/timeout twice | last-good artifacts | `failed` |

A retried (failed-then-redispatched) pass does **not** consume the `--max-passes` budget; the
budget counts completed passes, not infrastructure flakiness. Oscillation detection compares the
material-change fingerprint sets stored per pass in state (not raw text), so minor edits don't
mask a ping-pong.

## File Changes

**New fragment files (in `auto-plan/`):**

| File | Description |
|------|-------------|
| `HARDENING-PASS-PROTOCOL.md` | Playbook pasted into the Hardening Pass agent: review-and-patch, material-only edits, confidence gating, bubble-up rules. |
| `HARDENING-PASS-RESPONSE-TEMPLATE.md` | Exact response headers the Pass agent returns (orchestrator-parsing contract). |
| `CONVERGENCE-JUDGE-CHECKLIST.md` | Material-vs-minor rubric, conservative bias, and CONVERGED/NOT CONVERGED response format for the judge. |

**Modified files:**

| File | Change |
|------|--------|
| `auto-plan/SKILL.md` | Add `--harden`/`--max-passes`/`--unattended` to the flag table; add a Phase-matrix row; add the "Phase 5: Hardening Meta-Loop" section (loop pseudocode, Pass-result collection logic, judge dispatch); extend the State File and Planning Report sections; document the convergence metric/chart. |
| `CLAUDE.md` | Add the three new fragments to the architecture table; note the new orchestrator ↔ `HARDENING-PASS-RESPONSE-TEMPLATE.md` contract and the orchestrator ↔ `CONVERGENCE-JUDGE-CHECKLIST.md` contract. |
| `README.md` | One paragraph describing the `--harden` capability. |

**New ADRs (in `docs/adr/`):** `0001`–`0006` (listed in Resolved Questions / produced with this spec).

## Verification

This feature is done when:

1. `SKILL.md`'s flag table lists `--harden`, `--max-passes` (default 3), and `--unattended`, and the Phase matrix has a `--harden` row.
2. `SKILL.md` contains a "Phase 5: Hardening Meta-Loop" section whose pseudocode matches the Architecture and Phase 5 sections of this spec.
3. The three new fragment files exist and their response-template headers match this spec character-for-character.
4. `CLAUDE.md`'s architecture table lists all three new fragments and names the two new parsing contracts.
5. The `HARDENING-PASS-RESPONSE-TEMPLATE.md` headers and the SKILL.md Phase-5 collection logic reference the identical seven section names.
6. The `CONVERGENCE-JUDGE-CHECKLIST.md` response format and the SKILL.md judge-collection logic reference the identical headers (`Verdict`, `Changes`, `Open Gaps`, `Rationale`).
7. The State File section in SKILL.md documents the `harden` object exactly as in this spec, including the two-phase `running`→`complete` write.
8. The Planning Report section in SKILL.md documents the Hardening Passes table and the convergence CSV/PNG outputs.
9. The instability-score formula appears identically in SKILL.md and `CONVERGENCE-JUDGE-CHECKLIST.md`.
10. A dry read-through confirms `--harden` + `--dry-run` is specified as a hard error and `--redo` is specified as independent.

## Resolved Questions

1. **Opt-in vs default:** → Opt-in bare flag `--harden`; normal runs unchanged.
2. **Context-clearing mechanism:** → Thin outer orchestrator loop; each pass and each judge call is a fresh isolated sub-agent. (ADR 0001)
3. **Stop criterion:** → Convergence judge classifies material vs minor; stop when only-minor and no open gaps. (ADR 0003)
4. **Re-feed scope:** → Full artifact set (spec + ADRs + plan) every pass.
5. **Purpose of passes:** → Fill gaps and harden; "meaningful" = material change.
6. **Interactivity:** → Passes may escalate; non-interactive pass agents bubble up to the interactive orchestrator.
7. **Pass budget:** → `--max-passes`, default 3, distinct from `--max-iterations`.
8. **Loop placement:** → New Phase 5 wrapper; Pass 1 normal+interactive, Passes 2+ via the Pass agent. (ADR 0001)
9. **Flag composition:** → Legal with skip-plan/plan-only/resume/confidence-threshold/auto-commit/unattended; hard error with dry-run; redo independent.
10. **Pass agent nesting:** → Streamlined single-context review-and-patch; no skill re-invocation, no sub-agents. (ADR 0002)
11. **Write vs propose:** → Pass agent proposes; orchestrator applies after snapshot.
12. **New fragments:** → HARDENING-PASS-PROTOCOL, HARDENING-PASS-RESPONSE-TEMPLATE, CONVERGENCE-JUDGE-CHECKLIST.
13. **Cosmetic churn:** → Material-only edits; standalone minor edits forbidden.
14. **Judge trust:** → Independent diff; self-report is a cross-check only. (ADR 0003)
15. **Material/minor rubric + conservative bias:** → As listed; ambiguous → material. (ADR 0003)
16. **Judge cadence/baseline/model:** → Every pass; Snapshot-0 baseline; opus.
17. **Convergence stop condition:** → 0 material + 0 gaps + 0 UNRESOLVED + 0 pending.
18. **Termination conditions:** → converged / max_passes / oscillation / hard failure.
19. **Oscillation:** → Orchestrator-owned; compare pass-N vs pass-(N-2) fingerprints.
20. **Pass failure:** → Retry once; doesn't consume budget; abort after 2.
21. **State schema:** → Top-level `harden` object; two-phase write; full rewrite.
22. **Snapshots:** → File copies under reports/snapshots/pass-N/; last-2 retention; frozen date. (ADR 0004)
23. **`--resume`:** → Via convergence_status + current_pass; running entry → restore + re-run.
24. **`--redo`:** → Independent of the loop; no auto-re-harden; no new snapshots.
25. **Escalation handling:** → Record-and-defer; ask immediately, next pass applies.
26. **Confidence gating:** → low/medium/high/paranoid table.
27. **Unattended mode:** → `--unattended` + auto-detect; degrade to UNRESOLVED.
28. **Bubble-up dedup/deferral:** → Dedup via fuzzy match; deferred → UNRESOLVED; only pending blocks.
29. **Contradiction with settled decision:** → Reuse `--redo` cascade. (ADR 0005)
30. **`--auto-commit` granularity:** → Once per pass, message `auto-plan harden pass N: <verdict>`.
31. **Convergence metric:** → instability_score; CSV always. (ADR 0006)
32. **Convergence chart:** → Best-effort PNG; matplotlib → gnuplot → ASCII fallback.
33. **Documentation surface:** → SKILL.md, CLAUDE.md, README + 3 fragments.

## Out of Scope

- Re-hardening automatically after `--redo` (requires explicit `--harden`).
- A configurable numeric convergence threshold (convergence is categorical, not tunable).
- Parallel passes (passes are strictly sequential — each reads the previous pass's output).
- A snapshot-retention override flag (fixed at last-2 for this version).
- Hardening Pass agents spawning their own Grillers/Researchers (explicitly forbidden).
- Interactive diff review of each pass's edits before they are applied.
