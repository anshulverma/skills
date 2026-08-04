---
name: sdd
description: Use when taking a design spec all the way to implemented code with minimal supervision, when resuming an interrupted spec-to-code run, or when a /loop tick fires for an in-flight sdd pipeline.
---

# sdd

Spec-Driven Development. Drives one design spec from "approved" to "implemented" across
many self-paced ticks, with a single interactive gate at the front.

**Core principle: disk is truth.** Every tick starts with fresh, possibly-compacted context.
Conversation memory is never a valid source of pipeline state. A tick reads the run file,
does exactly one bounded unit of work, rewrites the run file, and exits.

## When to Use

- A design spec exists and is approved, and you want it built with minimal supervision
- A `/loop` tick fires and a run file exists at `~/.claude/docs/sdd/<slug>/run.json`
- An earlier sdd run was interrupted and needs resuming

Do NOT use for: exploratory work with no spec (use `superpowers:brainstorming` first), or a
change small enough to implement directly.

## Stages

| # | Stage | Interactive? | Advances when |
|---|-------|--------------|---------------|
| 1 | `UNDERSTAND` — read spec, ask all questions | **Yes, the only one** | User answers, folded into spec |
| 2 | `SPEC_HARDEN` — `auto-plan --harden --skip-plan` | No | `convergence_status` terminal |
| 3 | `PLAN_WRITE` — `superpowers:writing-plans` | No | Plan written + verified |
| 4 | `PLAN_HARDEN` — `auto-plan --resume --harden` | No | `convergence_status` terminal |
| 5 | `EXECUTE` — `superpowers:subagent-driven-development` | No | Every plan task done |

Stage details, exact flags, and the seams between stages: read
[references/STAGES.md](references/STAGES.md).

## The Tick Contract

Every `/sdd` invocation after stage 1 does exactly this:

1. Read `~/.claude/docs/sdd/<slug>/run.json`. If absent, this is stage 1 — do not loop, run
   the gate in the foreground.
2. If `status` is `done` or `blocked`: print the reason, **stop the loop**, exit.
3. Do **one** bounded unit: one hardening pass, or one plan task with its review. Never a
   whole stage.
4. Rewrite `run.json` in full (never patch in place). Bump `tick`.
5. Schedule the next wakeup, or stop. See [references/LOOP.md](references/LOOP.md).

**One unit per tick** is what makes the pipeline survive compaction, interruption, and
restart. A tick that tries to finish a stage will lose its context mid-stage and leave
unrecoverable partial state.

## Arming and Termination

Arm in **dynamic-pacing mode** — no interval:

```
/loop /sdd <slug>
```

Terminate with `ScheduleWakeup({stop: true})`.

A fixed-interval `/loop 15m /sdd` is a **recurring cron**: `stop: true` does not apply to it,
it needs `CronDelete(id)`, and it auto-expires after 7 days. Dynamic mode has neither
problem. Full rules, pacing, and exact tool signatures:
[references/LOOP.md](references/LOOP.md).

## Never Block the Loop

Stage 1 is the only place a human is present. Everything after runs with `--unattended`, so
an unanswerable question degrades to an `UNRESOLVED:` marker instead of hanging.

- **UNRESOLVED** — record it, keep going, report at the end.
- **BLOCKED** — genuinely cannot proceed (missing access, plan contradicts reality). Set
  `status: blocked` with a reason, stop the loop, tell the user. Do not keep ticking.

## Common Mistakes

| Mistake | Reality |
|---------|---------|
| `TaskStop(loop_id)` to end the loop | Wrong tool — that stops background agents. Use `ScheduleWakeup({stop: true})`. |
| Arming with `/loop 15m /sdd` | Interval mode can't self-terminate and expires in 7 days. Omit the interval. |
| `delaySeconds: 60` to poll subagents | Subagent completion re-invokes you automatically. Short polls burn ticks. Use 1200–1800s as a fallback only. |
| Adding a pid lockfile | Ticks fire only while the REPL is idle. Concurrent ticks cannot happen. |
| `--plan-only` for stage 4 | `--plan-only` runs Phase 3, which **regenerates** the plan and destroys the `writing-plans` output. Use `--resume --harden`. |
| Omitting `--unattended` | The run hangs forever on the first bubble-up question with nobody there to answer. |
| Trusting conversation memory for stage or progress | Context compacts between ticks. Re-read `run.json` every time. |
| Finishing a whole stage in one tick | Runs out of context mid-stage and strands partial state. |
| Skipping the stage-1 gate because the user wants it "fully autonomous" | Autonomy starts *after* the gate. A guessed clarification propagates silently through hardening, the plan, and every implementer with nobody there to catch it. Run the gate while the user is still present, or leave the questions on disk and arm nothing. |
| Running the model-escalation ladder on a missing-ACL failure | The ladder is for capability failures. Access and environment failures go straight to `blocked` — no model can grant an ACL. |

## Red Flags — Stop and Re-read the Contract

- About to ask the user something after stage 1
- About to invent a `ScheduleWakeup` parameter (only `delaySeconds`, `prompt`, `reason`, `stop`)
- About to re-dispatch a task the ledger already marks complete
- About to advance a stage without reading its terminal condition off disk
- Writing pipeline artifacts anywhere inside `fbsource`

All of these mean: re-read the tick contract above.
