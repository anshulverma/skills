# Stages, flags, and seams

## Layout

Everything lives outside the code repo. Never write pipeline artifacts into `fbsource`.

```
~/.claude/docs/sdd/<slug>/
  run.json          # pipeline state — the router
  spec.md           # working copy of the input spec + folded-in answers
  questions.md      # stage-1 questions, then surviving UNRESOLVED markers
  ledger.md         # execution ledger (stage 5)
  docs/auto-plan/   # auto-plan's own output tree (specs, plans, reports, adr)
```

`<slug>` is kebab-case, derived from the spec filename and frozen at stage 1 so paths never
churn.

**auto-plan writes to repo-relative `docs/auto-plan/...` and has no output-path flag.** Run
every `auto-plan` invocation with cwd = `~/.claude/docs/sdd/<slug>/` so its tree lands there.

## run.json

Rewrite in full every tick. Never patch in place.

```json
{
  "slug": "monk",
  "stage": "SPEC_HARDEN",
  "status": "running",
  "spec_path": "~/.claude/docs/sdd/monk/spec.md",
  "plan_path": "",
  "autoplan_state": "~/.claude/docs/sdd/monk/docs/auto-plan/reports/<date>-monk-state.json",
  "unresolved": [],
  "blocked_reason": "",
  "tick": 7,
  "stage_ticks": 3,
  "updated_at": "2026-08-04T18:22:00Z"
}
```

`stage` ∈ `UNDERSTAND | SPEC_HARDEN | PLAN_WRITE | PLAN_HARDEN | EXECUTE`.
`status` ∈ `running | done | blocked`.

Guard against silent stalls: if `stage_ticks` exceeds 25 with no change in the stage's own
terminal condition, set `status: blocked` with reason `"stage stalled"`.

## Stage 1 — UNDERSTAND (foreground, interactive)

The only stage with a human present. Do not arm the loop until it completes.

1. Read the spec end to end.
2. Survey the code it touches — in fbsource use the `meta_codesearch:code-search` agent, not
   Grep/Glob/find.
3. Write a restatement: goal, scope boundaries, success criteria, assumptions.
4. Ask **every** open question in one batch, each with your recommended answer.
5. Fold the answers into `spec.md` under `## Clarifications (answered <date>)`. They must be
   *in the file* — later stages run in fresh context and cannot see this conversation.
6. Write `run.json` at `stage: SPEC_HARDEN`.
7. Arm: `/loop /sdd <slug>`.

## Stage 2 — SPEC_HARDEN

cwd `~/.claude/docs/sdd/<slug>/`. First tick:

```
/auto-plan ./spec.md --harden --max-passes 20 --skip-plan --unattended
```

Every later tick: identical, plus `--resume`.

- `--skip-plan` stops auto-plan at spec + ADRs. Stage 3 owns the plan.
- `--unattended` is mandatory. Without it the first bubble-up question hangs the run.
- Never `--auto-commit` — the artifact dir is not a repo.

**Transition** — read `harden.convergence_status` from `autoplan_state`:

| Value | Action |
|---|---|
| `converged`, `max_passes_reached`, `oscillation` | Copy surviving `UNRESOLVED:` markers into `questions.md` and `run.json.unresolved`; go to `PLAN_WRITE` |
| `in_progress` | Stay; next tick adds `--resume` |
| `failed` | Retry once with `--resume`; second failure → `blocked` |

## Stage 3 — PLAN_WRITE (one tick)

Invoke `superpowers:writing-plans` against the hardened spec. Save the plan to the path
auto-plan uses for plans: `docs/auto-plan/plans/<date>-<slug>.md`. Record it in
`run.json.plan_path`.

Verify before advancing: the plan carries its required header, a Global Constraints section
copying the spec's binding values verbatim, per-task interfaces, and no placeholders (`TBD`,
"add error handling", "similar to Task N"). A placeholder here becomes a wrong implementation
in stage 5.

### The seam

Stage 4 must **harden this plan**, not regenerate it. auto-plan's state file must therefore
name it. Rewrite `autoplan_state` in full:

- set `artifacts.plan` to `plan_path`
- rename the existing `harden` block to `harden_spec` (keeps the stage-2 audit trail)
- install a fresh `harden`: `{enabled: true, max_passes: 20, current_pass: 1, convergence_status: "in_progress", passes: []}`

Without the reset, `--resume` reads a terminal `convergence_status` and falls straight
through stage 4 doing nothing.

## Stage 4 — PLAN_HARDEN

cwd `~/.claude/docs/sdd/<slug>/`:

```
/auto-plan ./spec.md --resume --harden --max-passes 20 --unattended
```

**Use `--resume`, not `--plan-only`.** Per auto-plan's own flag table, `--plan-only` routes
`0 → 3 → 4`, and Phase 3 is artifact generation — it would regenerate the plan and destroy
the `writing-plans` output that stage 3 just produced and verified. `--resume` re-enters
Phase 5 over the existing artifact set (spec + ADRs + plan).

**Verify the seam held.** On the first PLAN_HARDEN tick, after the pass completes, confirm
`plan_path` still carries the `writing-plans` structure and was edited rather than replaced.
If it was regenerated from scratch, the state reset above did not take: stop, set
`status: blocked` with reason `"stage-3 seam failed: plan regenerated"`, and report it. Do
not silently continue hardening a plan the user never approved.

Transition rules are identical to stage 2. Terminal → `EXECUTE`.

## Stage 5 — EXECUTE

`superpowers:subagent-driven-development`, with its continuous-execution behavior replaced by
**one plan task per tick**.

`ledger.md` — not the conversation — is the source of truth for progress. Resume at the first
task not marked complete. Never re-dispatch a completed task.

First EXECUTE tick only: run the pre-flight plan-conflict scan; write findings to
`questions.md`; confirm you are not on `master`.

Per tick:

1. Extract task N into a brief file.
2. Record `BASE_REV`.
3. Dispatch the implementer with an explicit model (per the skill's complexity table).
4. Build one review package: `sl log -r 'BASE::HEAD'`, `sl diff --stat`, `sl diff -U 10`.
5. Dispatch the task reviewer.
6. Dispatch **one** fix subagent for all Critical/Important findings; re-review.
7. Append `Task N: complete (commits <base7>..<head7>, review clean)` to `ledger.md`.

Implementer returns BLOCKED — first classify the failure, because the ladder only fits one
kind:

- **Capability failure** (task too hard, model got lost): escalate the model once, then split
  the task, then `status: blocked`. Never retry the same model unchanged.
- **Environment or access failure** (missing ACL, absent credential, unavailable service) or
  **the plan contradicts reality**: skip the ladder entirely and go straight to
  `status: blocked`. No stronger model and no narrower task slice can grant an ACL; running
  the ladder just burns two ticks to arrive at the same place.

Either way, append the task to `ledger.md` as **blocked, not complete**, so a resume stops
there instead of skipping it. Leave `stage` and `plan_path` intact so the run is resumable
once the blocker clears. Put the concrete remediation in `blocked_reason`.

After the last task: whole-branch review on the most capable model, one fix subagent for all
findings, then `arc f && arc lint`, then `status: done`.

## Finishing

On `done` or `blocked`: rewrite `run.json`, print the summary plus any `unresolved` items,
then `ScheduleWakeup({stop: true})`.

A tick that starts and finds `status` already `done` or `blocked` re-issues the stop and
exits — so the pipeline stays safe if the loop somehow outlives it.
