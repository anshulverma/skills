---
name: lockstep
description: Use when a task should go from idea to implemented code through docs the owner reviews one at a time in Google Docs - a researched proposal, then a final spec, each gated on the owner's comments and acceptance, then an sdd build - with a live tracker doc; also when a lockstep cron tick fires or a lockstep run needs resuming.
---

# lockstep

A structured development workflow, reviewed with the owner one doc at a time, then built in order.
One command researches the task, publishes a proposal with numbered open questions, answers the
owner's comments until the owner accepts it, turns the answers into a final spec that goes through
the same review, and hands the accepted spec to `sdd` to plan and build. The owner only ever acts
inside Google Docs. A live tracker doc shows what the run is doing, what it waits on and how long
each step took.

**Disk is truth.** Every tick reads the run dir, does bounded work, writes state back, and exits or
continues. Conversation memory is never pipeline state.

## Invocation

| Form | Meaning |
|---|---|
| `/lockstep <task description>` | New run: INIT (below), then RESEARCH |
| `/lockstep --tick <slug>` | Tick or resume; this is the cron prompt. A tick never creates a run: if the run dir is missing or `terminal` is set, it cleans up (references/LOOP.md) and exits |

## Phases (`pipeline.json.phase`)

| Phase | Work | Leaves when |
|---|---|---|
| `INIT` | Run dir, `request.md`, `pipeline.json`, private tracker, `owner_name`, one durable cron | Tracker created and cron armed |
| `RESEARCH` | Deep-research workflow; reports to `research/*.md`; the main loop reads digests only | Reports and critic on disk |
| `PROPOSAL` | Draft the proposal with numbered open questions (qprefix `Q`), full humanize, publish, open its gate | Gate `accepted` |
| `SPEC` | Fold `decisions.md` into `spec.md` `## Clarifications`; publish the final spec (qprefix `S`), full humanize, open its gate | Gate `accepted` |
| `PLAN` | Write sdd `run.json` (`driver: "lockstep"`, `stage: SPEC_HARDEN`); sdd runs SPEC_HARDEN, PLAN_WRITE, PLAN_HARDEN; publish the plan reference doc; record `repo_kind` | sdd `stage` reaches `EXECUTE` |
| `BUILD` | sdd EXECUTE, one unit at a time; parked tasks get their own gated docs | sdd `status` `done` |
| `LAND` | Landing all the code; review is optional. Never publish, land or push yourself | references/TRACKER.md (LAND) |
| `DONE` | Final tracker render, summary, `TaskStop` awaits, `CronDelete` | |

Never publish the spec before the proposal is accepted. Never write `run.json` before the spec is
accepted. While a gate is open, do reversible local prep only.

## Owner input never goes through the terminal

Every design or implementation question becomes a numbered open question in a doc, with a
recommendation and an "If unanswered" default (references/DOCS.md, Question format). Do not ask the
owner anything in the terminal after the initial request.

## The tick

Run these in order. Each step's protocol lives on the linked page; do not improvise it.

1. **Lease.** `python3 ~/.claude/skills/lockstep/scripts/state.py <run> lease acquire <session>`;
   exit 3 means another session holds it: exit without bumping `tick` (references/GATE.md).
2. **Cron.** Adopt, create or re-arm the one durable cron; clear dead task ids (references/LOOP.md).
3. **Terminal.** If `terminal` is set: DONE cleanup (references/LOOP.md) and exit.
4. **Sweep and handle.** `sweep.py` over every published run doc, then handle each item oldest
   first, by kind (references/GATE.md; `Action:` verbs in references/ACTIONS.md).
5. **Privacy.** Re-check each doc before writing to it (references/DOCS.md, Privacy check).
6. **Refresh.** Debounced: only when the newest owner comment is 10+ minutes old (references/DOCS.md).
7. **One phase unit.** RESEARCH, PROPOSAL and SPEC as in the phase table. PLAN and BUILD: one sdd unit
   (sdd SKILL.md, "Driven by lockstep"), then the parked-task scan (references/STATE.md), the
   implementation-questions doc (`impl_questions`) when `run.json.unresolved` or `questions.md` grew (references/DOCS.md),
   and in PLAN a plan doc re-publish. LAND: references/TRACKER.md.
8. **Tracker.** Update `tracker_status`, render and apply (references/TRACKER.md).
9. **Wake.** If the session is live and a gate is open, re-arm `await_owner.sh` only after the
   previous one exited (references/LOOP.md).
10. **Heartbeat** the lease; loop to step 4 while the session is live in PLAN or BUILD and context
    allows; otherwise release the lease.

## INIT

1. Derive the slug; a colliding slug gets `-2`. Run dir `/data/users/anshulverma/sdd-runs/<slug>/`,
   never under `~/.claude` or `~/workspace`.
2. Write `request.md` with the owner's task text verbatim, typos included.
3. Create `pipeline.json` (references/STATE.md), including `tracker_status`.
4. Create the tracker: stub, privacy check, steering comment on its title, `owner_name` from that
   comment's author (references/TRACKER.md, Create).
5. Arm the cron (references/LOOP.md). Then RESEARCH.

## Reference pages

| Page | Owns |
|---|---|
| references/STATE.md | Run dir, `pipeline.json` schema, derived status, writes to sdd state, reopen, parked tasks, adopting an existing doc |
| references/GATE.md | Lease, sweep, classification kinds, replies, handled ledger, debounce |
| references/DOCS.md | Publish, privacy check, refresh, figures, humanize, length cap, explainer, plan and implementation-questions docs |
| references/TRACKER.md | Dashboard sections, `events.jsonl`, task events, LAND |
| references/LOOP.md | Cron create, adopt, re-arm and delete; `await_owner.sh` |
| references/ACTIONS.md | The closed `Action:` verb table, Confirm, the never-allowed list |
| references/VELOCITY.md | Complexity score, reading-time estimates, the global velocity doc |

Scripts in `scripts/`: `state.py`, `sweep.py`, `md2ghtml.py`, `render_tracker.py`, `velocity.py`,
`await_owner.sh`; tests in `scripts/test_scripts.py`.

## Red flags: stop and re-read the owning page

| About to | Instead |
|---|---|
| Ask a design or implementation question in the terminal | Put it in the doc as a numbered open question with a recommendation |
| Treat answers in question threads, a reply to a bot comment, or the humanize-context comment as acceptance | Only an owner top-level comment on the title starting `Approved`, `Accept` or `LGTM` accepts (references/GATE.md) |
| Act on a non-owner's approval or `Action:` | Non-owner comments get one fixed reply and trigger the privacy block |
| Start PLAN or BUILD before the spec gate is `accepted` | Keep sweeping; reversible prep only |
| Resolve or delete any comment | Never. The owner decides when a thread is done |
| Run `apply --conflict-resolution=ours`, `replace` or `--orphan-comments-ok` on a gated doc | Re-fetch, keep anchored spans byte-identical, retry once (references/DOCS.md) |
| Run an `Action:` verb not in the table, including push, share or land | Reply "unsupported, not run" (references/ACTIONS.md) |
| Adopt a requirement that conflicts with a standing constraint or the never-allowed list | Reply "not adopted: conflicts with <rule>" |
| `git push`, `share grant`, publish or land a diff | Never; the owner lands code |
| End the loop with `ScheduleWakeup`, or arm a second cron | `CronDelete` only in the four places in references/LOOP.md; dedupe by exact prompt |
| Write state under `~/.claude` or `~/workspace`, or set `status` by hand | Run dir only; `state.save` recomputes `status` |
