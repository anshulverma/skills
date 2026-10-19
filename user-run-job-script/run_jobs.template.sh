#!/usr/bin/env bash
# __PURPOSE__
# Runs STEPS one at a time in its own tmux session and appends everything to $LOG.
#
#   bash __SCRIPT_PATH__                 start (detaches into tmux session $SESSION)
#   bash __SCRIPT_PATH__ --from <step>   resume at a step, skipping the ones before it
#   bash __SCRIPT_PATH__ --check         preflight only, launches nothing (the only mode an agent may run)
set -euo pipefail

SESSION=__SESSION__   # tmux session name; tmux refuses a second session with this name
LOG=__LOG_PATH__      # absolute path; the agent reads this instead of the user pasting output
RUN_LOCK=$LOG.lock    # held by the running copy for its whole life
# name|command. Each command must BLOCK until its job reaches a terminal state and exit non-zero
# on failure. A launcher that returns at submit lets the next step start while the job still runs.
STEPS=(  # STEPS-BEGIN
  "__STEP_1__|__COMMAND_1__"
  "__STEP_2__|__COMMAND_2__"
)  # STEPS-END

preflight() {
  : __PREFLIGHT__  # checks that launch nothing: inputs exist, tree clean, no active jobs, ...
}

FROM=""
case "${1:-}" in
  --check) preflight; echo "check: OK"; exit 0 ;;
  --from)
    FROM=${2:?--from needs a step name}
    known=0
    for s in "${STEPS[@]}"; do [[ ${s%%|*} == "$FROM" ]] && known=1; done
    [[ $known == 1 ]] || { echo "unknown step '$FROM'" >&2; exit 2; }
    ;;
  "") ;;
  *) echo "usage: $0 [--check | --from <step>]" >&2; exit 2 ;;
esac

# Always detach into a dedicated session, even when already inside tmux: an agent's own shell
# usually has $TMUX set, so keying on $TMUX would run the jobs in the foreground of that shell.
if [[ "${IN_RUNNER_TMUX:-}" != 1 ]]; then
  if [[ -n "${CLAUDECODE:-}" ]]; then
    echo "refusing: started from a Claude Code shell; run it from your own terminal" >&2
    exit 1
  fi
  # Failures before the detach also land in $LOG, so the agent never reads a stale RESULT line.
  # (preflight is called plainly, not in an `||` list, so set -e still stops on its first failure.)
  trap 'rc=$?; [[ $rc == 0 ]] || echo "==== $(date -Is) RESULT: NOT STARTED (exit $rc): see the user terminal ====" >> "$LOG"' EXIT
  # The user runs only this script, so it clears a leftover session itself. A session is
  # leftover when no running copy holds the run lock.
  if tmux has-session -t "$SESSION" 2>/dev/null; then
    if ! flock -n "$RUN_LOCK" true; then
      trap - EXIT  # keep the running copy's log clean
      echo "a run is in progress in tmux session $SESSION: tmux attach -t $SESSION" >&2
      exit 1
    fi
    tmux kill-session -t "$SESSION"
    echo "removed leftover tmux session $SESSION (no run held $RUN_LOCK)"
  fi
  preflight
  # The session ends with the run, so a finished or stopped run never blocks a --from resume.
  tmux new-session -d -s "$SESSION" "IN_RUNNER_TMUX=1 bash $(printf '%q ' "$0" "$@")"
  echo "started in tmux session $SESSION"
  echo "  watch: tmux attach -t $SESSION   (detach: Ctrl-b d)"
  echo "  log:   $LOG"
  trap - EXIT
  exit 0
fi

# tee ignores the signals below so the final RESULT line still reaches the log.
exec > >(trap '' INT TERM HUP; exec tee -a "$LOG") 2>&1
exec 8>"$RUN_LOCK"
flock -w 5 8 || { echo "another copy holds $RUN_LOCK; not starting a second one" >&2; exit 1; }
# Every exit path ends the log with exactly one RESULT line.
step=preflight
finished=0
trap 'exit 130' INT TERM HUP  # tmux kill-session sends HUP
trap 'rc=$?; [[ $finished == 1 ]] || echo "==== $(date -Is) RESULT: STOPPED at $step (exit $rc); if a job may still be running, check before resuming with: bash $0 --from $step ===="' EXIT
echo "==== $(date -Is) start on $(hostname) as $(whoami), args: ${*:-none} ===="
preflight

started=1
[[ -z $FROM ]] || started=0
for s in "${STEPS[@]}"; do
  name=${s%%|*}
  cmd=${s#*|}
  [[ $name == "$FROM" ]] && started=1
  if [[ $started == 0 ]]; then echo "== skip $name"; continue; fi
  step=$name
  echo "==== $(date -Is) step $name ===="
  bash -c "$cmd" 8>&-  # non-zero stops the run (set -e + EXIT trap); 8>&- keeps the lock out of jobs
done
finished=1
echo "==== $(date -Is) RESULT: ALL DONE ===="
