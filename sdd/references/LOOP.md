# Loop mechanics

How sdd is armed, paced, and stopped. Getting this wrong is the single most common failure:
in baseline testing, three independent agents produced three different termination
mechanisms and two were wrong.

## `/loop` is CronCreate, always

Read the installed `loop` skill before assuming otherwise. It parses
`[interval] <prompt…>`, converts the interval to a 5-field cron expression, and calls
**`CronCreate`** with `recurring: true`. There is no interval-less "dynamic pacing" path
through it — omitting the interval just defaults to `10m`.

| | Value |
|---|---|
| Armed with | `/loop 20m /sdd <slug>` |
| Backed by | `CronCreate`, `recurring: true` |
| Stop with | **`CronDelete({id})`** — the job ID returned by `CronCreate` |
| Auto-expires | **Yes, after 7 days** — fires once more, then deletes itself |
| Fires | Only while the REPL is idle, never mid-query |

`ScheduleWakeup` exists but is **not** this path — it serves an autonomous `/loop` with no
user prompt. Do not reach for it here; `stop: true` will not end a cron job.

### Consequences sdd must handle

1. **Record the job ID.** `CronCreate` returns it. Write it to `run.json` as `cron_job_id`
   immediately — without it the loop cannot be stopped from a later, fresh-context tick.
2. **Use `durable: true`.** The default is session-only, so the pipeline would die with the
   Claude process. An sdd run is explicitly designed to survive restarts.
3. **Watch the 7-day ceiling.** A long EXECUTE stage can outlive the cron. If
   `tick` count times the interval approaches 7 days, say so in the tick output and re-arm.

## The cron is a watchdog, not a pacer

This is the easiest thing to get wrong, and it silently costs days.

The cron does **not** set the pace of the pipeline. Its only job is to resume a run whose
session died, was interrupted, or went idle. Inside a live session, finish a unit and start
the next one immediately — do not wait for a fire.

Arithmetic that makes the point: two 20-pass hardening stages plus plan-writing plus a dozen
execution tasks is ~55 units. Paced by a 20-minute cron that is **18 hours**, nearly all of
it idle. Run back-to-back, it is however long the work actually takes.

A cron tick that fires and finds the run already advancing (`updated_at` moved recently, or
a unit is in flight) does nothing and exits.

### Picking the interval

Since it is a watchdog, the interval is a *recovery latency*, not a throughput knob — how
long a dead run should lie unnoticed.

| Situation | Interval |
|---|---|
| Default | `20m` |
| Long unattended absence, recovery latency matters less | `30m`–`1h` |

Do not go below `10m`: faster only means more no-op wakeups, never more progress.

## Ending a tick

A tick just ends. There is no per-tick scheduling call — the cron fires again on its own.

**Finished or parked** — after rewriting `run.json` with `status: done` or `status: blocked`:

```
CronDelete({id: <run.json.cron_job_id>})
```

Then print the summary. If `cron_job_id` is missing from `run.json`, call `CronList` to find
the job whose prompt is `/sdd <slug>` and delete that.

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
