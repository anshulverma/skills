# Loop mechanics

How sdd is armed, paced, and stopped. Getting this wrong is the single most common failure:
in baseline testing, three independent agents produced three different termination
mechanisms and two were wrong.

## Two loop modes — pick dynamic

`/loop` has two distinct modes with different control tools. They are not interchangeable.

| | Dynamic mode | Interval mode |
|---|---|---|
| Armed with | `/loop /sdd <slug>` (no interval) | `/loop 15m /sdd <slug>` |
| Backed by | `ScheduleWakeup` | `CronCreate` (recurring cron) |
| You control pacing | Yes, per tick | No, fixed |
| Stop with | `ScheduleWakeup({stop: true})` | `CronDelete({id})` |
| Auto-expires | No | **Yes, after 7 days** |

**sdd always uses dynamic mode.** Hardening passes and implementation tasks have wildly
different durations, so a fixed interval is either wasteful or too slow. More importantly,
dynamic mode can end itself cleanly and never expires mid-run.

## Ending a tick

Exactly one of these, at the very end of every tick, after `run.json` is rewritten.

**Still working:**

```
ScheduleWakeup({
  delaySeconds: 1500,
  prompt: "/sdd <slug>",
  reason: "sdd <slug>: PLAN_HARDEN pass 4/20 dispatched; fallback check"
})
```

`prompt` must be the same `/loop` input verbatim each turn, so the next firing re-enters the
skill.

**Finished or parked:**

```
ScheduleWakeup({stop: true})
```

Omit every other field. Use this for both `done` and `blocked`.

## Picking delaySeconds

The runtime clamps to `[60, 3600]`. The rule that matters:

**Subagent work is harness-tracked — you are re-invoked automatically when it completes.**
Polling for it is pure waste. Schedule a long fallback so the loop survives a hung subagent,
and let the completion notification do the real waking.

| Situation | delaySeconds |
|---|---|
| Subagents dispatched (implementer, reviewer, hardening pass) | 1200–1800 — fallback only |
| Waiting on external state the harness can't see (CI, MAST job, remote queue) | Match the real cadence, e.g. 480 for an ~8 min CI run |
| Idle tick, nothing specific to watch | 1200–1800 |

Never use 60–120s to poll something the harness already tracks.

`reason` is shown to the user and goes to telemetry. Make it specific: name the slug, the
stage, and what you're waiting on. "waiting" is useless; "sdd monk: EXECUTE task 4/11
implementer running" is useful.

## Valid ScheduleWakeup parameters

Only these four exist. Do not invent others (`noop`, `taskId`, `maxTicks` are not real):

- `delaySeconds` — number, clamped `[60, 3600]`
- `prompt` — string, the verbatim `/loop` input
- `reason` — string, one specific sentence
- `stop` — boolean; when true, all other fields ignored

## No lock file is needed

Scheduled jobs fire **only while the REPL is idle**, never mid-query. Two ticks cannot
overlap, so there is no double-dispatch race and no reason for a pidfile or mtime lock.
Baseline agents invent one anyway — it is dead complexity that can itself wedge the pipeline
if a stale lock is left behind.

## Interruption safety

A tick can die at any point (context exhaustion, API error, user interrupt). The pipeline
recovers because:

- `run.json` is rewritten **only** after a unit of work completes, so a dead tick leaves the
  previous consistent state.
- `auto-plan --resume` restores an interrupted hardening pass from its own snapshot.
- The execution ledger records completed tasks, so a re-run resumes at the first incomplete
  one.

Never write `run.json` at the *start* of a tick to "claim" work. That converts a crashed tick
into permanently skipped work.
