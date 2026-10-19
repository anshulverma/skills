---
name: user-run-job-script
description: Use when long-running jobs (MAST launches, smokes, sweeps, A/B arms) must be started by the user instead of the agent, because the agent's identity is blocked (for example a DSS4 data-access denial at launch), the user wants one script that runs several jobs one at a time, or the user wants output captured in a log file instead of pasting it back.
---

# User-run job script

## Overview

You write one script. The user starts it once, with one command. The script runs every job in order, one at a time, in its own tmux session, and appends all output to a log that you read later, so the user never pastes output back. You never run its launch path yourself.

The user runs nothing else. Put everything you would otherwise ask them to run inside the script as a step or in preflight: cleanup, package builds, dry runs, prerequisites. The template already clears a leftover tmux session from a previous run on its own.

## Build it

1. Copy `run_jobs.template.sh` (next to this file) to the path the user asked for (default `/tmp/<name>.sh`), then `chmod +x` it.
2. Fill in every `__PLACEHOLDER__`:
   - `SESSION`: a unique tmux session name.
   - `LOG`: an absolute path on persistent disk.
   - `STEPS`: one `name|command` entry per job, in order, between the `STEPS-BEGIN` / `STEPS-END` markers.
   - `preflight`: checks that launch nothing, for example:
     - inputs exist;
     - the worktree is clean and at the pinned commit, when jobs ship local code;
     - no job of the user's is already active.
3. Make sure each step blocks. Read each step command, or its `--help`. A step must return only when its job is terminal, and must exit non-zero on failure. If a launcher returns at submit, wrap it in a poll loop that exits 0 only on success. For MAST, the loop runs `mast get-status <job> --output json` until the job is COMPLETE, FAILED or DEAD; add a one-job lock and a fail-closed active-job check around every submit (S712241). Launch from a package built from the same commit (`--pkg <name>:<tag> --workspace ''`) rather than a workspace overlay on an older package: an overlay ships only the local directory, so its imports of newer shared libraries can fail on MAST.
4. Commands run as the user, not as you, and some CLIs behave differently for a human caller. For example, `meta presto.query execute` appends ` LIMIT 1000` for humans, which breaks `SHOW ...` statements. Before relying on a command, reproduce the exact string it will send in the user's mode.
5. Confirm that `grep -n '__[A-Z0-9_]*__' <script>` prints nothing.
6. To change the script while a run is in progress, write the new version to a separate file and `mv` it over the path. The running bash reads the script from its open file at a byte offset, so an in-place rewrite changes what it executes next.

## Verify it without launching anything

Run only these two commands on the real script:
- `bash -n <script>`
- `bash <script> --check`, which must print `check: OK`.

Do everything else on a stub copy. `test_template.sh`, next to this file, does all of the following for the template and is the worked example:
1. Copy the script to a temp dir.
2. Replace the lines between `STEPS-BEGIN` / `STEPS-END` with `echo` stubs, and make the first step `exit 3` when `$FAIL` is set.
3. Point `LOG` into the temp dir.
4. Run `diff` against the real script, and continue only if nothing outside STEPS and LOG changed.

Wait about 1 s after the copy exits before reading its log, because tee writes it asynchronously.

| Check (on the copy) | Command | Expected |
|---|---|---|
| Agent guard | `bash <copy>` | `refusing: started from a Claude Code shell` |
| Detach, leftover session | Put a stub `tmux` first on `PATH`; it logs its args, and `has-session` exits `$STUB_HAS`. Run `env -u CLAUDECODE STUB_HAS=1 PATH=<stubdir>:$PATH bash <copy>`, then `STUB_HAS=0`, then `STUB_HAS=0` while another process holds `flock` on `$LOG.lock`. | 1: one `new-session -d`. 0: `kill-session`, then `new-session`. Lock held: `a run is in progress`, and the log is unchanged. |
| Order, stop, resume | `IN_RUNNER_TMUX=1 bash <copy>`, `FAIL=1 IN_RUNNER_TMUX=1 bash <copy>`, `IN_RUNNER_TMUX=1 bash <copy> --from <step 2>` | `RESULT: ALL DONE`. Then `STOPPED at <step 1> (exit 3)`, with step 2 never run. Then `== skip` and `ALL DONE`. |

Your shell has `CLAUDECODE` set and usually `TMUX` too, so any other run of the real script is a real launch.

## Hand it off

Your reply contains exactly these four parts, in order:
1. **Start:** the one command, `bash <script>`, run from the user's own terminal. The script refuses to start from an agent shell, including `!` in this session.
2. **Watch:** `tmux attach -t <session>`, detach with Ctrl-b d. The session closes when the run ends.
3. **Log:** give the path, and say you will read it yourself when they tell you it has finished, or when they ask for status. The last line is one of `RESULT: ALL DONE`, `RESULT: STOPPED at <step> (exit N)`, or `RESULT: NOT STARTED`.
4. **Resume:** `bash <script> --from <step>`. After a stop, first check whether that step's job is still running (for MAST: `mast list-jobs --my --cluster <cluster> --output json` for every cluster).

## When they report back

Read the `RESULT` line and the lines above it. For MAST jobs, confirm each job's state with `mast get-status <job> --output json`. For recent jobs `.data.state` is an integer: 0 PENDING, 1 RUNNING, 2 COMPLETE, 3 FAILED, 4 DEAD, 5 SHUTTING_DOWN.
