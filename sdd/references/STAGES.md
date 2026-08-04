# Stages, flags, and seams

## Layout

Everything lives outside the code repo. Never write pipeline artifacts into `fbsource`.

**Do not put the run under `~/.claude/` or `~/workspace/`.** Both are dotsync-managed. dotsync
periodically restores its parent snapshot and quarantines your writes into
`~/.dotsync/conflicts/<n>/`, so a completed unit silently reverts. On the monk run this
destroyed two separate edit rounds; the quarantined copies held an older revision, so the work
was not even recoverable. Every check reported success at the time.

Use local disk outside both scopes:

```
/data/users/anshulverma/sdd-runs/<slug>/
  run.json          # pipeline state — the router
  spec.md           # working copy of the input spec + folded-in answers
  questions.md      # stage-1 questions, then surviving UNRESOLVED markers
  ledger.md         # execution ledger (stage 5)
  docs/auto-plan/   # auto-plan's own output tree (specs, plans, reports, adr)
```

`<slug>` is kebab-case, derived from the spec filename and frozen at stage 1 so paths never
churn.

### Keeping auto-plan's output out of the repo

`auto-plan` hardcodes repo-relative paths (`docs/auto-plan/specs|plans|reports/...`) and has
**no output-path flag**. The session cwd is normally inside `fbsource`, and the `Skill` tool
offers no way to change it — so a naive invocation writes planning cruft straight into the
monorepo.

`cd` does not fix this: each `Bash` call resets cwd, and `auto-plan` runs in the session, not
in a shell.

**Do this instead.** `auto-plan` is a markdown skill — its instructions are interpreted, not
executed — so an explicit override in the invocation wins. State the absolute artifact root
every time:

> Write **all** artifacts under `/data/users/anshulverma/sdd-runs/<slug>/docs/auto-plan/` (absolute), not
> the repo-relative `docs/auto-plan/`. Write nothing inside `fbsource`.

Verify after the first pass that the tree actually appeared under the run directory. If
anything landed in the repo, move it out and re-state the override — do not leave it there.

## run.json

Rewrite in full every tick. Never patch in place.

```json
{
  "slug": "monk",
  "stage": "SPEC_HARDEN",
  "status": "running",
  "spec_path": "/data/users/anshulverma/sdd-runs/monk/spec.md",
  "plan_path": "",
  "autoplan_state": "/data/users/anshulverma/sdd-runs/monk/docs/auto-plan/reports/<date>-monk-state.json",
  "unresolved": [],
  "blocked_reason": "",
  "in_flight": null,
  "tick": 7,
  "stage_ticks": 3,
  "updated_at": "2026-08-04T18:22:00Z"
}
```

`in_flight` is the concurrency guard — a tick claims a unit before starting it and clears it
on completion, so a fresh-context tick can tell a running unit from an idle run without
relying on file mtime. Schema and the staleness rule: see `SKILL.md`, "In-flight marker".

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

cwd `/data/users/anshulverma/sdd-runs/<slug>/`. First tick:

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

### Do not give one agent the whole artifact set

auto-plan's Phase 5 dispatches a single pass agent that reads every artifact, proposes edits as
full-file replacement bodies, and returns them. At real spec-and-plan size that agent **stalls**
— on the monk run it died on stream idle timeout twice, the second time after only reaching
"now let me read the spec". Nothing was produced either time.

Two things make it fail: the read (a 1659-line spec plus a 1129-line plan plus protocol files)
and the return (a full-file body as a payload).

Split it instead:

1. **Narrow read-only audits, run in parallel.** One per failure mode — provenance citations,
   interface/coverage, ordering. Each pulls what it needs with `grep -n` and targeted `sed`
   rather than loading whole files, and returns a compact list of defects.
2. **Apply the fixes from the orchestrator**, not from the agent.

This is the same rule as "keep payloads small, materialize files from the main loop", applied
to hardening. The convergence judge can stay a single agent, because it returns a verdict
rather than content.

### Stop on divergence, not just convergence

auto-plan detects `converged`, `oscillation`, and `max_passes_reached`. It does **not** detect
an artifact that is steadily *inflating* — every pass makes real changes, so nothing looks
stuck, and the loop runs to the pass cap while the document grows past the thing it describes.

After each pass, compute two numbers and record them in `run.json`:

- artifact line count
- markers raised this pass minus markers retired this pass

**Stop the loop when, over 2 consecutive passes, line count grows AND raised exceeds retired.**
That is a pass adding surface rather than resolving it. Record the triggering metrics, then
advance the stage.

On the monk run, SPEC_HARDEN pass 1 raised 26 markers and retired 1 while producing a
1276-line spec for a 7-file markdown skill. Nothing in auto-plan's own termination table would
have caught that; the Phase 4 reviewer caught it by reading. This rule makes it mechanical.

Ending a hardening loop early in either direction is the pipeline's call, not a question for
the user — report the decision and the metrics behind it.

## Stage 3 — PLAN_WRITE (one tick)

Invoke `superpowers:writing-plans` against the hardened spec. Save the plan to the path
auto-plan uses for plans: `docs/auto-plan/plans/<date>-<slug>.md`. Record it in
`run.json.plan_path`.

Verify before advancing: the plan carries its required header, a Global Constraints section
copying the spec's binding values verbatim, per-task interfaces, and no placeholders (`TBD`,
"add error handling", "similar to Task N"). A placeholder here becomes a wrong implementation
in stage 5.

### The seam

**Precondition: the state file must exist.** Stage 4 assumes stage 2 ran auto-plan end to end,
letting it emit `docs/auto-plan/reports/<date>-<slug>-state.json`. If you ran stage 2's phases
manually — dispatching grillers, writers, and reviewers yourself for control or payload reasons,
which is often the right call — **auto-plan never wrote one**. Then `--resume` has nothing to
load and the seam surgery below has nothing to patch.

Check for the state file before stage 4. If it is absent, reconstruct it: record the artifact
paths (spec, plan, ADRs), a `harden_spec` block summarising what stage 2 actually did, and a
fresh `harden` block at `current_pass: 1`. Mark it `"reconstructed": true` with a note saying
why, so the audit trail does not claim auto-plan produced it. Then run Phase 5's protocol
directly — pass agent, apply edits, convergence judge — rather than relying on `--resume`.

Stage 4 must **harden this plan**, not regenerate it. auto-plan's state file must therefore
name it. Rewrite `autoplan_state` in full:

- set `artifacts.plan` to `plan_path`
- rename the existing `harden` block to `harden_spec` (keeps the stage-2 audit trail)
- install a fresh `harden`: `{enabled: true, max_passes: 20, current_pass: 1, convergence_status: "in_progress", passes: []}`

Without the reset, `--resume` reads a terminal `convergence_status` and falls straight
through stage 4 doing nothing.

## Stage 4 — PLAN_HARDEN

cwd `/data/users/anshulverma/sdd-runs/<slug>/`:

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
