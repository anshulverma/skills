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
- A `/loop` tick fires and a run file exists at `/data/users/anshulverma/sdd-runs/<slug>/run.json`
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

1. Read `/data/users/anshulverma/sdd-runs/<slug>/run.json`. If absent, this is stage 1 — do not loop, run
   the gate in the foreground.
2. If `status` is `done` or `blocked`: print the reason, **stop the loop**, exit.
3. If `in_flight` is set and not stale, another unit is already running. **Do nothing and
   exit.** Do not bump `tick`. See "In-flight marker" below.
4. Claim the unit: set `in_flight`, then do **one** bounded unit — one hardening pass, or one
   plan task with its review. Never a whole stage.
5. Rewrite `run.json` in full (never patch in place). Bump `tick`, clear `in_flight`.
6. **Immediately start the next unit** while the session is live and context allows. Only
   return when context is running low, the run is `done`/`blocked`, or you are genuinely
   waiting on something external.

**One unit per *checkpoint*, not one unit per wall-clock tick.** The rule exists to bound
blast radius: state hits disk after every unit, so a crash or compaction loses at most one
unit. It does **not** mean pause between units. A pipeline that idles until the next cron
fire turns a 40-unit run into a multi-day run for no reason.

**The cron is a watchdog, not a pacer.** Its only job is to resume a run whose session died,
was interrupted, or drifted idle. Progress comes from running units back-to-back in a live
session. A cron tick that fires and finds the run already advancing does nothing and exits.

### In-flight marker

"Already advancing" must be readable **off disk**. A tick has fresh context and no memory of
a dispatched agent, so without a marker it sees an idle-looking run and dispatches a
competing unit — two agents editing the same artifact. File mtime is not a substitute: a
long-running agent that is still reading has not touched its target for many minutes.

Before starting a unit, claim it:

```json
"in_flight": {
  "unit": "PHASE_3_FIX_ROUND_1",
  "detail": "one line a fresh tick can act on",
  "started_at": "2026-08-04T19:19:40Z",
  "agent": "<agent id>",
  "target": "relative/path/being/written"
}
```

Clear it when the unit completes. On the next tick:

| `in_flight` state | Action |
|---|---|
| absent | Claim and run the next unit |
| present, `started_at` under 30 min | Do nothing, exit, do not bump `tick` |
| present, `started_at` over 30 min | Treat as a dead unit: log it, clear the marker, redo that unit |

The staleness window exists because a crashed agent never clears its own marker. Without it,
one dead unit wedges the pipeline permanently — the same failure a pidfile lock would cause.

### Fingerprint every artifact write

A tick that edits an artifact must, in the same unit, record a fingerprint in `run.json`:

```json
"artifact_fingerprints": {
  "docs/auto-plan/specs/<file>.md": {"sha256_16": "...", "lines": 1379, "mtime": 1785...}
}
```

Before the next unit touches that artifact, re-hash it. **A mismatch means the file changed
outside the pipeline — treat the previous unit as lost and redo it.**

This is not paranoia. It happened twice on the monk run: edits verified present immediately
after writing were gone minutes later, mtime reverted to an earlier revision. Root cause was
**dotsync**, which manages `~/.claude` and `~/workspace`, restores its parent snapshot, and
quarantines your writes into `~/.dotsync/conflicts/<n>/`. Keeping the run on unmanaged local
disk (see `STAGES.md` layout) prevents it — but fingerprint anyway, because any external
writer produces the same silent loss.

Verifying a write right after making it does **not** detect this; only a fingerprint checked
at the *start of the next unit* does.

Corollary: `grep`-verifying your own edit proves the write reached the filesystem at that
instant, nothing more. Never treat it as proof the change is durable.

## Arming and Termination

Arm with an explicit interval:

```
/loop 20m /sdd <slug>
```

`/loop` always creates a **recurring cron** (`CronCreate`); omitting the interval just
defaults it to `10m`. So:

- Record the returned job ID in `run.json` as `cron_job_id`, or a later tick cannot stop it.
- Terminate with **`CronDelete({id})`**. `ScheduleWakeup({stop: true})` does not end a cron.
- Arm it `durable: true`, or the run dies with the Claude process.
- It **auto-expires after 7 days** — a long EXECUTE stage may need re-arming.

Full rules and interval selection: [references/LOOP.md](references/LOOP.md).

## Never Block the Loop

Stage 1 is the only place a human is present. Everything after runs with `--unattended`, so
an unanswerable question degrades to an `UNRESOLVED:` marker instead of hanging.

- **UNRESOLVED** — record it, keep going, report at the end.
- **BLOCKED** — genuinely cannot proceed (missing access, plan contradicts reality). Set
  `status: blocked` with a reason, stop the loop, tell the user. Do not keep ticking.

## Common Mistakes

| Mistake | Reality |
|---------|---------|
| `TaskStop(loop_id)` to end the loop | Wrong tool — that stops background agents. Use `CronDelete({id})`. |
| `ScheduleWakeup({stop: true})` to end the loop | Also wrong — `/loop` is a cron. `stop: true` belongs to a different, promptless autonomous loop. Use `CronDelete({id})`. |
| Not recording `cron_job_id` in `run.json` | A later tick has fresh context and no memory of the job ID, so it cannot stop the loop. Fall back to `CronList` if this happens. |
| Arming without `durable: true` | Session-only jobs die with the Claude process, stranding the run. |
| An interval below 10m | Ticks fire while the previous unit's subagents are still running, find nothing, and burn turns. |
| Adding a pid lockfile | Ticks fire only while the REPL is idle. Concurrent ticks cannot happen. |
| `--plan-only` for stage 4 | `--plan-only` runs Phase 3, which **regenerates** the plan and destroys the `writing-plans` output. Use `--resume --harden`. |
| Omitting `--unattended` | The run hangs forever on the first bubble-up question with nobody there to answer. |
| Trusting conversation memory for stage or progress | Context compacts between ticks. Re-read `run.json` every time. |
| Finishing a whole stage in one tick | Runs out of context mid-stage and strands partial state. |
| Skipping the stage-1 gate because the user wants it "fully autonomous" | Autonomy starts *after* the gate. A guessed clarification propagates silently through hardening, the plan, and every implementer with nobody there to catch it. Run the gate while the user is still present, or leave the questions on disk and arm nothing. |
| Running the model-escalation ladder on a missing-ACL failure | The ladder is for capability failures. Access and environment failures go straight to `blocked` — no model can grant an ACL. |

## Red Flags — Stop and Re-read the Contract

- About to ask the user something after stage 1
- About to end the loop with anything other than `CronDelete({id})`
- About to re-dispatch a task the ledger already marks complete
- About to advance a stage without reading its terminal condition off disk
- Writing pipeline artifacts anywhere inside `fbsource`

All of these mean: re-read the tick contract above.
